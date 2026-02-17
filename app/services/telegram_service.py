
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from app.config import settings
from app.database import Database
from app.services.interview_service import InterviewService
from app.models.candidate import CandidateModel
from app.models.interview import InterviewSession
from bson import ObjectId

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class TelegramService:
    def __init__(self):
        self.token = settings.telegram_bot_token
        # self.db = Database.db  # REMOVED: db is not connected yet
        self.interview_service = InterviewService()
        self.application = None
        self.admin_email = "05bca054@gmail.com" # Hardcoded for POC as requested

    @property
    def db(self):
        """Get database instance dynamically."""
        if Database.db is None:
            print("CRITICAL: Database.db is None when accessing from TelegramService!")
        return Database.db

    async def initialize(self):
        """Initialize the bot application."""
        print("Telegram Bot: Initializing...")
        
        # Initialize service here to ensure DB is ready
        self.interview_service = InterviewService()
        
        # Fetch token from DB for the specific org
        org_id = await self.get_target_org_id()
        if not org_id:
            print("Telegram Bot Error: Admin Organization not found.")
            return

        org = await self.db.organizations.find_one({"_id": org_id})
        token = org.get("telegram_config", {}).get("bot_token")
        
        if not token:
            print("Telegram Bot Warning: No token found in Organization settings. Skipping.")
            return

        self.token = token
        print(f"Telegram Bot: Starting with token ending in ...{token[-4:]}")

        self.application = ApplicationBuilder().token(self.token).build()

        # Handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_click))
        self.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))

        await self.application.initialize()
        await self.application.start()
        print("Telegram Bot: Started Successfully! 🚀")

    async def start_polling(self):
        """Start polling for updates."""
        if self.application:
            print("Telegram Bot: Starting Polling...")
            await self.application.bot.delete_webhook()  # Ensure cleanup
            await self.application.updater.start_polling()
            print("Telegram Bot: Polling Active.")

    async def stop(self):
        """Stop the bot."""
        if self.application:
            print("Telegram Bot: Stopping...")
            await self.application.stop()
            await self.application.shutdown()
            print("Telegram Bot: Stopped.")

    async def get_target_org_id(self):
        """Get the Organization ID for the admin email."""
        admin = await self.db.users.find_one({"email": self.admin_email})
        if admin:
            return admin["organization_id"]
        # Fallback: Find ANY organization if admin not found (just for safety)
        org = await self.db.organizations.find_one({})
        return org["_id"] if org else None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        print(f"TELEGRAM LOG: User {user.first_name} ({user.id}) started the bot.")
        
        await update.message.reply_text(
            f"Hi {user.first_name}! 👋\nI'm the AI Recruiter. I can help you apply for open positions.\n\nLet me check what's available..."
        )
        
        # Fetch Pipelines
        org_id = await self.get_target_org_id()
        if not org_id:
            await update.message.reply_text("Error: Organization not found.")
            return

        pipelines_cursor = self.db.pipelines.find({"organization_id": org_id, "status": "active"})
        pipelines = await pipelines_cursor.to_list(length=10)

        if not pipelines:
            await update.message.reply_text("Sorry, there are no open positions right now.")
            return

        # Create Buttons
        keyboard = []
        for p in pipelines:
            keyboard.append([InlineKeyboardButton(p["name"], callback_data=f"apply_{str(p['_id'])}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please choose a role to apply for:", reply_markup=reply_markup)

    async def button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle role selection."""
        query = update.callback_query
        await query.answer()

        data = query.data
        user = query.from_user
        print(f"TELEGRAM LOG: Button clicked '{data}' by {user.first_name} ({user.id})")

        if data.startswith("apply_"):
            pipeline_id = data.split("_")[1]
            chat_id = str(user.id)
            
            # 1. Find or Create Candidate
            candidate = await self.db.candidates.find_one({"telegram_chat_id": chat_id, "pipeline_id": ObjectId(pipeline_id)})
            
            if not candidate:
                org_id = await self.get_target_org_id()
                new_candidate = CandidateModel(
                    organization_id=org_id,
                    pipeline_id=ObjectId(pipeline_id),
                    first_name=user.first_name or "Telegram",
                    last_name=user.last_name or "User",
                    email=f"telegram_{chat_id}@example.com", # Placeholder
                    phone=None,
                    status="active"
                )
                
                res = await self.db.candidates.insert_one(new_candidate.model_dump(by_alias=True, exclude={"id"}))
                candidate_id = res.inserted_id
                
                # Update with telegram_id manually
                await self.db.candidates.update_one({"_id": candidate_id}, {"$set": {"telegram_chat_id": chat_id}})
                print(f"TELEGRAM LOG: Created new candidate {candidate_id}")
            else:
                candidate_id = candidate["_id"]
                print(f"TELEGRAM LOG: Found existing candidate {candidate_id}")

            # 2. Create Interview Session
            await query.edit_message_text(text=f"Great! Starting your interview for the role... 🚀")
            
            try:
                session = await self.interview_service.create_session(
                    candidate_id=str(candidate_id),
                    platform="telegram",
                    chat_id=chat_id
                )
                print(f"TELEGRAM LOG: Session created {session.id}. Messages count: {len(session.messages)}")
                
                # Check if session is stuck (last message from user)
                if session.messages and session.messages[-1]["role"] != "assistant":
                    print("TELEGRAM LOG: Detected stuck session. Creating fresh one...")
                    # Mark old session as abandoned
                    await self.db.interview_sessions.update_one(
                        {"_id": session.id},
                        {"$set": {"status": "abandoned"}}
                    )
                    # Create fresh session
                    session = await self.interview_service.create_session(
                        candidate_id=str(candidate_id),
                        platform="telegram",
                        chat_id=chat_id
                    )
                    print(f"TELEGRAM LOG: Fresh session created {session.id}. Messages count: {len(session.messages)}")
                
                # Send the first message (greeting)
                if session.messages:
                    last_msg = session.messages[-1]
                    print(f"TELEGRAM LOG: Last message role: {last_msg['role']}")
                    if last_msg["role"] == "assistant":
                        await context.bot.send_message(chat_id=chat_id, text=last_msg["content"])
                        print(f"TELEGRAM LOG: Sent greeting: {last_msg['content'][:30]}...")
                    else:
                        # This shouldn't happen after the fix above, but just in case
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="Something went wrong initiating the interview. Please try /start again."
                        )
                        print("TELEGRAM LOG: Session still stuck after retry.")
                else:
                    print("TELEGRAM LOG: Session has NO messages.")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Something went wrong initiating the interview. Please try /start again."
                    )
                        
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"TELEGRAM LOG ERROR: {e}")
                await context.bot.send_message(chat_id=chat_id, text=f"Error starting interview: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        user_text = update.message.text
        chat_id = str(update.effective_chat.id)
        
        print(f"TELEGRAM LOG: Received message from {chat_id}: '{user_text}'")
        
        # Find active session
        session_data = await self.db.interview_sessions.find_one(
            {"telegram_chat_id": chat_id, "status": "active"},
            sort=[("created_at", -1)]
        )
        
        if not session_data:
            print("TELEGRAM LOG: No active session found.")
            await update.message.reply_text("You don't have an active interview. Type /start to apply.")
            return
            
        # Process Message
        session_id = str(session_data["_id"])
        
        # Send "Typing..." action
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        try:
            response_text = await self.interview_service.process_message(session_id, user_text)
            print(f"TELEGRAM LOG: Sending AI response: '{response_text[:30]}...'")
            await update.message.reply_text(response_text)
        except Exception as e:
            print(f"TELEGRAM LOG ERROR processing message: {e}")
            await update.message.reply_text("Sorry, I encountered an error. Please try again.")

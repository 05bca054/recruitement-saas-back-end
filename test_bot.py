
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from app.database import Database
from app.config import settings

# Hardcoded token from DB check to be sure (or fetch dynamically)
# I will fetch from DB to match exact environment
TOKEN = "8547810229:AAEKWsxzlrf4oVz1gxW-pXenng-NGKqQwlU" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"User {update.effective_user.first_name} sent /start")
    await update.message.reply_text("Hello! I am the Test Bot. I am working!")

async def run_bot():
    print(f"Starting Test Bot with token: ...{TOKEN[-4:]}")
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        
        print("Polling...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())

"""Service for handling AI interviews."""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId

from openai import AsyncOpenAI
from app.config import settings
from app.database import Database
from app.models.interview import InterviewSession
from app.models.candidate import CandidateModel
from app.services.airtable_service import AirtableService
# We'll need to import AirtableService later for sync

class InterviewService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4-turbo-preview" # Or gpt-3.5-turbo if cost concern
        # self.db = Database.db # REMOVED: Use dynamic property

    @property
    def db(self):
        if Database.db is None:
            print("CRITICAL: Database.db is None in InterviewService!")
        return Database.db
        
    async def create_session(self, candidate_id: str, platform: str = "web_simulator", chat_id: str = None) -> InterviewSession:
        """Initialize a new interview session."""
        candidate = await self.db.candidates.find_one({"_id": ObjectId(candidate_id)})
        if not candidate:
            raise ValueError("Candidate not found")
            
        pipeline = await self.db.pipelines.find_one({"_id": ObjectId(candidate["pipeline_id"])})
        if not pipeline:
            raise ValueError("Pipeline not found")
            
        # Check if active session exists
        existing = await self.db.interview_sessions.find_one({
            "candidate_id": ObjectId(candidate_id),
            "status": "active"
        })
        if existing:
            # Self-healing: If session exists but has no messages (stuck), try generating greeting again
            if not existing.get("messages"):
                session_obj = InterviewSession(**existing)
                await self._generate_initial_greeting(session_obj)
                # Re-fetch
                existing = await self.db.interview_sessions.find_one({"_id": existing["_id"]})
            
            return InterviewSession(**existing)
            
        session = InterviewSession(
            candidate_id=ObjectId(candidate_id),
            pipeline_id=ObjectId(candidate["pipeline_id"]),
            platform=platform,
            telegram_chat_id=chat_id,
            messages=[]
        )
        
        result = await self.db.interview_sessions.insert_one(session.model_dump(by_alias=True, exclude={"id"}))
        session.id = result.inserted_id
        
        # Generate initial AI greeting
        await self._generate_initial_greeting(session)
        
        # Fetch updated session with greeting
        updated_session_data = await self.db.interview_sessions.find_one({"_id": session.id})
        return InterviewSession(**updated_session_data)

    async def get_system_prompt(self, pipeline_id: ObjectId) -> str:
        """Retrieve the configured system prompt from the pipeline."""
        pipeline = await self.db.pipelines.find_one({"_id": pipeline_id})
        if not pipeline:
            return "You are a helpful interviewer. Please ask questions."
            
        agent_config = pipeline.get("interview_agent") or {}
        if not agent_config.get("enabled"):
             # Fallback
             return "You are a helpful interviewer. Please ask questions in English."
        
        prompt_template = agent_config.get("agent_prompt", "")
        
        # Dynamic Question Injection
        questions_data = []
        for stage in pipeline.get("stages", []):
            for q in stage.get("questions", []):
                q_text = q.get("text", "")
                f_up = q.get("follow_up")
                
                entry = q_text
                if f_up and f_up.get("text"):
                    cond = f_up.get("condition")
                    f_text = f_up.get("text")
                    if cond == "ai_judgment":
                        entry += f"\n   [FOLLOW-UP] If the answer is vague or interesting, ask: \"{f_text}\""
                    else:
                        entry += f"\n   [FOLLOW-UP] If answer is \"{cond}\" (or similar), ask: \"{f_text}\""
                
                questions_data.append(entry)
        
        if not questions_data:
            questions_data = ["Describe your background.", "Why do you want this job?"]
            
        total_questions = len(questions_data)
        last_question_text = questions_data[-1].split("\n")[0] if questions_data else ""
        penultimate_question = total_questions - 1 if total_questions > 1 else 1
        
        questions_list_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions_data)])
        
        # Replace placeholders
        final_prompt = prompt_template.replace("{{TOTAL_QUESTIONS}}", str(total_questions))
        final_prompt = final_prompt.replace("{{QUESTIONS_LIST}}", questions_list_str)
        final_prompt = final_prompt.replace("{{LAST_QUESTION_TEXT}}", last_question_text)
        final_prompt = final_prompt.replace("{{PENULTIMATE_QUESTION}}", str(penultimate_question))
        
        return final_prompt

    async def process_message(self, session_id: str, user_text: str) -> str:
        """Process a user message and generate AI response."""
        session_data = await self.db.interview_sessions.find_one({"_id": ObjectId(session_id)})
        if not session_data:
            raise ValueError("Session not found")
        
        session = InterviewSession(**session_data)
        if session.status == "completed":
            return "This interview has already been completed. Thank you!"

        # 1. Load System Prompt
        system_prompt = await self.get_system_prompt(session.pipeline_id)
        
        # 2. Prepare Messages
        # Filter existing messages to OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session.messages)
        
        # Add new user message
        new_user_msg = {"role": "user", "content": user_text}
        messages.append(new_user_msg)
        
        # Update session immediately with user msg
        await self.db.interview_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"messages": new_user_msg}, "$set": {"updated_at": datetime.utcnow()}}
        )

        # 3. Call OpenAI
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "end_interview",
                    "description": "Call this function when the interview is complete (all questions answered).",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Retrieve_messages1",
                    "description": "Retrieve conversation context and history.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "User_Info1",
                    "description": "Save candidate details extracted from answers.",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "data": {
                                "type": "object",
                                "description": "Key-value pairs of extracted info (e.g. {'name': 'John', 'age': 30})"
                            }
                        }, 
                        "required": ["data"]
                    }
                }
            }
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7
            )
            
            # Log Usage (Initial Response)
            if response.usage:
                await self._log_token_usage(response.usage, session.candidate_id, "chat")
            
            ai_message = response.choices[0].message
            
            # 4. Handle Tool Calls
            if ai_message.tool_calls:
                print(f"DEBUG: AI generated tool calls: {len(ai_message.tool_calls)}")
                # Add the tool call to conversation history as DICT
                messages.append(ai_message.model_dump())
                
                for tool_call in ai_message.tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    print(f"DEBUG: Executing tool {function_name} with args {args}")
                    
                    tool_output = "Success"
                    if function_name == "end_interview":
                        print("DEBUG: Calling complete_interview...")
                        await self.complete_interview(session)
                        tool_output = "Interview Completed."
                        return "Interview Completed. Thank you!"

                    elif function_name == "Retrieve_messages1":
                        tool_output = "Context retrieved successfully. Proceed with analysis."

                    elif function_name == "User_Info1":
                        data = args.get("data", {})
                        if data:
                            print(f"Captured User Info: {data}")
                        tool_output = "User info saved."

                    # Append tool result
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_output
                    })
                
                # 5. Get final response after tool outputs
                print("DEBUG: Getting final response after tool outputs...")
                response2 = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools
                )
                
                # Log Usage (Tool Response)
                if response2.usage:
                    await self._log_token_usage(response2.usage, session.candidate_id, "chat_tool_response")

                final_content = response2.choices[0].message.content
                if final_content:
                    print(f"DEBUG: Final AI content: {final_content[:50]}...")
                else:
                    print("DEBUG: Final AI content is None")
                    
                if final_content:
                    final_msg = {"role": "assistant", "content": final_content}
                    await self.db.interview_sessions.update_one(
                        {"_id": ObjectId(session_id)},
                        {"$push": {"messages": final_msg}, "$set": {"updated_at": datetime.utcnow()}}
                    )
                    return final_content
                else:
                    # AI didn't generate content after tool call, return acknowledgment
                    return "I understand. Please continue..."

            # 5. Save AI Response
            print(f"DEBUG: AI Content (No Tools): {ai_message.content[:50]}...")
            if ai_message.content:
                new_ai_msg = {"role": "assistant", "content": ai_message.content}
                await self.db.interview_sessions.update_one(
                    {"_id": ObjectId(session_id)},
                    {"$push": {"messages": new_ai_msg}, "$set": {"updated_at": datetime.utcnow()}}
                )
                return ai_message.content
                
            return "..." 

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            return error_msg


    async def evaluate_interview(self, session: InterviewSession) -> dict:
        """Analyze transcript and score answers based on rubric."""
        print(f"DEBUG: Starting evaluation for session {session.id}")
        # ... (rest of function) ...
        # skipping middle lines to avoid context errors, better to target evaluate_interview call site


    async def evaluate_interview(self, session: InterviewSession) -> dict:
        """Analyze transcript and score answers based on rubric."""
        print(f"DEBUG: Starting evaluation for session {session.id}")
        # 1. Fetch Pipeline Questions
        pipeline = await self.db.pipelines.find_one({"_id": session.pipeline_id})
        questions_data = []
        for stage in pipeline.get("stages", []):
            for q in stage.get("questions", []):
                questions_data.append({
                    "id": q.get("question_id"),
                    "text": q.get("text"),
                    "rubric": q.get("scoring_rubric", ""),
                    "max_score": q.get("max_score", 10)
                })
        
        # 2. Prepare Transcript
        transcript = []
        for msg in session.messages:
            role = "AI" if msg["role"] in ["system", "assistant"] else "Candidate"
            if msg["role"] == "system": continue
            transcript.append(f"{role}: {msg['content']}")
        transcript_text = "\n".join(transcript)
        print(f"DEBUG: Transcript length: {len(transcript_text)}")
        
        # 3. Call LLM for Scoring
        prompt = f"""
        You are an expert HR evaluator. Analyze the following interview transcript and score the candidate's answers based on the provided questions and rubrics.
        
        ### QUESTIONS & RUBRICS
        {json.dumps(questions_data, indent=2)}
        
        ### TRANSCRIPT
        {transcript_text}
        
        ### INSTRUCTIONS
        - Retrieve the candidate's answer for each question from the transcript.
        - Evaluate the answer against the rubric.
        - Assign a score (0 to max_score).
        - Provide a brief reasoning.
        - If a question was NOT asked or NOT answered, score it 0 and mark as "not_answered".
        
        ### OUTPUT FORMAT (JSON)
        {{
            "scores": [
                {{
                    "question_id": "q1",
                    "score": 8,
                    "reasoning": "Candidate explained..."
                }}
            ],
            "total_score": 50,
            "summary_notes": "Candidate showed strong..."
        }}
        """
        
        try:
            print("DEBUG: Calling LLM for scoring...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            # Log Usage
            if response.usage:
                await self._log_token_usage(response.usage, session.candidate_id, "scoring")

            content = response.choices[0].message.content
            print(f"DEBUG: Scoring Result: {content[:100]}...")
            result = json.loads(content)
            return result
        except Exception as e:
            print(f"Scoring Error: {e}")
            return {"scores": [], "total_score": 0, "summary_notes": "Scoring failed."}

    async def complete_interview(self, session: InterviewSession):
        """Mark interview as complete, Score it, and update Airtable."""
        
        # 1. Calculate Scores
        scoring_result = await self.evaluate_interview(session)
        scores = scoring_result.get("scores", [])
        total_score = scoring_result.get("total_score", 0)
        summary = scoring_result.get("summary_notes", "")
        
        # 2. Update session status & scores
        await self.db.interview_sessions.update_one(
            {"_id": session.id},
            {"$set": {
                "status": "completed",
                "scores": scores,
                "total_score": total_score,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # 3. Update Candidate Status
        await self.db.candidates.update_one(
            {"_id": session.candidate_id},
            {"$set": {"status": "interview_completed", "updated_at": datetime.utcnow()}}
        )
        
        # 4. Trigger Airtable Sync
        try:
            # Fetch Candidate to get Org ID and Airtable Record ID
            candidate = await self.db.candidates.find_one({"_id": session.candidate_id})
            if not candidate or not candidate.get("airtable_record_id"):
                print(f"Skipping Airtable sync: No record ID for candidate {session.candidate_id}")
                return

            # Fetch Organization to get API Key
            org = await self.db.organizations.find_one({"_id": candidate["organization_id"]})
            airtable_config = org.get("airtable_config", {})
            api_key = airtable_config.get("api_key")
            base_id = airtable_config.get("base_id")
            
            # Fetch Pipeline to get Table ID
            pipeline = await self.db.pipelines.find_one({"_id": candidate["pipeline_id"]})
            table_id = pipeline.get("airtable_table_id")

            if not (api_key and base_id and table_id):
                 print(f"Skipping Airtable sync: Missing config for candidate {session.candidate_id}")
                 return

            # Format Transcript
            transcript = []
            for msg in session.messages:
                role = "AI" if msg["role"] == "system" or msg["role"] == "assistant" else "Candidate"
                if msg["role"] == "system": continue # Skip system prompt
                transcript.append(f"{role}: {msg['content']}")
            
            transcript_text = "\n\n".join(transcript)
            
            # Sync to Airtable
            airtable = AirtableService(api_key)
            # We assume a field "Interview Notes" or "Notes" exists
            # Or we append to "Status"
            
            notes = f"SCORE: {total_score}\n\nSUMMARY: {summary}\n\nTRANSCRIPT:\n{transcript_text[:5000]}" # Truncate if too long
            
            await airtable.update_record(
                base_id,
                table_id,
                candidate["airtable_record_id"],
                {
                    "Status": "Interview Completed",
                    "Interview Notes": notes
                }
            )
            print(f"Successfully synced interview to Airtable for candidate {session.candidate_id}")
            
        except Exception as e:
            print(f"Error syncing to Airtable: {e}")


    async def _log_token_usage(self, usage: Any, candidate_id: ObjectId, interaction_type: str):
        """Log token usage for billing."""
        # 1. Get Organization ID
        candidate = await self.db.candidates.find_one({"_id": candidate_id})
        if not candidate:
            print(f"Warning: Candidate {candidate_id} not found for billing log.")
            return

        org_id = candidate.get("organization_id")
        
        # 2. Extract Token Counts
        if hasattr(usage, "prompt_tokens"):
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
        else:
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
        # 3. Calculate Cost (from settings)
        cost_input = (input_tokens / 1_000_000) * settings.input_token_cost_per_million
        cost_output = (output_tokens / 1_000_000) * settings.output_token_cost_per_million
        total_cost = cost_input + cost_output
        
        # 4. Save Log
        log_entry = {
            "organization_id": str(org_id),
            "candidate_id": str(candidate_id),
            "interaction_type": interaction_type,
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": total_cost,
            "timestamp": datetime.utcnow()
        }
        
        await self.db.token_usage_logs.insert_one(log_entry)
        
        # 5. Update Candidate Stats (Incremental)
        await self.db.candidates.update_one(
            {"_id": candidate_id},
            {"$inc": {
                "total_input_tokens": input_tokens,
                "total_output_tokens": output_tokens,
                "total_ai_cost": total_cost
            }}
        )
        
        # 6. Update Organization Stats (Incremental)
        await self.db.organizations.update_one(
            {"_id": org_id},
            {"$inc": {
                "total_input_tokens": input_tokens,
                "total_output_tokens": output_tokens,
                "total_ai_cost": total_cost
            }}
        )
        
        print(f"BILLING: Logged usage: {input_tokens} in, {output_tokens} out. Cost: ${total_cost:.6f}")

    async def _generate_initial_greeting(self, session: InterviewSession):
        """Generate the first message from the AI."""
        print(f"DEBUG: Generating initial greeting for session {session.id}...")
        try:
            system_prompt = await self.get_system_prompt(session.pipeline_id)
            print(f"DEBUG: System prompt retrieved. Length: {len(system_prompt)}")
            
            # Construct messages to trigger greeting
            messages = [{"role": "system", "content": system_prompt}]
            messages.append({"role": "user", "content": "Ready"})
            
            print("DEBUG: Calling OpenAI for greeting...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )
            
            # Log Usage
            if response.usage:
                await self._log_token_usage(response.usage, session.candidate_id, "greeting")
            
            ai_message = response.choices[0].message
            print(f"DEBUG: OpenAI Response: {ai_message.content[:50]}...")
            
            if ai_message.content:
                new_ai_msg = {"role": "assistant", "content": ai_message.content}
                await self.db.interview_sessions.update_one(
                    {"_id": session.id},
                    {"$push": {"messages": new_ai_msg}, "$set": {"updated_at": datetime.utcnow()}}
                )
                print("DEBUG: Greeting pushed to DB.")
        except Exception as e:
            print(f"Error generating initial greeting: {e}")
            import traceback
            traceback.print_exc()
            # Append error message so it's visible to user
            error_msg = {"role": "assistant", "content": f"I apologize, I'm having trouble starting the interview. Error details: {str(e)}"}
            await self.db.interview_sessions.update_one(
                {"_id": session.id},
                {"$push": {"messages": error_msg}, "$set": {"updated_at": datetime.utcnow()}}
            )

from typing import List
from app.models.question import Question

def generate_system_prompt(questions: List[Question]) -> str:
    """
    Generates a system prompt for the AI interviewer 'Laura' based on the list of questions.
    """
    
    # Sort questions by order
    sorted_questions = sorted(questions, key=lambda q: q.order)
    
    question_list_text = ""
    logic_instructions = []
    
    total_main = len(sorted_questions)
    
    for i, q in enumerate(sorted_questions):
        question_num = i + 1
        
        # Add main question
        question_list_text += f"{question_num}. {q.text}\n"
        
        # Add follow-up if exists
        if q.follow_up:
            sub_id = f"{question_num}a"
            question_list_text += f"    - {sub_id}. 🔁 {q.follow_up.text}\n"
            
            # Add logic instruction
            condition = q.follow_up.condition
            # Normalize condition for the prompt
            if condition.lower() == "yes":
                logic_instructions.append(f"- If the user answers 'Yes' to question {question_num}, ask sub-question {sub_id}.")
                logic_instructions.append(f"- If the user answers 'No' to question {question_num}, SKIP sub-question {sub_id} and move to the next numbered question.")
            elif condition.lower() == "no":
                logic_instructions.append(f"- If the user answers 'No' to question {question_num}, ask sub-question {sub_id}.")
                logic_instructions.append(f"- If the user answers 'Yes' to question {question_num}, SKIP sub-question {sub_id} and move to the next numbered question.")
            elif condition.lower() == "ai_judgment":
                logic_instructions.append(f"- Analyze the candidate's answer to question {question_num}.")
                logic_instructions.append(f"- If the answer requires clarification or if the follow-up question {sub_id} is relevant based on the context of the answer, ask it.")
                logic_instructions.append(f"- Otherwise, if the answer is complete and the follow-up is not needed, SKIP sub-question {sub_id}.")
            else:
                # Custom condition
                logic_instructions.append(f"- If the answer to question {question_num} is '{condition}', ask sub-question {sub_id}.")
                logic_instructions.append(f"- Otherwise, SKIP sub-question {sub_id}.")

    # Clean up logic instructions string
    logic_block = "\n   ".join(logic_instructions)

    prompt = f"""## Role
You are **Laura**, a friendly and professional human HR agent. You are conducting a job interview. Your goal is to complete ALL {total_main} numbered questions (1-{total_main}) before ending the interview.

## Language & Tone
- **Language:** Spanish (Español).
- **Tone:** Professional, personalized, and very friendly.
- **Style:**
  - Always use friendly emojis (🙂, ✨, 😊, 🥳, 🤩, 🤞).
  - Briefly acknowledge each answer (1 sentence max), then ask the next question.
  - Do NOT list or repeat previous answers.
  - **Constraint:** Do not answer user questions about the company or role. If they ask, politely tell them to finish the interview first.

## Interview Workflow
1. **The Greeting:** (Only after user says "Ready"): Greet them warmly and ask Question 1.

2. **The Loop:**
   - When you receive an answer, acknowledge it briefly.
   - Determine which question comes NEXT based on the conversation history.
   - Ask questions **one by one** in numerical order (1→2→3...→{total_main}).
   - **Never repeat a question that has already been answered.**
   
   **Branching Logic:**
   {logic_block}

   - **CRITICAL:** After question {total_main}, you MUST end the interview.

3. **The End:**
   - After Question {total_main} is answered, call the End_interview tool.
   - Respond with ONLY this exact message:
   
   Con esto, hemos terminado todas las preguntas de la entrevista 🎉  

¡Felicidades! 🥳 ¡Has completado la entrevista con éxito!  
Si tienes alguna pregunta o hay algo más en lo que te pueda apoyar, ¡no dudes en decirme! 😊

## Tool Usage Rules
1. **Retrive_messages1**: MUST be called at the start of every turn (except the first "Ready").
2. **User Info1**: Call this to save details extracted from answers.
3. **End_interview**: Call ONLY when Question {total_main} has been answered.

## Question Progress Tracking
**CRITICAL:** Before asking any question, check the conversation history to see:
- What was the last question number asked?
- Did the user answer it?
- What is the NEXT question number?

## Interview Questions List
{question_list_text}
"""
    return prompt


import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("MONGODB_DB_NAME")

async def inspect_pipeline():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    # Find all pipelines
    pipelines = await db.pipelines.find({}).to_list(None)
    if not pipelines:
        print("No pipelines found.")
        return

    for pipeline in pipelines:
        print(f"\nPipeline: {pipeline.get('name')}")
        print(f"Agent Prompt (First 20 chars): {pipeline.get('interview_agent', {}).get('agent_prompt', '')[:20]}...")
        
        stages = pipeline.get("stages", [])
        print(f"Stages: {len(stages)}")
        
        for i, stage in enumerate(stages):
            print(f"  Stage {i+1}: {stage.get('name')}")
            questions = stage.get("questions", [])
            print(f"    Questions: {len(questions)}")
            for q in questions:
                print(f"      - {q.get('text')}")
                follow_up = q.get('follow_up')
                if follow_up:
                    print(f"        [FOLLOW-UP] Condition: {follow_up.get('condition')} -> {follow_up.get('text')}")

if __name__ == "__main__":
    asyncio.run(inspect_pipeline())

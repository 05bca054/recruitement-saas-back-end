#!/usr/bin/env python3
"""Check if the candidate has scores saved."""

import asyncio
from app.database import Database
from bson import ObjectId

async def check_scores():
    """Check the latest candidate's scores."""
    await Database.connect()
    
    # Get the most recent candidate
    candidate = await Database.db.candidates.find_one(
        {},
        sort=[("created_at", -1)]
    )
    
    if not candidate:
        print("❌ No candidates found")
        return
    
    candidate_id = candidate["_id"]
    print(f"📋 Latest Candidate: {candidate_id}")
    print(f"   Name: {candidate.get('first_name')} {candidate.get('last_name')}")
    print(f"   Status: {candidate.get('status')}")
    print(f"   Email: {candidate.get('email')}")
    
    # Get the session for this candidate
    session = await Database.db.interview_sessions.find_one(
        {"candidate_id": candidate_id},
        sort=[("created_at", -1)]
    )
    
    if not session:
        print("❌ No interview session found")
        return
    
    print(f"\n📝 Interview Session: {session['_id']}")
    print(f"   Status: {session.get('status')}")
    print(f"   Total Score: {session.get('total_score', 'N/A')}")
    print(f"   Message Count: {len(session.get('messages', []))}")
    
    scores = session.get('scores', [])
    if scores:
        print(f"\n✅ Scores ({len(scores)} questions):")
        for score in scores:
            print(f"   - Q: {score.get('question_id')[:8]}... | Score: {score.get('score')}/{score.get('max_score', 10)}")
            print(f"     Reasoning: {score.get('reasoning', 'N/A')[:60]}...")
    else:
        print("\n❌ No scores found in session")
    
    summary = session.get('summary_notes')
    if summary:
        print(f"\n📄 Summary: {summary[:100]}...")

if __name__ == "__main__":
    asyncio.run(check_scores())

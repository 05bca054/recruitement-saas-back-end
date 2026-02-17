#!/usr/bin/env python3
"""Script to delete all candidates and interview sessions from the database."""

import asyncio
from app.database import Database
from app.config import settings

async def clear_all_data():
    """Delete all candidates and interview sessions."""
    await Database.connect()
    
    # Delete all interview sessions
    sessions_result = await Database.db.interview_sessions.delete_many({})
    print(f"✅ Deleted {sessions_result.deleted_count} interview sessions")
    
    # Delete all candidates
    candidates_result = await Database.db.candidates.delete_many({})
    print(f"✅ Deleted {candidates_result.deleted_count} candidates")
    
    print("\n🎉 Database cleared successfully!")

if __name__ == "__main__":
    asyncio.run(clear_all_data())

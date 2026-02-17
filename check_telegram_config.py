
import asyncio
from app.database import Database
from app.config import settings

async def check_config():
    await Database.connect()
    
    email = "05bca054@gmail.com"
    print(f"Checking for user: {email}")
    
    user = await Database.db.users.find_one({"email": email})
    if not user:
        print("❌ User not found!")
        return

    print(f"✅ User found. Org ID: {user['organization_id']}")
    
    org = await Database.db.organizations.find_one({"_id": user['organization_id']})
    if not org:
        print("❌ Organization not found!")
        return

    print(f"✅ Organization found: {org['name']}")
    
    config = org.get("telegram_config", {})
    print(f"Telegram Config: {config}")
    
    if config.get("bot_token"):
        print(f"✅ Bot Token is present (ends with ...{config['bot_token'][-4:]})")
    else:
        print("❌ Bot Token is MISSING in DB")

    await Database.disconnect()

if __name__ == "__main__":
    asyncio.run(check_config())

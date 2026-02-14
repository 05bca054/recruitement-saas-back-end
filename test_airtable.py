"""Test Airtable API to debug table creation."""
import httpx
import asyncio
import sys

# Replace these with your actual values
API_KEY = sys.argv[1] if len(sys.argv) > 1 else ""
BASE_ID = sys.argv[2] if len(sys.argv) > 2 else ""

async def test_airtable():
    """Test Airtable table creation."""
    
    if not API_KEY or not BASE_ID:
        print("Usage: python test_airtable.py <API_KEY> <BASE_ID>")
        return
    
    meta_url = "https://api.airtable.com/v0/meta"
    
    # Test 1: List existing tables
    print("=" * 60)
    print("TEST 1: Listing existing tables in base")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{meta_url}/bases/{BASE_ID}/tables",
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=10.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
            tables = response.json()
            print(f"\n✅ Found {len(tables.get('tables', []))} existing tables:")
            for table in tables.get('tables', []):
                print(f"  - {table['name']} (ID: {table['id']})")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 2: Create a new table
    print("\n" + "=" * 60)
    print("TEST 2: Creating a new test table")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{meta_url}/bases/{BASE_ID}/tables",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "name": "Test Pipeline",
                    "fields": [
                        {"name": "Name", "type": "singleLineText"},
                        {"name": "Email", "type": "email"},
                        {"name": "Phone", "type": "phoneNumber"},
                        {"name": "Current Stage", "type": "singleLineText"},
                        {"name": "Status", "type": "singleSelect", "options": {
                            "choices": [
                                {"name": "Active"},
                                {"name": "Rejected"},
                                {"name": "Hired"}
                            ]
                        }},
                        {"name": "Overall Score", "type": "number", "options": {
                            "precision": 2
                        }},
                        {"name": "Resume URL", "type": "url"},
                        {"name": "Created At", "type": "dateTime", "options": {
                            "dateFormat": {"name": "iso"},
                            "timeFormat": {"name": "24hour"},
                            "timeZone": "utc"
                        }}
                    ]
                },
                timeout=30.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
            result = response.json()
            print(f"\n✅ Table created successfully!")
            print(f"  Table ID: {result['id']}")
            print(f"  Table Name: {result['name']}")
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error {e.response.status_code}")
            print(f"Error details: {e.response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_airtable())

"""Airtable API service."""
import httpx
from typing import Optional, Dict, List


class AirtableService:
    """Service for Airtable API operations."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.airtable.com/v0"
        self.meta_url = "https://api.airtable.com/v0/meta"
    
    def client(self):
        """Get HTTP client with proper headers."""
        return httpx.AsyncClient()
    
    async def create_base(self, workspace_id: str, base_name: str) -> Dict:
        """Create a new Airtable base."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.meta_url}/bases",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "name": base_name,
                        "workspaceId": workspace_id,
                        "tables": [
                            {
                                "name": "Candidates",
                                "fields": [
                                    {"name": "Name", "type": "singleLineText"}
                                ]
                            }
                        ]
                    },
                    timeout=30.0
                )
                
                # Log response for debugging
                print(f"Airtable API Response Status: {response.status_code}")
                print(f"Airtable API Response: {response.text}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"Airtable API Error: {e.response.status_code}")
                print(f"Error details: {e.response.text}")
                raise Exception(f"Airtable API error: {e.response.text}")

    
    async def create_table(self, base_id: str, table_name: str) -> Dict:
        """Create a table in an Airtable base."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.meta_url}/bases/{base_id}/tables",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "name": table_name,
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
            response.raise_for_status()
            return response.json()
    
    async def create_record(self, base_id: str, table_id: str, fields: Dict) -> Dict:
        """Create a record in Airtable."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{base_id}/{table_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"fields": fields},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def update_record(self, base_id: str, table_id: str, record_id: str, fields: Dict) -> Dict:
        """Update a record in Airtable."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/{base_id}/{table_id}/{record_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"fields": fields},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_record(self, base_id: str, table_id: str, record_id: str) -> Dict:
        """Get a record from Airtable."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{base_id}/{table_id}/{record_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"
CANDIDATE_ID = "6990595ba2d05c67ee940f34"  # From browser logs. If invalid, this will fail.

def test_start_interview():
    print(f"Testing Start Interview for candidate {CANDIDATE_ID}...")
    url = f"{BASE_URL}/interviews/start"
    payload = {
        "candidate_id": CANDIDATE_ID,
        "platform": "web_simulator"
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            messages = data.get("messages", [])
            print(f"Session ID: {session_id}")
            print(f"Messages count: {len(messages)}")
            if messages:
                print("Messages:", json.dumps(messages, indent=2))
            else:
                print("WARNING: Messages array is empty! Greeting generation failed silently?")
            return session_id
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_chat(session_id):
    if not session_id:
        return
    print(f"\nTesting Chat for session {session_id}...")
    url = f"{BASE_URL}/interviews/chat"
    payload = {
        "session_id": session_id,
        "message": "Hello, are you there?"
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    session_id = test_start_interview()
    if session_id:
        test_chat(session_id)

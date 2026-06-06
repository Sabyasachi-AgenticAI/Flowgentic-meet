import os
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv(".env.local")

def main():
    api_key = os.getenv("CARTESIA_API_KEY")
    if not api_key:
        print("CARTESIA_API_KEY not found!")
        return
        
    req = urllib.request.Request(
        "https://api.cartesia.ai/voices",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        },
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"Total voices: {len(data)}")
            # Filter and print voices
            for voice in data:
                name = voice.get("name", "Unknown")
                vid = voice.get("id", "Unknown")
                # print details
                gender = "unknown"
                language = "unknown"
                if "metadata" in voice and voice["metadata"]:
                    gender = voice["metadata"].get("gender", "unknown")
                    language = voice["metadata"].get("language", "unknown")
                print(f"Name: {name} | ID: {vid} | Gender: {gender} | Language: {language}")
    except Exception as e:
        print(f"Error fetching voices: {e}")

if __name__ == "__main__":
    main()

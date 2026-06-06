import os
import asyncio
from dotenv import load_dotenv
from livekit.plugins import cartesia
import livekit.agents

load_dotenv(".env.local")

async def main():
    api_key = os.getenv("CARTESIA_API_KEY")
    print(f"Using API Key: {api_key[:10]}...")
    
    async with livekit.agents.utils.http_context.open():
        tts_client = cartesia.TTS(voice="95856005-0332-41b0-935f-352e296aa0df") # Sophie
        print("Testing synthesis...")
        try:
            async with tts_client.stream() as stream:
                stream.push_text("Hello from Cartesia!")
                stream.end_input()
                frames_count = 0
                async for ev in stream:
                    frames_count += 1
                print(f"Success! Synthesized {frames_count} audio frames.")
        except Exception as e:
            print(f"Error during synthesis: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

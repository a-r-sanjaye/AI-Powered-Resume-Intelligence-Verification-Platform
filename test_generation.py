from google import genai
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("API Key not found")
    exit(1)

client = genai.Client(api_key=api_key)

try:
    print("Testing gemini-2.0-flash...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents="Hello, can you hear me?"
    )
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")

def test_model(model_name):
    print(f"Testing model: {model_name}")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents="Hello, are you working?"
        )
        print(f"Success! Response: {response.text[:50]}...")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    if not api_key:
        print("GOOGLE_API_KEY not found.")
    else:
        models_to_test = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro",
            "gemini-pro"
        ]
        
        for model in models_to_test:
            if test_model(model):
                break

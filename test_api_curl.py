import requests
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("API Key not found")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        with open('models_list.json', 'w') as f:
            f.write(response.text)
        print("Models saved to models_list.json")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Error: {e}")

import requests
import os

BASE_URL = "http://127.0.0.1:5000"
FILE_PATH = "sample_resume.docx"

def test_flow():
    # 1. Check Index
    try:
        print("Testing Index Page...")
        resp = requests.get(BASE_URL)
        if resp.status_code == 200 and "AI Driven Resume Integrity Checker" in resp.text:
            print("SUCCESS: Index page loaded.")
        else:
            print(f"FAILURE: Index page failed. Status: {resp.status_code}")
            return
            
        # 2. Upload Resume
        print("\\nTesting Upload (Review Page)...")
        if not os.path.exists(FILE_PATH):
            print(f"FAILURE: Test file {FILE_PATH} not found.")
            return

        with open(FILE_PATH, 'rb') as f:
            files = {'resume': (FILE_PATH, f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            resp = requests.post(f"{BASE_URL}/upload", files=files)
            
        if resp.status_code == 200:
            if "Review Extracted Data" in resp.text:
                print("SUCCESS: Review page loaded.")
                # Basic check if name extraction worked (assuming sample has some name)
                # We won't be too strict on content, just flow.
            else:
                print("FAILURE: Review page did not contain expected text.")
                print(resp.text[:500])
                return
        else:
            print(f"FAILURE: Upload request failed. Status: {resp.status_code}")
            return

        # 3. Analyze (Simulate form submission from Review Page)
        print("\\nTesting Analysis...")
        # We need the filename that was saved. It should be the same as FILE_PATH basename
        filename = os.path.basename(FILE_PATH)
        
        data = {
            'filename': filename,
            'name': 'Linus Torvalds', # Known name for identity match
            'email': 'linus@example.com',
            'github_url': 'https://github.com/torvalds', # Real profile
            'linkedin_url': 'https://linkedin.com/in/linustorvalds', # Likely exists, checking metadata
            'course_url': ''
        }
        
        resp = requests.post(f"{BASE_URL}/analyze", data=data)
        
        if resp.status_code == 200:
            if "Resume Analysis Result" in resp.text:
                print("SUCCESS: Result page loaded.")
                
                # Check for specific Deep Verification outputs in the HTML
                # We expect "Identity: MATCH" or repo stats
                if "Identity: MATCH" in resp.text:
                    print("SUCCESS: Deep Identity Verification passed (Name Match).")
                else:
                    print("WARNING: Identity Match NOT found in output.")
                    
                if "Top Langs" in resp.text:
                    print("SUCCESS: GitHub Repo Analysis ran (Top Langs found).")
                else:
                    print("WARNING: GitHub Repo Analysis stats NOT found.")
            else:
                print("FAILURE: Result page did not contain expected text.")
                print(resp.text[:500])
        else:
             print(f"FAILURE: Analysis request failed. Status: {resp.status_code}")
             print("Error Body:", resp.text)

    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_flow()

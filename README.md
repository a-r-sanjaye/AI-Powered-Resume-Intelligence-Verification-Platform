# AI Driven Resume Integrity Checker

An advanced, AI-powered system built to evaluate, analyze, and verify the integrity of candidate resumes. By combining Natural Language Processing (NLP), Large Language Models (LLM), and real-time data verification, this tool significantly streamlines the hiring process, reduces fraud, and empowers HR teams to make data-driven, confident decisions.

## Features

- **Document Parsing**: Effortlessly extracts text from various resume formats including PDF, DOCX, and images (via OCR).
- **Intelligent Field Extraction**: Uses NLP to identify names, contact information, skills, and links (GitHub, LinkedIn, Portfolio).
- **Automated Verification**:
  - **GitHub Analysis**: Verifies GitHub profiles, runs deep code analysis (LLM) to assess code quality and detect potential tutorial clones.
  - **LinkedIn Reachability**: Checks LinkedIn profile metadata and reachability format.
  - **Certification Validation**: Scans explicitly mentioned certificates against external databases.
- **AI-Driven Integrity Scoring**:
  - Calculates an overall "Integrity Score" based on verified claims vs. unverified/broken claims.
  - LLM-powered anomaly detection scans for exaggerated descriptions, overlapping timelines, and inconsistent skills.
- **Skill Validation Challenges**: Automatically generates technical interview questions based on the candidate's parsed skills.
- **Job Description Matching**: Evaluates the similarity between the candidate's resume and a provided job description using semantic analysis (`sentence-transformers`).
- **HR Dashboard**: A clean and visual dashboard to review past candidate reports, risk alerts, and overall integrity metrics.

## Tech Stack

- **Backend / API**: Flask (Python)
- **Database**: SQLite / SQLAlchemy
- **Data Processing**: Pandas, NumPy
- **NLP & Text Engineering**: spaCy, sentence-transformers, scikit-learn
- **Document Extraction**: pdfplumber, python-docx, pytesseract, Pillow
- **AI / LLM Integrations**: Google GenAI
- **Web Scraping / Verification**: requests, beautifulsoup4

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd AI Driven Resume Integrity Checker
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Create a `.env` file in the root directory and add all the necessary environment variables, API keys (e.g., Google GenAI, GitHub tokens), and secret keys:
   ```properties
   FLASK_SECRET_KEY=your_secret_key_here
   GEMINI_API_KEY=your_google_genai_api_key
   # Add any additional tokens/keys required for scrapers
   ```

## Usage

1. **Initialize the database:**
   The application automatically creates the SQLite database (`app.db` via `db.create_all()`) when first run.

2. **Run the Flask application:**
   You can run the app directly using Python or via the provided batch/PowerShell scripts:
   ```bash
   python app.py
   # Or on Windows using standard scripts:
   run_app.bat
   # Or
   .\run_app.ps1
   ```

3. **Access the Web Interface:**
   By default, the application runs on `http://127.0.0.1:5000`.
   - **Upload Resume**: Go to the homepage (`/`) to start a new candidate evaluation.
   - **Dashboard**: Review existing candidates at `/dashboard`.

## Testing & Health Checks

The project includes several tests (`test_models.py`, `test_generation.py`, `test_api_curl.py`, etc.) and a system health check script to ensure OCR, PDFs, and core APIs communicate correctly. 

To run a health check:
```bash
python run_health_check.py
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)

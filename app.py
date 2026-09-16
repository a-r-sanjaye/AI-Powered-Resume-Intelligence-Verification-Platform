
from dotenv import load_dotenv
load_dotenv(override=True)

import os

# Suppress TensorFlow/Keras warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from flask import Flask, render_template, request, flash, redirect, url_for, session
import uuid
from werkzeug.utils import secure_filename
from config import Config
from models import db, Candidate, ResumeClaim
from modules.extraction import extract_text_from_file
from modules.nlp import parse_resume
from modules.verification import verify_github, verify_linkedin, verify_certification, verify_link_health
from modules.analysis import detect_anomalies, calculate_integrity_score
from modules.analysis import detect_anomalies, calculate_integrity_score
from modules.matching import calculate_similarity

app = Flask(__name__)

app = Flask(__name__)

app.config.from_object(Config)
db.init_app(app)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/setup-candidate', methods=['POST'])
def setup_candidate():
    print("--- Setup Candidate Request Received ---")
    name = request.form.get('name')
    email = request.form.get('email')
    
    if not name or not email:
        flash("Name and Email are required.")
        return redirect(url_for('index'))
        
    session['candidate_name'] = name
    session['candidate_email'] = email
    
    return render_template('upload.html', session_name=name, session_email=email)

@app.route('/dashboard')
def dashboard():
    candidates = Candidate.query.order_by(Candidate.created_at.desc()).all()
    
    # Calculate Summary Stats
    total_candidates = len(candidates)
    if total_candidates > 0:
        avg_score = sum(c.overall_integrity_score for c in candidates) / total_candidates
    else:
        avg_score = 0
        
    high_integrity = sum(1 for c in candidates if c.overall_integrity_score >= 80)
    moderate_integrity = sum(1 for c in candidates if 50 <= c.overall_integrity_score < 80)
    risk_alerts = sum(1 for c in candidates if c.overall_integrity_score < 50)
    
    stats = {
        'total': total_candidates,
        'avg_score': round(avg_score, 1),
        'high': high_integrity,
        'moderate': moderate_integrity,
        'risk': risk_alerts
    }
    
    return render_template('dashboard.html', candidates=candidates, stats=stats)

@app.route('/delete_candidate/<int:candidate_id>', methods=['POST'])
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    try:
        # Delete related claims first (cascade should handle this if set up, but being explicit is safe)
        ResumeClaim.query.filter_by(candidate_id=candidate.id).delete()
        db.session.delete(candidate)
        db.session.commit()
        flash('Candidate record deleted successfully.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting candidate: {str(e)}')
        
    return redirect(url_for('dashboard'))

@app.route('/report/<int:candidate_id>')
def view_report(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    
    # Re-run lightweight parsing for display (since we don't store full JSON in DB)
    parsed_data = parse_resume(candidate.resume_text)
    

    
    # Generate challenges on the fly for the report view as well
    skill_challenges = []
    if parsed_data.get('skills'):
        try:
            from modules.skill_validation import generate_technical_questions
            skill_challenges = generate_technical_questions(parsed_data.get('skills'))
        except Exception as e:
            print(f"Skill Validation Error: {e}")

    return render_template('report.html', candidate=candidate, parsed=parsed_data, claims=candidate.claims, skill_challenges=skill_challenges)

@app.route('/upload', methods=['POST'])
def upload_resume():
    """
    Step 2: Upload file, extract text, and parse data.
    Renders the review page.
    """
    print("--- Upload Request Received ---")
    if 'resume' not in request.files:
        flash('No file part')
        return redirect(url_for('index')) # Redirect to start if session lost or error
    
    file = request.files['resume']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(filepath)
        print(f"File saved to: {filepath}")
        
        # Extract Text
        text, error_msg = extract_text_from_file(filepath)
        
        if error_msg:
             flash(error_msg)
             # Basic cleanup if failed
             if os.path.exists(filepath): os.remove(filepath)
             return redirect(url_for('index'))
             
        if not text:
             flash('Failed to extract text from file.')
             if os.path.exists(filepath): os.remove(filepath)
             return redirect(url_for('index'))

        # NLP Parsing (to populate the form)
        parsed_data = parse_resume(text)
        
        # Merge Session Data (Source of Truth for Identity)
        parsed_data['name'] = session.get('candidate_name', parsed_data.get('name'))
        parsed_data['email'] = session.get('candidate_email', parsed_data.get('email'))
        
        # Render Review Page
        return render_template('review.html', parsed=parsed_data, filename=filename)
    
    flash('Invalid file type')
    return redirect(url_for('index'))

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """
    Step 3: Receive confirmed data, run verification, and save to DB.
    """
    print("--- Analysis Request Received ---")
    filename = request.form.get('filename')
    if not filename:
        flash("Session expired or invalid file.")
        return redirect(url_for('index'))
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        flash("File not found on server.")
        return redirect(url_for('index'))
        
    # Re-extract text (stateless approach for simplicity)
    text, _ = extract_text_from_file(filepath)
    
    # Re-parse 
    parsed_data = parse_resume(text)
    
    # 3. Save to DB
    # PRIORITIZE SESSION DATA for Identity
    candidate_name = session.get('candidate_name') or parsed_data.get('name') or 'Unknown Candidate'
    candidate_email = session.get('candidate_email') or parsed_data.get('email')
    
    # Handle missing email
    if not candidate_email:
        unique_id = uuid.uuid4().hex[:8]
        candidate_email = f"unknown_{unique_id}@example.com"

    candidate = Candidate.query.filter_by(email=candidate_email).first()
    if candidate:
        candidate.name = candidate_name
        candidate.phone = parsed_data.get('phone', '') # Parse phone from text
        candidate.resume_text = text
        # Clear previous claims
        ResumeClaim.query.filter_by(candidate_id=candidate.id).delete()
    else:
        candidate = Candidate(
            name=candidate_name,
            email=candidate_email,
            phone=parsed_data.get('phone', ''),
            resume_text=text
        )
        db.session.add(candidate)
        
    db.session.commit()
    
    # --- VERIFICATION STEP ---
    # Merge parsed links with form overrides
    links = parsed_data.get('links', {})
    
    # Overwrite with manual inputs if provided
    manual_github = request.form.get('github_url', '').strip()
    manual_linkedin = request.form.get('linkedin_url', '').strip()
    
    if manual_github:
        links['github'] = manual_github
    if manual_linkedin:
        links['linkedin'] = manual_linkedin
        
    course_url = request.form.get('course_url', '').strip()
    
    if course_url:
        # Verify manually provided course URL
        health_check = verify_link_health(course_url)
        claim = ResumeClaim(
            candidate_id=candidate.id,
            category='Certificate - Manual Link',
            value=course_url,
            verification_source='Link Reachability Check',
            verification_status=health_check['status'],
            confidence_score=health_check['confidence'],
            audit_log=health_check['details']
        )
        db.session.add(claim)
    

    # Verify GitHub
    if links.get('github'):
        gh_result = verify_github(
            links['github'], 
            candidate_name=candidate.name,
            resume_skills=parsed_data.get('skills', [])
        )
        claim = ResumeClaim(
            candidate_id=candidate.id,
            category='Social - GitHub',
            value=links['github'],
            verification_source='GitHub API + Repo Analysis',
            verification_status=gh_result['status'],
            confidence_score=gh_result['confidence'],
            audit_log=gh_result['details']
        )
        db.session.add(claim)

        # --- DEEP CODE INSIGHT START ---
        # Only run if profile exists/verified
        if gh_result['confidence'] > 0.5:
            try:
                from modules.verification import fetch_github_code_samples
                from modules.llm_analysis import analyze_code_quality
                
                username = links['github'].split("github.com/")[-1].strip("/")
                code_samples = fetch_github_code_samples(username)
                
                if code_samples:
                    code_analysis = analyze_code_quality(code_samples)
                    
                    # Format feedback
                    insight_text = f"Score: {code_analysis.get('quality_score', 0)}/100 | Level: {code_analysis.get('complexity_level', 'Unknown')}"
                    if code_analysis.get('is_tutorial_clone'):
                        insight_text += " | ⚠️ Potential Tutorial Clone"
                    
                    audit_details = code_analysis.get('feedback', '')
                    if code_analysis.get('key_strengths'):
                        audit_details += " Strengths: " + ", ".join(code_analysis['key_strengths'])

                    claim = ResumeClaim(
                        candidate_id=candidate.id,
                        category='Code Quality',
                        value=insight_text,
                        verification_source='Deep Code Analysis (LLM)',
                        verification_status='Analyzed',
                        confidence_score=code_analysis.get('quality_score', 0) / 100.0,
                        audit_log=audit_details
                    )
                    db.session.add(claim)
            except Exception as e:
                print(f"Deep Code Insight Failed: {e}")
        # --- DEEP CODE INSIGHT END ---

    # Verify LinkedIn
    if links.get('linkedin'):
        # 1. Check Format & Metadata
        li_result = verify_linkedin(links['linkedin'], candidate_name=candidate.name)
        
        # 2. Check Reachability
        health_check = verify_link_health(links['linkedin'])
        
        final_status = li_result['status']
        final_confidence = li_result['confidence']
        extra_details = ""
        
        if health_check['status'] != 'Active':
            final_status = "Broken Link"
            final_confidence = 0.0
            extra_details = f" | {health_check['status']}: {health_check['details']}"
        
        claim = ResumeClaim(
            candidate_id=candidate.id,
            category='Social - LinkedIn',
            value=links['linkedin'],
            verification_source='Metadata Check',
            verification_status=final_status,
            confidence_score=final_confidence,
            audit_log=li_result['details'] + extra_details
        )
        db.session.add(claim)
        
    # Verify Certificates (Text Scan + Scrape)
    cert_results = verify_certification(text, candidate_name=candidate.name)
    for cert in cert_results:
        claim = ResumeClaim(
            candidate_id=candidate.id,
            category=f"Certificate - {cert['source']}",
            value="Certificate found in text",
            verification_source='Scraper + Pattern',
            verification_status=cert['status'],
            confidence_score=cert['confidence'],
            audit_log=cert['details']
        )
        db.session.add(claim)

    # Save Skills as Claims
    for skill in parsed_data.get('skills', []):
        claim = ResumeClaim(
            candidate_id=candidate.id,
            category='Skill',
            value=skill,
            verification_status='Unverified'
        )
        db.session.add(claim)
    
    db.session.commit()

    # --- ANALYSIS STEP ---
    current_claims = candidate.claims 
    anomalies = detect_anomalies(parsed_data, current_claims)
    
    for anomaly in anomalies:
        claim = ResumeClaim(
            candidate_id=candidate.id,
            category='Anomaly',
            value=anomaly,
            verification_status='Flagged',
            confidence_score=1.0,
            audit_log="Detected by Anomaly Engine"
        )
        db.session.add(claim)

    # --- LLM INTEGRITY CHECK ---
    from modules.llm_analysis import analyze_integrity
    llm_result = analyze_integrity(text)
    
    # Save Truth Score as a special claim/metric (or just use it to adjust overall score)
    # We will save it as a claim for display purposes
    claim = ResumeClaim(
        candidate_id=candidate.id,
        category='Integrity Score (AI)',
        value=f"{llm_result.get('truth_score', 0)}/100",
        verification_status='AI Evaluated',
        confidence_score=llm_result.get('truth_score', 0) / 100.0,
        audit_log=llm_result.get('summary', 'AI Analysis Completed')
    )
    db.session.add(claim)

    # Save specific flags
    for flag in llm_result.get('flags', []):
        if isinstance(flag, dict): # Normal case
            claim = ResumeClaim(
                candidate_id=candidate.id,
                category=f"AI Flag - {flag.get('type')}",
                value=flag.get('text', 'N/A'),
                verification_status='Flagged',
                confidence_score=0.8,
                audit_log=flag.get('reason', '')
            )
            db.session.add(claim)
        else: # Error string case
             claim = ResumeClaim(
                candidate_id=candidate.id,
                category="AI Analysis Error",
                value="Error",
                verification_status='Error',
                audit_log=str(flag)
            )
             db.session.add(claim)

        
    # Calculate Score
    db.session.commit()
    final_score = calculate_integrity_score(candidate, candidate.claims, anomalies)
    candidate.overall_integrity_score = final_score
    db.session.commit()
    


    # Cleanup: Remove the uploaded file now that we are done
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Cleanup: Removed {filepath}")
    except Exception as e:
        print(f"Warning: Failed to remove file {filepath}: {e}")

    # --- SKILL VALIDATION STEP ---
    skill_challenges = []
    if parsed_data.get('skills'):
        try:
            from modules.skill_validation import generate_technical_questions
            skill_challenges = generate_technical_questions(parsed_data.get('skills'))
        except Exception as e:
            print(f"Skill Validation Integration Error: {e}")

    return render_template('result.html', candidate=candidate, parsed=parsed_data, claims=candidate.claims, skill_challenges=skill_challenges)

@app.route('/match', methods=['GET', 'POST'])
def match_resume():
    similarity_score = None
    job_description = ""
    
    if request.method == 'POST':
        job_description = request.form.get('job_description', '')
        
        if 'resume' not in request.files:
            flash('No file part')
            return redirect(request.url)
            
        file = request.files['resume']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            
            try:
                # Extract text
                resume_text, error = extract_text_from_file(filepath)
                if error:
                    flash(f"Error extracting text: {error}")
                else:
                    # Calculate similarity
                    # Multiply by 100 for percentage
                    raw_score = calculate_similarity(resume_text, job_description)
                    similarity_score = round(raw_score * 100, 1)
            except Exception as e:
                flash(f"An error occurred during matching: {str(e)}")
            finally:
                # Cleanup
                if os.path.exists(filepath):
                    os.remove(filepath)
    
    return render_template('match.html', similarity_score=similarity_score, job_description=job_description)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
        db.create_all()  # Create database tables
    app.run(debug=True)

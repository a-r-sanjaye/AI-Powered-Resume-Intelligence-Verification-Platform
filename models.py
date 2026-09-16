from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    resume_text = db.Column(db.Text)
    overall_integrity_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    claims = db.relationship('ResumeClaim', backref='candidate', lazy=True)

class ResumeClaim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'Education', 'Skill', 'Experience'
    value = db.Column(db.Text, nullable=False)
    verification_source = db.Column(db.String(50))  # e.g., 'LinkedIn', 'GitHub'
    verification_status = db.Column(db.String(20), default='Unverified')  # Verified, Suspicious, Fake
    confidence_score = db.Column(db.Float, default=0.0)
    audit_log = db.Column(db.Text)



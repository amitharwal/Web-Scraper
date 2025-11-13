"""
Database Models.
"""

from auditor_pro import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    projects = db.relationship('Project', backref='owner', lazy=True, cascade='all, delete-orphan')

    def __init__(self, email, password):
        self.email = email
        self.set_password(password)
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    def __repr__(self):
        return f"User('{self.email}')"


class Project(db.Model):
    """
    Project model for storing user-tracked sites.
    """
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    schedule = db.Column(db.String(20), nullable=False, default='none')

    reports = db.relationship('AuditReport', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"Project('{self.name}', '{self.base_url}')"

    def get_latest_report_status(self):
        latest_report = self.reports.order_by(AuditReport.created_at.desc()).first()
        if not latest_report:
            return "No audits run"
        if latest_report.status == 'PENDING' or latest_report.status == 'RUNNING':
            return f"Audit {latest_report.status.lower()}..."
        if latest_report.status == 'COMPLETE':
            schedule_text = f" ({self.schedule.title()})" if self.schedule != 'none' else ""
            return f"Score: {latest_report.overall_score}/100 | Perf: {latest_report.performance_score}/100{schedule_text}"
        return "Audit Failed"


class AuditReport(db.Model):
    __tablename__ = 'audit_reports'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    error_message = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    overall_score = db.Column(db.Integer)
    seo_score = db.Column(db.Integer)
    a11y_score = db.Column(db.Integer)
    performance_score = db.Column(db.Integer)
    lcp = db.Column(db.Float)
    cls = db.Column(db.Float)
    fid = db.Column(db.Float)
    results = db.relationship('AuditResult', backref='report', lazy=True, cascade='all, delete-orphan')

    # One Report can have Many Broken Links
    broken_links = db.relationship('BrokenLink', backref='report', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"AuditReport {self.id} ({self.status}) for Project {self.project_id}"

class AuditResult(db.Model):
    __tablename__ = 'audit_results'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('audit_reports.id'), nullable=False)
    def __repr__(self):
        return f"AuditResult {self.id} ({self.status}) - {self.title}"

class BrokenLink(db.Model):
    """
    Stores a single broken link found during an audit.
    """
    __tablename__ = 'broken_links'

    id = db.Column(db.Integer, primary_key=True)
    link_url = db.Column(db.String(1024), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)

    # Foreign key to link to the AuditReport table
    report_id = db.Column(db.Integer, db.ForeignKey('audit_reports.id'), nullable=False)

    def __repr__(self):
        return f"BrokenLink {self.id} ({self.status_code}) - {self.link_url[:50]}"
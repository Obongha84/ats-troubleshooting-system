from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# ========== SETUP ==========
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diagnostics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ========== MODELS ==========
class Diagnosis(db.Model):
    __tablename__ = 'diagnoses'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    system_status = db.Column(db.String(50), default='Healthy')
    cpu_usage = db.Column(db.Float, default=0.0)
    memory_usage = db.Column(db.Float, default=0.0)
    disk_usage = db.Column(db.Float, default=0.0)
    network_status = db.Column(db.String(50), default='Unknown')
    issues_found = db.Column(db.Integer, default=0)
    issues_fixed = db.Column(db.Integer, default=0)
    details = db.Column(db.Text, default='{}')
    user_notes = db.Column(db.Text, nullable=True)

class SystemCheck(db.Model):
    __tablename__ = 'system_checks'
    
    id = db.Column(db.Integer, primary_key=True)
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnoses.id', ondelete='CASCADE'))
    check_name = db.Column(db.String(100))
    status = db.Column(db.String(50))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ========== CREATE TABLES ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("=" * 60)
        print("✅ TABLES CREATED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📊 Tables created:")
        print("   📁 diagnoses")
        print("   📁 system_checks")
        print("\n📁 Database location:", os.path.abspath('diagnostics.db'))
        print("\n💡 Next steps:")
        print("   1. Run 'python app.py' to start the web server")
        print("   2. Open http://127.0.0.1:5000 in your browser")
        print("   3. Click 'Run Diagnostics' to create data")
        print("   4. Run 'python quick_view.py' to view the data")
        print("=" * 60)
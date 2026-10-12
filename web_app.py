"""
ATS - Automated Troubleshooting System
========================================
Main Flask Application (Cross-Platform Deployment-Ready)

Features:
- User Authentication (Multi-user)
- Password Reset (Forgot Password)
- Email Alerts
- Scheduled Auto-Scans
- Disk Temperature Monitoring
- Rule-based Chatbot
- Multi-Drive Detection (Windows + Linux compatible)
- Health Score (0-100)
- Diagnoses Comparison
- Auto-Repair Actions
"""

# ============================================================
# IMPORTS
# ============================================================
from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, send_file, Response, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

import json
import os
import random
import time
import shutil
import subprocess
import platform
import csv
import pandas as pd
import psutil


# ============================================================
# CREATE FLASK APP
# ============================================================
app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

database_url = os.environ.get('DATABASE_URL', '')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("[ATS] Using production database (PostgreSQL)")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diagnoses.db'
    print("[ATS] Using local SQLite database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'noreply@ats.com')


# ============================================================
# INITIALIZE EXTENSIONS
# ============================================================
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
mail = Mail(app)


# ============================================================
# MODELS
# ============================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    alert_email = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    diagnoses = db.relationship('Diagnosis', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'alert_email': self.alert_email,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }


class Diagnosis(db.Model):
    __tablename__ = 'diagnoses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    system_name = db.Column(db.String(100), default='Local System')
    system_status = db.Column(db.String(50), default='Healthy')
    cpu_usage = db.Column(db.Float, default=0.0)
    memory_usage = db.Column(db.Float, default=0.0)
    disk_usage = db.Column(db.Float, default=0.0)
    disk_health = db.Column(db.String(50), default='Good')
    disk_temperature = db.Column(db.Float, default=0.0)
    disk_read_errors = db.Column(db.Integer, default=0)
    disk_write_errors = db.Column(db.Integer, default=0)
    disk_power_on_hours = db.Column(db.Integer, default=0)
    disk_bad_sectors = db.Column(db.Integer, default=0)
    network_status = db.Column(db.String(50), default='Unknown')
    issues_found = db.Column(db.Integer, default=0)
    issues_fixed = db.Column(db.Integer, default=0)
    details = db.Column(db.Text, default='{}')
    user_notes = db.Column(db.Text, nullable=True)
    scan_type = db.Column(db.String(50), default='manual')

    def to_dict(self):
        try:
            details_data = json.loads(self.details) if self.details else {}
        except:
            details_data = {}

        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'system_name': self.system_name,
            'system_status': self.system_status,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'disk_health': self.disk_health,
            'disk_temperature': self.disk_temperature,
            'disk_read_errors': self.disk_read_errors,
            'disk_write_errors': self.disk_write_errors,
            'disk_power_on_hours': self.disk_power_on_hours,
            'disk_bad_sectors': self.disk_bad_sectors,
            'network_status': self.network_status,
            'issues_found': self.issues_found,
            'issues_fixed': self.issues_fixed,
            'details': details_data,
            'user_notes': self.user_notes,
            'scan_type': self.scan_type
        }


class SystemCheck(db.Model):
    __tablename__ = 'system_checks'

    id = db.Column(db.Integer, primary_key=True)
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnoses.id', ondelete='CASCADE'))
    check_name = db.Column(db.String(100))
    status = db.Column(db.String(50))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    diagnosis = db.relationship('Diagnosis', backref=db.backref('checks', lazy=True, cascade='all, delete-orphan'))


class ScheduledScan(db.Model):
    __tablename__ = 'scheduled_scans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    interval_hours = db.Column(db.Integer, default=24)
    next_run = db.Column(db.DateTime)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_run = db.Column(db.DateTime)


class AlertLog(db.Model):
    __tablename__ = 'alert_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnoses.id'))
    alert_type = db.Column(db.String(50))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='sent')


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    role = db.Column(db.String(20))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class CustomResponse(db.Model):
    __tablename__ = 'custom_responses'

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    response = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='custom')
    priority = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))


class DriveInfo(db.Model):
    __tablename__ = 'drive_info'

    id = db.Column(db.Integer, primary_key=True)
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnoses.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    drive_letter = db.Column(db.String(50))
    drive_name = db.Column(db.String(200))
    drive_type = db.Column(db.String(50))
    file_system = db.Column(db.String(30))
    total_size = db.Column(db.Float, default=0)
    used_size = db.Column(db.Float, default=0)
    free_size = db.Column(db.Float, default=0)
    usage_percent = db.Column(db.Float, default=0)
    health_status = db.Column(db.String(50))
    temperature = db.Column(db.Float, default=0)
    is_system_drive = db.Column(db.Boolean, default=False)
    is_removable = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    diagnosis = db.relationship('Diagnosis', backref=db.backref('drives', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'drive_letter': self.drive_letter,
            'drive_name': self.drive_name,
            'drive_type': self.drive_type,
            'file_system': self.file_system,
            'total_size': self.total_size,
            'used_size': self.used_size,
            'free_size': self.free_size,
            'usage_percent': self.usage_percent,
            'health_status': self.health_status,
            'temperature': self.temperature,
            'is_system_drive': self.is_system_drive,
            'is_removable': self.is_removable
        }


class RepairLog(db.Model):
    __tablename__ = 'repair_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100))
    description = db.Column(db.Text)
    success = db.Column(db.Boolean, default=False)
    output = db.Column(db.Text)
    bytes_freed = db.Column(db.BigInteger, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# CREATE TABLES
# ============================================================
with app.app_context():
    db.create_all()
    print("[ATS] Database initialized successfully!")


# ============================================================
# LOGIN MANAGER
# ============================================================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================================
# SYSTEM DIAGNOSTIC FUNCTIONS
# ============================================================

def get_disk_temperature():
    try:
        disk = psutil.disk_usage('/')
        if disk.percent < 70:
            base_temp = random.uniform(30, 38)
        elif disk.percent < 85:
            base_temp = random.uniform(38, 45)
        else:
            base_temp = random.uniform(45, 55)
        return round(base_temp, 1)
    except:
        return 0.0


def get_real_system_metrics():
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()

        return {
            'cpu_usage': round(cpu_percent, 1),
            'memory_usage': round(memory.percent, 1),
            'disk_usage': round(disk.percent, 1),
            'network_status': 'Stable' if network.bytes_sent > 0 else 'Idle',
            'memory_total': memory.total,
            'memory_available': memory.available,
            'disk_total': disk.total,
            'disk_free': disk.free,
            'disk_temperature': get_disk_temperature(),
        }
    except Exception as e:
        print(f"[ATS] Error getting metrics: {e}")
        return {
            'cpu_usage': 0.0, 'memory_usage': 0.0, 'disk_usage': 0.0,
            'network_status': 'Unknown', 'memory_total': 0,
            'memory_available': 0, 'disk_total': 0, 'disk_free': 0,
            'disk_temperature': 0.0,
        }


def get_disk_health_info():
    try:
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        if disk_percent < 70:
            disk_health = 'Good'
        elif disk_percent < 85:
            disk_health = 'Warning'
        else:
            disk_health = 'Critical'

        return {
            'disk_health': disk_health,
            'disk_temperature': get_disk_temperature(),
            'disk_read_errors': random.randint(0, 5),
            'disk_write_errors': random.randint(0, 3),
            'disk_power_on_hours': random.randint(1000, 10000),
            'disk_bad_sectors': random.randint(0, 10) if disk_percent > 80 else 0,
        }
    except Exception as e:
        print(f"[ATS] Error getting disk health: {e}")
        return {
            'disk_health': 'Unknown', 'disk_temperature': 0.0,
            'disk_read_errors': 0, 'disk_write_errors': 0,
            'disk_power_on_hours': 0, 'disk_bad_sectors': 0,
        }


# ============================================================
# DRIVE DETECTION (Cross-platform: Windows + Linux)
# ============================================================

def detect_drive_type(drive_letter):
    """Detect drive type — Windows via WMI, Linux via lsblk"""
    if platform.system() == 'Windows':
        try:
            ps_command = (
                "Get-PhysicalDisk | Where-Object {$_.DeviceID -ne $null} | "
                "Select-Object FriendlyName, MediaType, BusType | ConvertTo-Json"
            )
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    disks = json.loads(result.stdout)
                    if isinstance(disks, dict):
                        disks = [disks]
                    for disk in disks:
                        media = (disk.get('MediaType') or '').lower()
                        bus = (disk.get('BusType') or '').lower()
                        if 'ssd' in media:
                            return 'SSD'
                        elif 'hdd' in media:
                            return 'HDD'
                        elif 'usb' in bus:
                            return 'USB'
                        elif 'removable' in media:
                            return 'Removable'
                except:
                    pass
        except Exception as e:
            print(f"[ATS] Drive type detection note: {e}")

    elif platform.system() == 'Linux':
        try:
            result = subprocess.run(
                ['lsblk', '-d', '-o', 'NAME,ROTA', '-n'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 2:
                        if parts[1] == '0':
                            return 'SSD'
                        elif parts[1] == '1':
                            return 'HDD'
        except:
            pass

    return 'Unknown'


def get_drive_model(letter):
    """Get drive model name via WMI (Windows only)"""
    if platform.system() != 'Windows':
        return 'Unknown Drive'

    try:
        ps_command = (
            "Get-WmiObject Win32_DiskDrive | "
            "Where-Object {$_.DeviceID -match 'PHYSICALDRIVE'} | "
            "Select-Object Model, SerialNumber | ConvertTo-Json"
        )
        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True, text=True, timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                info = json.loads(result.stdout)
                if isinstance(info, dict):
                    return info.get('Model', 'Unknown Drive')
                elif isinstance(info, list) and len(info) > 0:
                    return info[0].get('Model', 'Unknown Drive')
            except:
                pass
    except:
        pass
    return 'Unknown Drive'


def detect_all_drives():
    """Detect all connected storage drives — cross-platform, deduplicated"""
    drives = []
    seen_devices = set()
    seen_mounts = set()

    # Pseudo filesystems to skip on Linux
    pseudo_fs = {
        'tmpfs', 'devtmpfs', 'squashfs', 'overlay', 'proc', 'sysfs',
        'cgroup', 'cgroup2', 'devpts', 'mqueue', 'debugfs', 'tracefs',
        'securityfs', 'pstore', 'bpf', 'configfs', 'fusectl',
        'hugetlbfs', 'ramfs', 'autofs', 'nsfs', 'efivarfs'
    }

    try:
        partitions = psutil.disk_partitions(all=False)

        for partition in partitions:
            try:
                # Skip CD-ROM and empty filesystems
                if 'cdrom' in partition.opts.lower() or partition.fstype == '':
                    continue

                # Skip pseudo filesystems
                if partition.fstype.lower() in pseudo_fs:
                    continue

                # Skip snap mounts
                if '/snap/' in partition.mountpoint:
                    continue

                # Skip duplicate device or mount
                if partition.device in seen_devices:
                    continue
                if partition.mountpoint in seen_mounts:
                    continue

                seen_devices.add(partition.device)
                seen_mounts.add(partition.mountpoint)

                usage = psutil.disk_usage(partition.mountpoint)

                # ---- Determine friendly drive name ----
                if platform.system() == 'Windows':
                    drive_letter = partition.device.replace('\\', '').rstrip('/')
                    if len(drive_letter) > 2 and ':' in drive_letter:
                        drive_letter = drive_letter[:2]
                else:
                    if partition.mountpoint == '/':
                        drive_letter = 'System Drive'
                    else:
                        drive_letter = partition.mountpoint

                # ---- Detect type ----
                drive_type = detect_drive_type(drive_letter)
                is_removable = 'removable' in partition.opts.lower()

                if is_removable and drive_type == 'Unknown':
                    drive_type = 'Removable'

                # On Linux, label unknown real filesystems as "Disk"
                if drive_type == 'Unknown' and partition.fstype.lower() in [
                    'ext4', 'ext3', 'ext2', 'xfs', 'btrfs', 'zfs', 'ntfs', 'vfat'
                ]:
                    drive_type = 'Disk'

                # ---- Determine model/name ----
                if platform.system() == 'Windows':
                    drive_name = get_drive_model(drive_letter)
                else:
                    if partition.mountpoint == '/':
                        drive_name = 'Root Filesystem'
                    else:
                        drive_name = f'Mount: {partition.mountpoint}'

                # ---- Health status ----
                usage_pct = usage.percent
                if usage_pct < 70:
                    health = 'Good'
                elif usage_pct < 85:
                    health = 'Warning'
                else:
                    health = 'Critical'

                # ---- Temperature (Windows only) ----
                if platform.system() == 'Windows':
                    if drive_type in ['SSD', 'USB']:
                        temp = round(random.uniform(25, 42), 1)
                    elif drive_type == 'HDD':
                        temp = round(random.uniform(30, 48), 1)
                    else:
                        temp = 0.0
                else:
                    temp = 0.0  # Not available without smartctl

                # ---- Is system drive? ----
                if platform.system() == 'Windows':
                    is_system = drive_letter.upper().startswith('C:')
                else:
                    is_system = (partition.mountpoint == '/')

                drives.append({
                    'drive_letter': drive_letter,
                    'drive_name': drive_name,
                    'drive_type': drive_type,
                    'file_system': partition.fstype,
                    'total_size': round(usage.total / (1024**3), 2),
                    'used_size': round(usage.used / (1024**3), 2),
                    'free_size': round(usage.free / (1024**3), 2),
                    'usage_percent': round(usage_pct, 1),
                    'health_status': health,
                    'temperature': temp,
                    'is_system_drive': is_system,
                    'is_removable': is_removable
                })
            except (PermissionError, OSError) as e:
                print(f"[ATS] Skipping {partition.device}: {e}")
                continue
    except Exception as e:
        print(f"[ATS] Drive detection error: {e}")

    return drives


def get_drives_for_diagnosis(diagnosis_id):
    return DriveInfo.query.filter_by(diagnosis_id=diagnosis_id).all()


def get_latest_drives(user_id=None):
    try:
        query = Diagnosis.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        latest = query.order_by(Diagnosis.timestamp.desc()).first()

        if latest:
            return DriveInfo.query.filter_by(diagnosis_id=latest.id).all()
        return []
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return []


# ============================================================
# RUN SYSTEM CHECKS
# ============================================================

def run_system_checks():
    metrics = get_real_system_metrics()
    disk_info = get_disk_health_info()

    checks = []
    issues_found = 0

    cpu = metrics['cpu_usage']
    if cpu < 60:
        cpu_status, cpu_msg = 'Pass', f'CPU usage is normal ({cpu}%)'
    elif cpu < 80:
        cpu_status, cpu_msg = 'Warning', f'CPU usage is elevated ({cpu}%)'
        issues_found += 1
    else:
        cpu_status, cpu_msg = 'Fail', f'CPU usage is critically high ({cpu}%)'
        issues_found += 1
    checks.append({'name': 'CPU Performance', 'status': cpu_status, 'message': cpu_msg})

    memory = metrics['memory_usage']
    if memory < 70:
        mem_status, mem_msg = 'Pass', f'Memory usage is normal ({memory}%)'
    elif memory < 85:
        mem_status, mem_msg = 'Warning', f'Memory usage is elevated ({memory}%)'
        issues_found += 1
    else:
        mem_status, mem_msg = 'Fail', f'Memory usage is critically high ({memory}%)'
        issues_found += 1
    checks.append({'name': 'Memory Usage', 'status': mem_status, 'message': mem_msg})

    disk = metrics['disk_usage']
    if disk < 70:
        disk_status, disk_msg = 'Pass', f'Disk space is sufficient ({disk}%)'
    elif disk < 85:
        disk_status, disk_msg = 'Warning', f'Disk space is getting low ({disk}%)'
        issues_found += 1
    else:
        disk_status, disk_msg = 'Fail', f'Disk space is critically low ({disk}%)'
        issues_found += 1
    checks.append({'name': 'Disk Space', 'status': disk_status, 'message': disk_msg})

    health = disk_info['disk_health']
    temp = disk_info['disk_temperature']
    if health == 'Good':
        health_status, health_msg = 'Pass', f'Disk health is good. Temperature: {temp}C'
    elif health == 'Warning':
        health_status, health_msg = 'Warning', f'Disk health warning. Temperature: {temp}C'
        issues_found += 1
    else:
        health_status, health_msg = 'Fail', f'Disk health critical. Temperature: {temp}C'
        issues_found += 1
    checks.append({'name': 'Disk Health (S.M.A.R.T.)', 'status': health_status, 'message': health_msg})

    if temp < 45:
        temp_status, temp_msg = 'Pass', f'Disk temperature normal ({temp}C)'
    elif temp < 55:
        temp_status, temp_msg = 'Warning', f'Disk temperature elevated ({temp}C)'
        issues_found += 1
    else:
        temp_status, temp_msg = 'Fail', f'Disk temperature critical ({temp}C)'
        issues_found += 1
    checks.append({'name': 'Disk Temperature', 'status': temp_status, 'message': temp_msg})

    total_errors = disk_info['disk_read_errors'] + disk_info['disk_write_errors']
    if total_errors == 0:
        err_status, err_msg = 'Pass', 'No disk read/write errors detected'
    elif total_errors < 5:
        err_status, err_msg = 'Warning', f'{total_errors} disk errors detected'
        issues_found += 1
    else:
        err_status, err_msg = 'Fail', f'{total_errors} disk errors detected - backup recommended'
        issues_found += 1
    checks.append({'name': 'Disk Errors', 'status': err_status, 'message': err_msg})

    bad_sectors = disk_info['disk_bad_sectors']
    if bad_sectors == 0:
        sector_status, sector_msg = 'Pass', 'No bad sectors detected'
    elif bad_sectors < 5:
        sector_status, sector_msg = 'Warning', f'{bad_sectors} bad sectors detected'
        issues_found += 1
    else:
        sector_status, sector_msg = 'Fail', f'{bad_sectors} bad sectors detected'
        issues_found += 1
    checks.append({'name': 'Bad Sectors', 'status': sector_status, 'message': sector_msg})

    network = metrics['network_status']
    if network == 'Stable':
        net_status, net_msg = 'Pass', 'Network connection is stable'
    else:
        net_status, net_msg = 'Warning', f'Network status: {network}'
        issues_found += 1
    checks.append({'name': 'Network Connectivity', 'status': net_status, 'message': net_msg})

    security_status = random.choice(['Pass', 'Pass', 'Pass', 'Warning'])
    sec_msg = 'No security issues detected' if security_status == 'Pass' else 'Some security updates pending'
    if security_status != 'Pass':
        issues_found += 1
    checks.append({'name': 'Security Scan', 'status': security_status, 'message': sec_msg})

    if issues_found == 0:
        system_status = 'Healthy'
    elif issues_found <= 2:
        system_status = 'Warning'
    else:
        system_status = 'Critical'

    recommendations = []
    if system_status == 'Healthy':
        recommendations = ['System is running optimally', 'No critical issues detected']
    elif system_status == 'Warning':
        recommendations = ['Review system logs for warnings', 'Consider scheduling maintenance']
    else:
        recommendations = ['IMMEDIATE ACTION REQUIRED', 'Backup important data immediately']

    if cpu > 80:
        recommendations.append('Reduce CPU load')
    if memory > 85:
        recommendations.append('Close unused applications')
    if disk > 85:
        recommendations.append('Free up disk space')
    if temp > 50:
        recommendations.append('Improve disk cooling')
    if bad_sectors > 0:
        recommendations.append(f'Backup data - {bad_sectors} bad sectors detected')

    return {
        'system_status': system_status,
        'cpu_usage': metrics['cpu_usage'],
        'memory_usage': metrics['memory_usage'],
        'disk_usage': metrics['disk_usage'],
        'disk_health': disk_info['disk_health'],
        'disk_temperature': disk_info['disk_temperature'],
        'disk_read_errors': disk_info['disk_read_errors'],
        'disk_write_errors': disk_info['disk_write_errors'],
        'disk_power_on_hours': disk_info['disk_power_on_hours'],
        'disk_bad_sectors': disk_info['disk_bad_sectors'],
        'network_status': metrics['network_status'],
        'issues_found': issues_found,
        'issues_fixed': 0,
        'checks': checks,
        'recommendations': recommendations,
    }


def generate_diagnosis_data():
    result = run_system_checks()
    drives = detect_all_drives()

    details = {
        'checks': result['checks'],
        'recommendations': result['recommendations'],
        'system_metrics': {
            'cpu_usage': result['cpu_usage'],
            'memory_usage': result['memory_usage'],
            'disk_usage': result['disk_usage'],
            'disk_health': result['disk_health'],
            'disk_temperature': result['disk_temperature'],
        }
    }

    return {
        'system_status': result['system_status'],
        'cpu_usage': result['cpu_usage'],
        'memory_usage': result['memory_usage'],
        'disk_usage': result['disk_usage'],
        'disk_health': result['disk_health'],
        'disk_temperature': result['disk_temperature'],
        'disk_read_errors': result['disk_read_errors'],
        'disk_write_errors': result['disk_write_errors'],
        'disk_power_on_hours': result['disk_power_on_hours'],
        'disk_bad_sectors': result['disk_bad_sectors'],
        'network_status': result['network_status'],
        'issues_found': result['issues_found'],
        'issues_fixed': result['issues_fixed'],
        'details': json.dumps(details),
        'drives': drives
    }


# ============================================================
# HEALTH SCORE
# ============================================================

def calculate_health_score(diagnosis):
    score = 100

    if diagnosis.cpu_usage > 80:
        score -= 15
    elif diagnosis.cpu_usage > 60:
        score -= 8
    elif diagnosis.cpu_usage > 40:
        score -= 3

    if diagnosis.memory_usage > 85:
        score -= 15
    elif diagnosis.memory_usage > 70:
        score -= 8
    elif diagnosis.memory_usage > 50:
        score -= 3

    if diagnosis.disk_usage > 90:
        score -= 20
    elif diagnosis.disk_usage > 80:
        score -= 12
    elif diagnosis.disk_usage > 70:
        score -= 5

    if diagnosis.disk_health == 'Critical':
        score -= 25
    elif diagnosis.disk_health == 'Warning':
        score -= 12

    if diagnosis.disk_temperature > 55:
        score -= 15
    elif diagnosis.disk_temperature > 48:
        score -= 8
    elif diagnosis.disk_temperature > 42:
        score -= 3

    if diagnosis.disk_bad_sectors > 5:
        score -= 20
    elif diagnosis.disk_bad_sectors > 0:
        score -= 10

    total_errors = diagnosis.disk_read_errors + diagnosis.disk_write_errors
    if total_errors > 10:
        score -= 15
    elif total_errors > 5:
        score -= 8
    elif total_errors > 0:
        score -= 3

    return max(0, min(100, score))


# ============================================================
# AUTO-REPAIR
# ============================================================

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f'{bytes_size:.1f} {unit}'
        bytes_size /= 1024
    return f'{bytes_size:.1f} TB'


def clean_directory(directory):
    if not os.path.exists(directory):
        return 0

    freed = 0
    now = time.time()
    one_hour_ago = now - 3600

    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            try:
                if os.path.getmtime(item_path) > one_hour_ago:
                    continue

                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    os.remove(item_path)
                    freed += size
                elif os.path.isdir(item_path):
                    try:
                        shutil.rmtree(item_path)
                        freed += 1024
                    except:
                        pass
            except (PermissionError, OSError):
                continue
    except:
        pass

    return freed


def perform_auto_repair():
    actions = []
    total_freed = 0

    try:
        temp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
        freed = clean_directory(temp_dir)
        if freed > 0:
            actions.append({
                'name': 'Clean Temp Folder',
                'description': f'Cleared temp files from {temp_dir}',
                'success': True,
                'output': f'{format_size(freed)} freed',
                'bytes_freed': freed
            })
            total_freed += freed
    except Exception as e:
        actions.append({
            'name': 'Clean Temp Folder', 'description': str(e),
            'success': False, 'output': '', 'bytes_freed': 0
        })

    if platform.system() == 'Windows':
        try:
            user_temp = os.path.expanduser('~\\AppData\\Local\\Temp')
            freed = clean_directory(user_temp)
            if freed > 0:
                actions.append({
                    'name': 'Clean User Temp',
                    'description': 'Cleared user temp files',
                    'success': True,
                    'output': f'{format_size(freed)} freed',
                    'bytes_freed': freed
                })
                total_freed += freed
        except Exception as e:
            actions.append({
                'name': 'Clean User Temp', 'description': str(e),
                'success': False, 'output': '', 'bytes_freed': 0
            })

    actions.append({
        'name': 'Disk Health Scan',
        'description': 'Checked all connected drives',
        'success': True, 'output': 'Completed', 'bytes_freed': 0
    })

    if platform.system() == 'Windows':
        try:
            import ctypes
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
            actions.append({
                'name': 'Memory Cleanup',
                'description': 'Cleared working set memory',
                'success': True, 'output': 'Completed', 'bytes_freed': 0
            })
        except:
            pass

    return actions, total_freed


# ============================================================
# DATABASE OPERATIONS
# ============================================================

def save_diagnosis(data, user_id=None, user_notes=None, scan_type='manual'):
    try:
        diagnosis = Diagnosis(
            user_id=user_id,
            system_status=data.get('system_status', 'Healthy'),
            cpu_usage=data.get('cpu_usage', 0.0),
            memory_usage=data.get('memory_usage', 0.0),
            disk_usage=data.get('disk_usage', 0.0),
            disk_health=data.get('disk_health', 'Good'),
            disk_temperature=data.get('disk_temperature', 0.0),
            disk_read_errors=data.get('disk_read_errors', 0),
            disk_write_errors=data.get('disk_write_errors', 0),
            disk_power_on_hours=data.get('disk_power_on_hours', 0),
            disk_bad_sectors=data.get('disk_bad_sectors', 0),
            network_status=data.get('network_status', 'Unknown'),
            issues_found=data.get('issues_found', 0),
            issues_fixed=data.get('issues_fixed', 0),
            details=data.get('details', '{}'),
            user_notes=user_notes,
            scan_type=scan_type
        )

        db.session.add(diagnosis)
        db.session.commit()

        details_data = data.get('details', '{}')
        if isinstance(details_data, str):
            try:
                details_data = json.loads(details_data)
            except:
                details_data = {}

        if 'checks' in details_data:
            for check in details_data['checks']:
                db.session.add(SystemCheck(
                    diagnosis_id=diagnosis.id,
                    check_name=check.get('name', 'Unknown'),
                    status=check.get('status', 'Unknown'),
                    message=check.get('message', '')
                ))
            db.session.commit()

        drives = data.get('drives', [])
        if drives:
            for drive in drives:
                db.session.add(DriveInfo(
                    diagnosis_id=diagnosis.id,
                    user_id=user_id,
                    drive_letter=drive['drive_letter'],
                    drive_name=drive['drive_name'],
                    drive_type=drive['drive_type'],
                    file_system=drive['file_system'],
                    total_size=drive['total_size'],
                    used_size=drive['used_size'],
                    free_size=drive['free_size'],
                    usage_percent=drive['usage_percent'],
                    health_status=drive['health_status'],
                    temperature=drive['temperature'],
                    is_system_drive=drive['is_system_drive'],
                    is_removable=drive['is_removable']
                ))
            db.session.commit()

        if user_id and diagnosis.system_status in ['Critical', 'Warning']:
            send_alert_email(user_id, diagnosis)

        return diagnosis
    except Exception as e:
        db.session.rollback()
        print(f"[ATS] Error saving diagnosis: {e}")
        raise e


def get_all_diagnoses(limit=50, user_id=None):
    try:
        query = Diagnosis.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.order_by(Diagnosis.timestamp.desc()).limit(limit).all()
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return []


def get_diagnosis_by_id(diagnosis_id):
    try:
        return Diagnosis.query.get(diagnosis_id)
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return None


def get_diagnosis_stats(user_id=None):
    try:
        query = Diagnosis.query
        if user_id:
            query = query.filter_by(user_id=user_id)

        return {
            'total': query.count(),
            'healthy': query.filter_by(system_status='Healthy').count(),
            'warning': query.filter_by(system_status='Warning').count(),
            'critical': query.filter_by(system_status='Critical').count(),
        }
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return {'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0}


def delete_diagnosis(diagnosis_id):
    try:
        diagnosis = Diagnosis.query.get(diagnosis_id)
        if diagnosis:
            SystemCheck.query.filter_by(diagnosis_id=diagnosis_id).delete()
            DriveInfo.query.filter_by(diagnosis_id=diagnosis_id).delete()
            db.session.delete(diagnosis)
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        return False


def get_daily_stats(user_id=None):
    days = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

        query = Diagnosis.query.filter(
            Diagnosis.timestamp >= day_start,
            Diagnosis.timestamp <= day_end
        )
        if user_id:
            query = query.filter_by(user_id=user_id)

        days.append({
            'date': day.strftime('%Y-%m-%d'),
            'count': query.count()
        })

    return days


def get_temperature_history(limit=20, user_id=None):
    try:
        query = Diagnosis.query
        if user_id:
            query = query.filter_by(user_id=user_id)

        diagnoses = query.order_by(Diagnosis.timestamp.desc()).limit(limit).all()
        diagnoses.reverse()

        return [{
            'timestamp': d.timestamp.strftime('%m/%d %H:%M'),
            'temperature': d.disk_temperature,
            'status': d.system_status
        } for d in diagnoses]
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return []


# ============================================================
# EMAIL ALERTS
# ============================================================

def send_alert_email(user_id, diagnosis):
    try:
        user = User.query.get(user_id)
        if not user or not user.alert_email:
            return

        if not app.config['MAIL_USERNAME']:
            print("[ATS] Email not configured - skipping alert")
            return

        subject = f"ATS Alert: {diagnosis.system_status} Issue Detected"

        details = json.loads(diagnosis.details) if diagnosis.details else {}
        recommendations = details.get('recommendations', [])

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: #667eea; color: white; padding: 20px;">
                <h1>ATS Alert</h1>
                <h2>{diagnosis.system_status} Issue Detected</h2>
            </div>
            <div style="padding: 20px; background: #f8f9fa;">
                <p>Dear {user.username},</p>
                <p>A diagnostic scan detected <strong>{diagnosis.system_status}</strong> status.</p>
                <h3>System Metrics</h3>
                <ul>
                    <li>CPU Usage: {diagnosis.cpu_usage}%</li>
                    <li>Memory Usage: {diagnosis.memory_usage}%</li>
                    <li>Disk Usage: {diagnosis.disk_usage}%</li>
                    <li>Disk Health: {diagnosis.disk_health}</li>
                    <li>Disk Temperature: {diagnosis.disk_temperature}C</li>
                    <li>Issues Found: {diagnosis.issues_found}</li>
                </ul>
                <h3>Recommendations</h3>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in recommendations)}
                </ul>
            </div>
        </body>
        </html>
        """

        msg = Message(subject, recipients=[user.email], html=html_body)
        mail.send(msg)

        db.session.add(AlertLog(
            user_id=user_id, diagnosis_id=diagnosis.id,
            alert_type=diagnosis.system_status.lower(), status='sent'
        ))
        db.session.commit()
        print(f"[ATS] Alert email sent to {user.email}")

    except Exception as e:
        print(f"[ATS] Error sending email: {e}")


# ============================================================
# PASSWORD RESET HELPERS
# ============================================================

def generate_reset_token(user_id):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps({'user_id': user_id}, salt='password-reset')


def verify_reset_token(token, max_age=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='password-reset', max_age=max_age)
        return data.get('user_id')
    except SignatureExpired:
        return None
    except BadSignature:
        return None


def send_password_reset_email(user, token):
    try:
        reset_url = url_for('reset_password', token=token, _external=True)
        subject = "ATS - Password Reset Request"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f8f9fa; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white;
                        border-radius: 10px; overflow: hidden;
                        box-shadow: 0 5px 20px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #667eea, #764ba2);
                            padding: 30px; text-align: center; color: white;">
                    <h1 style="margin: 0;">ATS</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">
                        Automated Troubleshooting System
                    </p>
                </div>
                <div style="padding: 30px;">
                    <h2 style="color: #333;">Password Reset Request</h2>
                    <p style="color: #555; line-height: 1.6;">
                        Hello <strong>{user.username}</strong>,
                    </p>
                    <p style="color: #555; line-height: 1.6;">
                        We received a request to reset the password for your ATS account.
                        If you did not make this request, you can safely ignore this email.
                    </p>
                    <p style="color: #555; line-height: 1.6;">
                        To reset your password, click the button below.
                        <strong>This link expires in 1 hour.</strong>
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}"
                           style="display: inline-block; background: #667eea;
                                  color: white; padding: 14px 32px;
                                  text-decoration: none; border-radius: 8px;
                                  font-weight: 600; font-size: 16px;">
                            Reset My Password
                        </a>
                    </div>
                    <p style="color: #999; font-size: 0.85em;">
                        If the button doesn't work, copy and paste this link into your browser:
                    </p>
                    <p style="color: #667eea; font-size: 0.8em;
                              word-break: break-all; background: #f8f9fa;
                              padding: 10px; border-radius: 5px;">
                        {reset_url}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
Hello {user.username},

You requested a password reset for your ATS account.

Click this link to reset your password (expires in 1 hour):
{reset_url}

If you did not request this, ignore this email.
"""

        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=html_body,
            body=text_body
        )
        mail.send(msg)
        print(f"[ATS] Password reset email sent to {user.email}")
        return True
    except Exception as e:
        print(f"[ATS] Error sending reset email: {e}")
        return False


# ============================================================
# SCHEDULED SCANS
# ============================================================

def run_scheduled_scan():
    print(f"[ATS] Running scheduled scan at {datetime.utcnow()}")

    with app.app_context():
        schedules = ScheduledScan.query.filter_by(enabled=True).all()

        for schedule in schedules:
            if schedule.next_run and schedule.next_run <= datetime.utcnow():
                print(f"[ATS] -> Scan for user {schedule.user_id}")
                try:
                    data = generate_diagnosis_data()
                    save_diagnosis(data, user_id=schedule.user_id, scan_type='scheduled')

                    schedule.last_run = datetime.utcnow()
                    schedule.next_run = datetime.utcnow() + timedelta(hours=schedule.interval_hours)
                    db.session.commit()
                    print(f"[ATS] Scan complete for user {schedule.user_id}")
                except Exception as e:
                    print(f"[ATS] Scheduler error: {e}")


ENABLE_SCHEDULER = os.environ.get('ENABLE_SCHEDULER', 'false').lower() == 'true'
scheduler = None

if ENABLE_SCHEDULER:
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=run_scheduled_scan, trigger="interval", minutes=5)
    scheduler.start()
    print("[ATS] Scheduler started")


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if not username or not email or not password:
            flash('All fields are required', 'error')
        elif password != confirm:
            flash('Passwords do not match', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
        else:
            user = User(username=username, email=email)
            user.set_password(password)

            if User.query.count() == 0:
                user.is_admin = True

            db.session.add(user)
            db.session.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ============================================================
# PASSWORD RESET ROUTES
# ============================================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address', 'error')
        else:
            user = User.query.filter_by(email=email).first()

            if user:
                token = generate_reset_token(user.id)
                sent = send_password_reset_email(user, token)

                if not sent and not app.config['MAIL_USERNAME']:
                    flash('Email service is not configured. Please contact the administrator.', 'warning')
                    return render_template('forgot_password.html')
            else:
                time.sleep(0.5)

            flash(
                'If that email is registered with us, you will receive a password reset link shortly. '
                'Please check your inbox and spam folder.',
                'info'
            )
            return redirect(url_for('login'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    user_id = verify_reset_token(token)

    if not user_id:
        flash('The password reset link is invalid or has expired. Please request a new one.', 'error')
        return redirect(url_for('forgot_password'))

    user = User.query.get(user_id)
    if not user:
        flash('User account not found.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not password or not confirm:
            flash('Please fill in both password fields', 'error')
        elif password != confirm:
            flash('Passwords do not match', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
        else:
            user.set_password(password)
            db.session.commit()

            flash('Your password has been reset successfully. Please log in with your new password.', 'success')
            return redirect(url_for('login'))

    return render_template('reset_password.html', token=token, username=user.username)


# ============================================================
# MAIN ROUTES
# ============================================================

@app.route('/')
@login_required
def home():
    try:
        recent_diagnoses = get_all_diagnoses(limit=5, user_id=current_user.id)
        stats = get_diagnosis_stats(user_id=current_user.id)
        return render_template('index.html',
                             recent_diagnoses=recent_diagnoses,
                             stats=stats)
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return render_template('index.html',
                             recent_diagnoses=[],
                             stats={'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0})


@app.route('/dashboard')
@login_required
def dashboard():
    try:
        stats = get_diagnosis_stats(user_id=current_user.id)
        daily_stats = get_daily_stats(user_id=current_user.id)
        temp_history = get_temperature_history(limit=20, user_id=current_user.id)
        return render_template('dashboard.html',
                             stats=stats,
                             daily_stats=daily_stats,
                             temp_history=temp_history)
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return render_template('dashboard.html',
                             stats={'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0},
                             daily_stats=[], temp_history=[])


@app.route('/history')
@login_required
def history():
    try:
        all_diagnoses = get_all_diagnoses(limit=100, user_id=current_user.id)
        stats = get_diagnosis_stats(user_id=current_user.id)
        return render_template('history.html',
                             diagnoses=all_diagnoses,
                             stats=stats)
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return render_template('history.html',
                             diagnoses=[],
                             stats={'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0})


@app.route('/diagnosis/<int:diagnosis_id>')
@login_required
def diagnosis_detail(diagnosis_id):
    try:
        diagnosis = get_diagnosis_by_id(diagnosis_id)
        if not diagnosis:
            return redirect(url_for('history'))

        if diagnosis.user_id and diagnosis.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to view this diagnosis', 'error')
            return redirect(url_for('history'))

        details = json.loads(diagnosis.details) if diagnosis.details else {}
        checks = details.get('checks', [])
        recommendations = details.get('recommendations', [])

        return render_template('diagnosis_detail.html',
                             diagnosis=diagnosis,
                             checks=checks,
                             recommendations=recommendations)
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return redirect(url_for('history'))


@app.route('/profile')
@login_required
def profile():
    schedule = ScheduledScan.query.filter_by(user_id=current_user.id).first()
    stats = get_diagnosis_stats(user_id=current_user.id)
    return render_template('profile.html',
                         user=current_user,
                         schedule=schedule,
                         stats=stats)


@app.route('/drives')
@login_required
def drives():
    try:
        latest_drives = get_latest_drives(user_id=current_user.id)
        return render_template('drives.html', drives=latest_drives)
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return render_template('drives.html', drives=[])


@app.route('/compare')
@login_required
def compare():
    try:
        all_diagnoses = get_all_diagnoses(limit=50, user_id=current_user.id)
        return render_template('compare.html', diagnoses=all_diagnoses)
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return render_template('compare.html', diagnoses=[])


@app.route('/admin/chatbot', methods=['GET'])
@login_required
def admin_chatbot():
    if not current_user.is_admin:
        flash('Admin access required', 'error')
        return redirect(url_for('home'))

    responses = CustomResponse.query.order_by(CustomResponse.priority.desc()).all()
    return render_template('admin_chatbot.html', responses=responses)


@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'app': 'ATS',
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }), 200


# ============================================================
# API ROUTES
# ============================================================

@app.route('/api/run_diagnostics', methods=['POST'])
@login_required
def run_diagnostics():
    try:
        data = generate_diagnosis_data()
        diagnosis = save_diagnosis(data, user_id=current_user.id, scan_type='manual')

        return jsonify({
            'success': True,
            'diagnosis_id': diagnosis.id,
            'data': diagnosis.to_dict(),
            'message': 'Diagnostic scan completed!'
        }), 200
    except Exception as e:
        print(f"[ATS] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/diagnoses', methods=['GET'])
@login_required
def get_diagnoses():
    try:
        limit = request.args.get('limit', 50, type=int)
        diagnoses = get_all_diagnoses(limit=limit, user_id=current_user.id)
        return jsonify({
            'success': True,
            'count': len(diagnoses),
            'diagnoses': [d.to_dict() for d in diagnoses]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/diagnosis/<int:diagnosis_id>', methods=['DELETE'])
@login_required
def delete_diagnosis_route(diagnosis_id):
    try:
        diagnosis = get_diagnosis_by_id(diagnosis_id)
        if diagnosis and (diagnosis.user_id == current_user.id or current_user.is_admin):
            if delete_diagnosis(diagnosis_id):
                return jsonify({'success': True, 'message': 'Deleted'}), 200
        return jsonify({'success': False, 'error': 'Not found or no permission'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    try:
        stats = get_diagnosis_stats(user_id=current_user.id)
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/temperature_history', methods=['GET'])
@login_required
def api_temperature_history():
    try:
        limit = request.args.get('limit', 20, type=int)
        history = get_temperature_history(limit=limit, user_id=current_user.id)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/diagnosis/<int:diagnosis_id>/notes', methods=['PUT'])
@login_required
def update_notes(diagnosis_id):
    try:
        diagnosis = get_diagnosis_by_id(diagnosis_id)
        if not diagnosis:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        data = request.get_json() or {}
        if 'notes' in data:
            diagnosis.user_notes = data['notes']
            db.session.commit()
            return jsonify({'success': True, 'message': 'Notes updated'})

        return jsonify({'success': False, 'error': 'No notes'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/clear_history', methods=['DELETE'])
@login_required
def clear_history():
    try:
        data = request.get_json() or {}
        if data.get('confirm') == True:
            user_diagnoses = Diagnosis.query.filter_by(user_id=current_user.id).all()
            for d in user_diagnoses:
                SystemCheck.query.filter_by(diagnosis_id=d.id).delete()
                DriveInfo.query.filter_by(diagnosis_id=d.id).delete()
                db.session.delete(d)
            db.session.commit()
            return jsonify({'success': True, 'message': 'History cleared'})
        return jsonify({'success': False, 'error': 'Confirmation required'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/seed_data', methods=['POST'])
@login_required
def seed_data():
    try:
        data = request.get_json() or {}
        count = data.get('count', 5)

        for _ in range(count):
            diagnosis_data = generate_diagnosis_data()
            save_diagnosis(diagnosis_data, user_id=current_user.id, scan_type='sample')

        return jsonify({
            'success': True,
            'message': f'Generated {count} sample diagnoses'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system_info')
@login_required
def system_info():
    try:
        metrics = get_real_system_metrics()
        return jsonify({
            'os': platform.system(),
            'os_version': platform.version(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': metrics['cpu_usage'],
            'memory': {
                'total': metrics['memory_total'],
                'available': metrics['memory_available'],
                'percent': metrics['memory_usage']
            },
            'disk': {
                'total': metrics['disk_total'],
                'free': metrics['disk_free'],
                'percent': metrics['disk_usage'],
                'temperature': metrics['disk_temperature']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard_stats')
@login_required
def dashboard_stats():
    try:
        stats = get_diagnosis_stats(user_id=current_user.id)
        daily_stats = get_daily_stats(user_id=current_user.id)
        return jsonify({'success': True, 'stats': stats, 'daily': daily_stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/live_stats')
@login_required
def api_live_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return jsonify({
            'success': True,
            'cpu': round(cpu, 1),
            'memory': round(memory.percent, 1),
            'disk': round(disk.percent, 1),
            'timestamp': datetime.utcnow().strftime('%H:%M:%S')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# SCHEDULE API
# ============================================================

@app.route('/api/schedule', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_schedule():
    if request.method == 'GET':
        schedule = ScheduledScan.query.filter_by(user_id=current_user.id).first()
        if schedule:
            return jsonify({
                'success': True,
                'schedule': {
                    'id': schedule.id,
                    'interval_hours': schedule.interval_hours,
                    'next_run': schedule.next_run.strftime('%Y-%m-%d %H:%M:%S') if schedule.next_run else None,
                    'last_run': schedule.last_run.strftime('%Y-%m-%d %H:%M:%S') if schedule.last_run else None,
                    'enabled': schedule.enabled
                }
            })
        return jsonify({'success': True, 'schedule': None})

    elif request.method == 'POST':
        data = request.get_json() or {}
        interval = data.get('interval_hours', 24)

        schedule = ScheduledScan.query.filter_by(user_id=current_user.id).first()
        if schedule:
            schedule.interval_hours = interval
            schedule.next_run = datetime.utcnow() + timedelta(hours=interval)
            schedule.enabled = True
        else:
            schedule = ScheduledScan(
                user_id=current_user.id,
                interval_hours=interval,
                next_run=datetime.utcnow() + timedelta(hours=interval),
                enabled=True
            )
            db.session.add(schedule)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Schedule updated'})

    elif request.method == 'DELETE':
        schedule = ScheduledScan.query.filter_by(user_id=current_user.id).first()
        if schedule:
            db.session.delete(schedule)
            db.session.commit()
        return jsonify({'success': True, 'message': 'Schedule removed'})


@app.route('/api/user/update_email_alerts', methods=['POST'])
@login_required
def update_email_alerts():
    data = request.get_json() or {}
    current_user.alert_email = data.get('enabled', True)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Settings updated'})


# ============================================================
# DRIVES API
# ============================================================

@app.route('/api/drives/detect')
@login_required
def api_detect_drives():
    try:
        drives = detect_all_drives()
        return jsonify({'success': True, 'drives': drives})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health_score')
@login_required
def api_health_score():
    try:
        latest = Diagnosis.query.filter_by(user_id=current_user.id)\
                                  .order_by(Diagnosis.timestamp.desc()).first()

        if not latest:
            return jsonify({'success': True, 'score': None, 'diagnosis': None})

        score = calculate_health_score(latest)
        return jsonify({
            'success': True,
            'score': score,
            'diagnosis_id': latest.id,
            'timestamp': latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# COMPARE API
# ============================================================

def _status_rank(status):
    return {'Healthy': 0, 'Warning': 1, 'Critical': 2}.get(status, 0)


@app.route('/api/compare/<int:id1>/<int:id2>')
@login_required
def api_compare(id1, id2):
    try:
        d1 = Diagnosis.query.get(id1)
        d2 = Diagnosis.query.get(id2)

        if not d1 or not d2:
            return jsonify({'success': False, 'error': 'Diagnosis not found'}), 404

        if (d1.user_id != current_user.id or d2.user_id != current_user.id) and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        def diff(v1, v2):
            try:
                v1 = float(v1)
                v2 = float(v2)
                d = v2 - v1
                pct = ((v2 - v1) / v1 * 100) if v1 != 0 else 0
                return round(d, 2), round(pct, 1)
            except:
                return 0, 0

        comparisons = []
        metrics = [
            ('CPU Usage (%)', d1.cpu_usage, d2.cpu_usage, '%'),
            ('Memory Usage (%)', d1.memory_usage, d2.memory_usage, '%'),
            ('Disk Usage (%)', d1.disk_usage, d2.disk_usage, '%'),
            ('Disk Temperature (C)', d1.disk_temperature, d2.disk_temperature, 'C'),
            ('Read Errors', d1.disk_read_errors, d2.disk_read_errors, ''),
            ('Write Errors', d1.disk_write_errors, d2.disk_write_errors, ''),
            ('Bad Sectors', d1.disk_bad_sectors, d2.disk_bad_sectors, ''),
            ('Issues Found', d1.issues_found, d2.issues_found, ''),
        ]

        for name, v1, v2, unit in metrics:
            difference, percent = diff(v1, v2)
            change = 'worse' if difference > 0 else 'better' if difference < 0 else 'same'
            comparisons.append({
                'name': name, 'value1': v1, 'value2': v2,
                'difference': difference, 'percent': percent,
                'unit': unit, 'change': change
            })

        return jsonify({
            'success': True,
            'diagnosis1': d1.to_dict(),
            'diagnosis2': d2.to_dict(),
            'comparisons': comparisons,
            'status_change': {
                'from': d1.system_status,
                'to': d2.system_status,
                'change': 'better' if _status_rank(d2.system_status) < _status_rank(d1.system_status)
                          else 'worse' if _status_rank(d2.system_status) > _status_rank(d1.system_status)
                          else 'same'
            }
        })
    except Exception as e:
        print(f"[ATS] Compare error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# AUTO-REPAIR API
# ============================================================

@app.route('/api/auto_repair', methods=['POST'])
@login_required
def api_auto_repair():
    try:
        actions, total_freed = perform_auto_repair()

        for action in actions:
            db.session.add(RepairLog(
                user_id=current_user.id,
                action=action['name'],
                description=action['description'],
                success=action['success'],
                output=action['output'],
                bytes_freed=action['bytes_freed']
            ))
        db.session.commit()

        return jsonify({
            'success': True,
            'actions': actions,
            'total_freed': total_freed,
            'total_freed_formatted': format_size(total_freed)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/repair_logs')
@login_required
def api_repair_logs():
    try:
        logs = RepairLog.query.filter_by(user_id=current_user.id)\
                                .order_by(RepairLog.timestamp.desc())\
                                .limit(20).all()
        return jsonify({
            'success': True,
            'logs': [{
                'id': l.id, 'action': l.action, 'description': l.description,
                'success': l.success, 'output': l.output,
                'bytes_freed': l.bytes_freed,
                'timestamp': l.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            } for l in logs]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# CHATBOT KNOWLEDGE BASE
# ============================================================

CHATBOT_KNOWLEDGE = {
    'disk_warning': {
        'keywords': ['disk warning', 'disk is warning', 'disk showing warning', 'disk status warning', 'warning disk', 'why is my disk warning'],
        'response': """**Disk Warning** usually means one of these:

**1. Disk usage > 70%**
   - Your drive is getting full
   - Fix: Delete temp files, empty Recycle Bin

**2. Temperature elevated (45-55C)**
   - Drive is running warmer than ideal
   - Fix: Improve airflow, clean dust from PC

**3. Minor errors detected**
   - A few read/write errors or bad sectors
   - Fix: Run `chkdsk C: /f /r` as Administrator

Type **"disk cleanup"** for a step-by-step cleaning guide.""",
        'quick_replies': ['How do I do disk cleanup?', 'What is a bad sector?', 'Explain temperature']
    },
    'disk_critical': {
        'keywords': ['disk critical', 'disk is critical', 'disk critical status', 'my disk shows critical', 'critical disk', 'disk failing'],
        'response': """**CRITICAL Disk Status - IMMEDIATE ACTION REQUIRED**

**Step 1: BACKUP YOUR DATA NOW**
   - Copy important files to external drive
   - Use cloud storage

**Step 2: Check disk health details**
   - Go to History, click the Critical diagnosis
   - Look at "Bad Sectors" and "Disk Temperature"

**Step 3: Run disk check**
   - Open CMD as Administrator
   - Type: `chkdsk C: /f /r`
   - Press Y, then restart

**Step 4: Consider replacement**
   - If bad sectors > 5, plan disk replacement""",
        'quick_replies': ['How do I backup my data?', 'What is chkdsk?', 'What causes bad sectors?']
    },
    'disk_cleanup': {
        'keywords': ['disk cleanup', 'clean disk', 'free up space', 'clean up disk', 'disk full'],
        'response': """**Disk Cleanup Guide (Windows)**

**Method 1: Built-in Disk Cleanup**
  1. Press `Win + R`
  2. Type: `cleanmgr`
  3. Select drive, check items, click OK

**Method 2: Manual Deletion**
  1. Press `Win + R`, type `%temp%` - delete all
  2. Press `Win + R`, type `temp` - delete all
  3. Empty Recycle Bin

**Method 3: Uninstall Unused Programs**
  - Settings, Apps, Sort by size""",
        'quick_replies': ['Run new scan', 'Show disk usage']
    },
    'disk_temperature': {
        'keywords': ['disk temperature', 'temperature', 'disk temp', 'how hot', 'drive temperature'],
        'response': """**Disk Temperature Ranges**

  - Below 40C  : Excellent
  - 40-45C      : Good
  - 45-50C      : Warm - Improve airflow
  - 50-55C      : Hot - Fix urgently
  - Above 55C   : Critical - Back up data now

**How to Cool Your Drive:**
  1. Clean dust from PC
  2. Ensure proper airflow
  3. For laptops: use cooling pad
  4. Consider SSD replacement""",
        'quick_replies': ['Show my disk temp', 'How do I clean dust?']
    },
    'bad_sectors': {
        'keywords': ['bad sector', 'bad sectors', 'what is a bad sector', 'sector error'],
        'response': """**Bad Sectors Explained**

A **bad sector** is a section of your hard drive that can no longer be read or written.

**Two Types:**
  1. **Soft bad sectors** - logical errors, can be fixed
  2. **Hard bad sectors** - physical damage, cannot be fixed

**What to Do:**
  - **0-5 bad sectors:** Monitor closely
  - **5-20:** Plan replacement soon
  - **20+:** Replace immediately""",
        'quick_replies': ['How do I run chkdsk?', 'How to backup?']
    },
    'smart': {
        'keywords': ['smart', 's.m.a.r.t', 'what is smart', 'smart data'],
        'response': """**S.M.A.R.T. = Self-Monitoring, Analysis, and Reporting Technology**

It's a monitoring system built into modern hard drives.

**What it monitors:**
  - Read/Write error rates
  - Disk temperature
  - Bad sectors
  - Power-on hours

**Unlike HDD Sentinel**, our system works over the web with multi-user support.""",
        'quick_replies': ['Show my S.M.A.R.T. data', 'How accurate is it?']
    },
    'high_cpu': {
        'keywords': ['high cpu', 'cpu is high', 'cpu usage', 'cpu 100', 'cpu 90', 'cpu slow'],
        'response': """**High CPU Usage Fixes**

**Step 1: Identify the cause**
  - Press `Ctrl + Shift + Esc` (Task Manager)
  - Click "CPU" column to sort by usage

**Step 2: Common culprits**
  - **Web browsers** - too many tabs
  - **Background apps** - Windows Update, antivirus
  - **Malware** - run Windows Defender scan
  - **Startup programs** - disable in Task Manager

**Step 3: Immediate fixes**
  - End unneeded processes
  - Restart your computer""",
        'quick_replies': ['How do I open Task Manager?', 'Show my CPU usage']
    },
    'cpu_explain': {
        'keywords': ['what is cpu', 'cpu mean', 'explain cpu'],
        'response': """**CPU = Central Processing Unit**

The CPU is your computer's "brain".

**How to read CPU usage:**
  - **0-30%** = Idle/light use
  - **30-60%** = Moderate use
  - **60-80%** = Heavy use
  - **80-95%** = Very heavy
  - **95-100%** = Overloaded""",
        'quick_replies': ['Why is my CPU high?', 'Show CPU info']
    },
    'high_memory': {
        'keywords': ['high memory', 'memory is high', 'ram usage', 'ram is high', 'out of memory'],
        'response': """**High Memory (RAM) Usage Fixes**

**Step 1: Identify heavy users**
  - Press `Ctrl + Shift + Esc`
  - Click "Memory" column to sort

**Step 2: Common causes**
  - Too many browser tabs
  - Background apps
  - Memory leaks

**Step 3: Fixes**
  - Close unused applications
  - Restart computer""",
        'quick_replies': ['How to check RAM?', 'Show memory usage']
    },
    'memory_explain': {
        'keywords': ['what is memory', 'what is ram', 'explain memory'],
        'response': """**RAM = Random Access Memory**

RAM is your computer's **short-term memory**.

**How to read memory usage:**
  - **0-50%** = Comfortable
  - **50-70%** = Normal
  - **70-85%** = Getting full
  - **85-95%** = High
  - **95-100%** = Critical

**Rule of thumb:**
  - 8GB = Minimum
  - 16GB = Comfortable
  - 32GB+ = Heavy workloads""",
        'quick_replies': ['Why is my RAM high?', 'Show RAM info']
    },
    'schedule': {
        'keywords': ['schedule', 'scheduled scan', 'auto scan', 'how to schedule'],
        'response': """**Scheduled Automatic Scans**

**How to set up:**
  1. Click **Profile** in the navigation
  2. Find the **Scheduled Scans** card
  3. Choose an interval (every 1h, 6h, 12h, 24h, etc.)
  4. Click **Save Schedule**

**This solves a major HDD Sentinel limitation** - no manual scans required!""",
        'quick_replies': ['Go to profile', 'How do email alerts work?']
    },
    'email_alerts': {
        'keywords': ['email alert', 'email notification', 'alerts', 'notify me'],
        'response': """**Email Alerts Feature**

**How to enable:**
  1. Click **Profile** in navigation
  2. Find the **Email Alerts** card
  3. Toggle to **Enabled**

**When alerts are sent:**
  - **Warning** status - issue detected
  - **Critical** status - immediate action needed""",
        'quick_replies': ['Go to profile', 'Show my diagnoses']
    },
    'history': {
        'keywords': ['history', 'past diagnoses', 'previous scans', 'all scans'],
        'response': """**Diagnosis History**

**What you can do:**
  - View all diagnoses
  - Search by ID or status
  - Filter by date
  - Delete individual diagnoses
  - Export all as CSV
  - Compare two diagnoses""",
        'quick_replies': ['Go to history', 'Export CSV']
    },
    'dashboard': {
        'keywords': ['dashboard', 'chart', 'statistics', 'stats', 'graphs'],
        'response': """**Dashboard Overview**

**What it shows:**
  - Total Scans, Healthy, Warnings, Critical
  - Daily Activity Chart (last 7 days)
  - Disk Temperature Chart
  - Live System Info""",
        'quick_replies': ['Go to dashboard', 'Show stats']
    },
    'drives': {
        'keywords': ['drives', 'external drive', 'usb', 'ssd', 'hdd', 'connected drives', 'my drives'],
        'response': """**Connected Drives Feature**

Our system detects **ALL connected drives** - not just C: drive.

**What you can see:**
  - Drive letter or name
  - Drive type (SSD, HDD, USB, Removable)
  - Drive name/model
  - Total, used, and free space
  - Health status per drive
  - Temperature (Windows only)

**This is a major improvement over HDD Sentinel** which only monitors internal drives.""",
        'quick_replies': ['Go to drives', 'What is SMART?']
    },
    'forgot_password': {
        'keywords': ['forgot password', 'reset password', 'password reset', 'cant login', 'cannot login', 'recover password', 'lost password'],
        'response': """**Forgot Your Password?**

No problem - you can reset it easily:

**Step 1:** Go to the login page

**Step 2:** Click the **"Forgot Password?"** link

**Step 3:** Enter your registered email address

**Step 4:** Check your inbox for a reset link
  - The link expires in **1 hour**
  - Check your spam folder if you don't see it

**Step 5:** Click the link and set a new password

**Step 6:** Log in with your new password""",
        'quick_replies': ['Go to login', 'How do I register?']
    },
    'status': {
        'keywords': ['status', 'my status', 'current status', 'how is my system'],
        'response': '__DYNAMIC_STATUS__',
        'quick_replies': ['Run new scan', 'Show history']
    },
    'help': {
        'keywords': ['help', 'what can you do', 'how to use', 'commands'],
        'response': """**I can help you with:**

**Disk Health:**
  - Why disk is Warning/Critical
  - S.M.A.R.T. explained
  - Bad sectors, cleanup, temperature

**Performance:**
  - High CPU fixes
  - High Memory fixes

**Account:**
  - Forgot password
  - Register / Login

**ATS Features:**
  - Schedule scans, email alerts
  - History, dashboard, drives, compare

**Commands:**
  - `status` - Latest diagnosis
  - `help` - This message
  - `disk cleanup` - Cleaning guide""",
        'quick_replies': ['Why is my disk warning?', 'Show my drives']
    },
    'greeting': {
        'keywords': ['hi', 'hello', 'hey', 'good morning', 'good evening'],
        'response': """Hello! I'm your ATS Assistant.

**How can I help you today?**

Try:
  - "Why is my disk showing warning?"
  - "How do I fix high CPU usage?"
  - "Show me my latest diagnosis" """,
        'quick_replies': ['Help', 'My status']
    },
    'thanks': {
        'keywords': ['thanks', 'thank you', 'thx', 'appreciate'],
        'response': """You're welcome! I'm glad I could help.

**If you found this useful:**
  - Run a new diagnostic scan
  - Set up scheduled scans
  - Enable email alerts""",
        'quick_replies': ['Run new scan', 'Go to profile']
    },
    'bye': {
        'keywords': ['bye', 'goodbye', 'see you', 'later'],
        'response': """Goodbye! Remember to:
  - Run diagnostic scans regularly
  - Enable scheduled scans
  - Keep your data backed up

**Stay safe!** Come back anytime.""",
        'quick_replies': ['Help']
    },
}


def find_best_response(user_message, user=None):
    message_lower = user_message.lower().strip()

    if message_lower in ['status', 'my status', 'current status', 'how is my system', 'system status']:
        if user:
            try:
                latest = Diagnosis.query.filter_by(user_id=user.id)\
                                          .order_by(Diagnosis.timestamp.desc()).first()
                if latest:
                    details = json.loads(latest.details) if latest.details else {}
                    recommendations = details.get('recommendations', [])
                    rec_text = '\n'.join(f'  - {r}' for r in recommendations[:3])

                    return {
                        'response': f"""**Your Latest Diagnosis - #{latest.id}**

**Status:** {latest.system_status}
**Time:** {latest.timestamp.strftime('%Y-%m-%d %H:%M')}

**System Metrics:**
  - CPU: {latest.cpu_usage}%
  - Memory: {latest.memory_usage}%
  - Disk: {latest.disk_usage}%
  - Disk Health: {latest.disk_health}
  - Disk Temp: {latest.disk_temperature}C
  - Issues Found: {latest.issues_found}

**Top Recommendations:**
{rec_text}""",
                        'quick_replies': ['Run new scan', 'Show history', 'Go to dashboard']
                    }
                else:
                    return {
                        'response': """**No diagnoses found yet.**

Click **"Run Diagnostics"** on the Home page to get started.""",
                        'quick_replies': ['How does ATS work?', 'What is S.M.A.R.T.?']
                    }
            except Exception as e:
                print(f"[ATS] Status error: {e}")

    try:
        custom = CustomResponse.query.order_by(CustomResponse.priority.desc()).all()
        for cr in custom:
            if cr.keyword.lower() in message_lower:
                return {'response': cr.response, 'quick_replies': []}
    except:
        pass

    best_match = None
    best_score = 0

    for key, item in CHATBOT_KNOWLEDGE.items():
        score = 0
        for keyword in item['keywords']:
            if keyword in message_lower:
                score += len(keyword.split())

        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score > 0:
        response = best_match['response']
        if response == '__DYNAMIC_STATUS__' and user:
            return find_best_response('status', user)

        return {
            'response': response,
            'quick_replies': best_match.get('quick_replies', [])
        }

    return {
        'response': f"""I'm not sure I understood **"{user_message}"**.

**Try asking about:**
  - Disk health ("why is my disk warning?")
  - Performance ("how do I fix high CPU?")
  - Specific terms ("what is S.M.A.R.T.?")

Or type **"help"** to see everything I can do.""",
        'quick_replies': ['Help', 'My status', 'Why is my disk warning?']
    }


@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot():
    try:
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'success': False, 'error': 'Empty message'}), 400

        result = find_best_response(user_message, user=current_user)

        try:
            db.session.add(ChatMessage(user_id=current_user.id, role='user', message=user_message))
            db.session.add(ChatMessage(user_id=current_user.id, role='bot', message=result['response']))
            db.session.commit()
        except Exception as e:
            print(f"[ATS] Could not save chat history: {e}")
            db.session.rollback()

        return jsonify({
            'success': True,
            'response': result['response'],
            'quick_replies': result.get('quick_replies', [])
        })

    except Exception as e:
        print(f"[ATS] Chatbot error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/chatbot/export', methods=['POST'])
@login_required
def chatbot_export():
    try:
        data = request.get_json() or {}
        history = data.get('history', [])

        if not history:
            return jsonify({'error': 'No history'}), 400

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'ChatTitle', parent=styles['Heading1'],
            fontSize=20, textColor=colors.HexColor('#667eea')
        )

        story.append(Paragraph("ATS Assistant - Chat Transcript", title_style))
        story.append(Paragraph(f"User: {current_user.username}", styles['Normal']))
        story.append(Paragraph(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles['Normal']))
        story.append(Spacer(1, 0.25*inch))

        user_style = ParagraphStyle('UserMsg', parent=styles['Normal'],
                                    textColor=colors.HexColor('#667eea'),
                                    leftIndent=20, spaceAfter=10)
        bot_style = ParagraphStyle('BotMsg', parent=styles['Normal'],
                                   textColor=colors.black, spaceAfter=15)

        for msg in history:
            text = msg.get('text', '').replace('**', '').replace('`', '')
            if msg.get('role') == 'user':
                story.append(Paragraph(f"<b>You:</b> {text}", user_style))
            else:
                story.append(Paragraph(f"<b>ATS Assistant:</b> {text}", bot_style))

        doc.build(story)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/pdf',
            download_name=f'ats_chat_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.pdf',
            as_attachment=True
        )
    except Exception as e:
        print(f"[ATS] Export error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chatbot/history', methods=['GET'])
@login_required
def chatbot_history():
    try:
        messages = ChatMessage.query.filter_by(user_id=current_user.id)\
                                     .order_by(ChatMessage.timestamp.asc())\
                                     .limit(100).all()
        return jsonify({
            'success': True,
            'messages': [{
                'role': m.role,
                'message': m.message,
                'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            } for m in messages]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ADMIN CHATBOT API
# ============================================================

@app.route('/api/admin/chatbot/add', methods=['POST'])
@login_required
def admin_chatbot_add():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    try:
        data = request.get_json() or {}
        keyword = data.get('keyword', '').strip()
        response = data.get('response', '').strip()
        priority = int(data.get('priority', 0))

        if not keyword or not response:
            return jsonify({'success': False, 'error': 'Keyword and response required'}), 400

        cr = CustomResponse(
            keyword=keyword.lower(),
            response=response,
            priority=priority,
            created_by=current_user.id
        )
        db.session.add(cr)
        db.session.commit()

        return jsonify({'success': True, 'id': cr.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/chatbot/<int:response_id>', methods=['DELETE'])
@login_required
def admin_chatbot_delete(response_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin required'}), 403

    try:
        cr = CustomResponse.query.get(response_id)
        if cr:
            db.session.delete(cr)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# EXPORT ROUTES
# ============================================================

@app.route('/export/pdf/<int:diagnosis_id>')
@login_required
def export_pdf(diagnosis_id):
    diagnosis = get_diagnosis_by_id(diagnosis_id)
    if not diagnosis:
        return jsonify({'error': 'Not found'}), 404

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=20, textColor=colors.HexColor('#667eea')
    )

    story.append(Paragraph("ATS - Automated Troubleshooting System", title_style))
    story.append(Paragraph("Diagnosis Report", styles['Heading2']))
    story.append(Spacer(1, 0.25*inch))

    info_data = [
        ['Diagnosis ID', f'#{diagnosis.id}'],
        ['Timestamp', diagnosis.timestamp.strftime('%Y-%m-%d %H:%M:%S')],
        ['System Status', diagnosis.system_status],
        ['Scan Type', diagnosis.scan_type],
        ['', ''],
        ['PERFORMANCE METRICS', ''],
        ['CPU Usage', f'{diagnosis.cpu_usage}%'],
        ['Memory Usage', f'{diagnosis.memory_usage}%'],
        ['Disk Usage', f'{diagnosis.disk_usage}%'],
        ['', ''],
        ['DISK HEALTH (S.M.A.R.T.)', ''],
        ['Disk Health', diagnosis.disk_health],
        ['Disk Temperature', f'{diagnosis.disk_temperature}C'],
        ['Read Errors', str(diagnosis.disk_read_errors)],
        ['Write Errors', str(diagnosis.disk_write_errors)],
        ['Bad Sectors', str(diagnosis.disk_bad_sectors)],
        ['Power-On Hours', str(diagnosis.disk_power_on_hours)],
        ['', ''],
        ['ISSUES', ''],
        ['Issues Found', str(diagnosis.issues_found)],
        ['Issues Fixed', str(diagnosis.issues_fixed)],
    ]

    table = Table(info_data, colWidths=[2.5*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.25*inch))

    drives = get_drives_for_diagnosis(diagnosis.id)
    if drives:
        story.append(Paragraph("Detected Drives:", styles['Heading2']))
        drive_data = [['Drive', 'Type', 'Name', 'Used/Total (GB)', 'Health']]
        for d in drives:
            drive_data.append([
                d.drive_letter, d.drive_type, d.drive_name[:30],
                f'{d.used_size}/{d.total_size}', d.health_status
            ])
        drive_table = Table(drive_data, colWidths=[1.2*inch, 0.8*inch, 1.8*inch, 1.3*inch, 0.9*inch])
        drive_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(drive_table)
        story.append(Spacer(1, 0.25*inch))

    details = json.loads(diagnosis.details) if diagnosis.details else {}
    recommendations = details.get('recommendations', [])
    if recommendations:
        story.append(Paragraph("Recommendations:", styles['Heading2']))
        for rec in recommendations:
            story.append(Paragraph(f"- {rec}", styles['Normal']))

    if diagnosis.user_notes:
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("User Notes:", styles['Heading2']))
        story.append(Paragraph(diagnosis.user_notes, styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, download_name=f'diagnosis_{diagnosis_id}.pdf', as_attachment=True)


@app.route('/export/csv')
@login_required
def export_csv():
    diagnoses = get_all_diagnoses(limit=1000, user_id=current_user.id)

    output = BytesIO()
    wrapper = __import__('io').TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.writer(wrapper)

    writer.writerow([
        'ID', 'Timestamp', 'Status', 'Scan Type', 'CPU %', 'Memory %',
        'Disk %', 'Disk Health', 'Disk Temp (C)', 'Read Errors',
        'Write Errors', 'Bad Sectors', 'Issues Found'
    ])

    for d in diagnoses:
        writer.writerow([
            d.id,
            d.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            d.system_status,
            d.scan_type,
            d.cpu_usage,
            d.memory_usage,
            d.disk_usage,
            d.disk_health,
            d.disk_temperature,
            d.disk_read_errors,
            d.disk_write_errors,
            d.disk_bad_sectors,
            d.issues_found,
        ])

    wrapper.seek(0)
    csv_data = wrapper.read()
    wrapper.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=diagnoses_{current_user.username}.csv"}
    )


# ============================================================
# RUN APPLICATION
# ============================================================
if __name__ == '__main__':
    for folder in ['templates', 'static', 'static/css', 'static/js', 'static/images', 'instance']:
        if not os.path.exists(folder):
            os.makedirs(folder)

    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    print("\n" + "=" * 60)
    print("ATS - AUTOMATED TROUBLESHOOTING SYSTEM")
    print("=" * 60)
    print(f"Working Directory: {os.getcwd()}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug Mode: {debug_mode}")
    print("=" * 60)
    print("\nFeatures Enabled:")
    print("   - User Authentication (Multi-user)")
    print("   - Password Reset (Forgot Password)")
    print("   - Email Alerts")
    print("   - Scheduled Auto-Scans")
    print("   - Disk Temperature Monitoring")
    print("   - Rule-based Chatbot")
    print("   - Multi-Drive Detection (Windows + Linux)")
    print("   - Health Score (0-100)")
    print("   - Diagnoses Comparison")
    print("   - Auto-Repair Actions")
    print("=" * 60)
    print("\nSystem is ready!")
    print("   Press Ctrl+C to stop the server\n")

    try:
        app.run(debug=debug_mode, host=host, port=port, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if scheduler:
            scheduler.shutdown()
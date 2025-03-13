from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
import os
import sys
import shutil
import json
from datetime import datetime

# Add project root to path
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_dir)

import config
from web_dashboard.authentication import change_password, hash_password

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/')
@login_required
def index():
    return render_template('settings.html')

@bp.route('/get_current')
@login_required
def get_settings():
    """Get current settings"""
    try:
        # Extract settings from config
        settings = {
            "camera": {
                "camera_index": getattr(config, "CAMERA_INDEX", 0),
                "frame_width": getattr(config, "FRAME_WIDTH", 640),
                "frame_height": getattr(config, "FRAME_HEIGHT", 480),
            },
            "detection": {
                "face_recognition_tolerance": getattr(config, "FACE_RECOGNITION_TOLERANCE", 0.6),
                "face_confidence_threshold": getattr(config, "FACE_CONFIDENCE_THRESHOLD", 0.5),
                "frames_to_skip": getattr(config, "FRAMES_TO_SKIP", 3),
                "nms_iou_threshold": getattr(config, "NMS_IOU_THRESHOLD", 0.5)
            },
            "tracking": {
                "tracker_timeout": getattr(config, "TRACKER_TIMEOUT", 1.0),
                "presence_timeout": getattr(config, "PRESENCE_TIMEOUT", 5.0),
                "person_timeout": getattr(config, "PERSON_TIMEOUT", 5.0)
            },
            "alerts": {
                "min_seconds_between_alerts": getattr(config, "MIN_SECONDS_BETWEEN_ALERTS", 10),
                "telegram_token": getattr(config, "TELEGRAM_TOKEN", ""),
                "telegram_chat_id": getattr(config, "TELEGRAM_CHAT_ID", "")
            },
            "recording": {
                "recording_enabled": getattr(config, "RECORDING_ENABLED", True),
                "video_fps": getattr(config, "VIDEO_FPS", 20),
                "intruder_clip_seconds": getattr(config, "INTRUDER_CLIP_SECONDS", 10)
            },
            "paths": {
                "dataset_dir": config.DATASET_DIR,
                "recordings_dir": config.RECORDINGS_DIR,
                "intruders_dir": config.INTRUDERS_DIR,
                "logs_dir": config.LOGS_DIR
            }
        }
        
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route('/update', methods=['POST'])
@login_required
def update_settings():
    """Update system settings"""
    try:
        settings = request.json
        
        # Create backup of config file
        config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.py")
        backup_file = config_file + f".bak_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        shutil.copy2(config_file, backup_file)
        
        # Read config file
        with open(config_file, "r") as f:
            lines = f.readlines()
            
        # Update values
        new_lines = []
        updated_settings = []
        
        # Map of settings to look for in config.py
        setting_map = {
            "camera.camera_index": "CAMERA_INDEX",
            "camera.frame_width": "FRAME_WIDTH",
            "camera.frame_height": "FRAME_HEIGHT",
            "detection.face_recognition_tolerance": "FACE_RECOGNITION_TOLERANCE",
            "detection.face_confidence_threshold": "FACE_CONFIDENCE_THRESHOLD",
            "detection.frames_to_skip": "FRAMES_TO_SKIP",
            "detection.nms_iou_threshold": "NMS_IOU_THRESHOLD",
            "tracking.tracker_timeout": "TRACKER_TIMEOUT",
            "tracking.presence_timeout": "PRESENCE_TIMEOUT",
            "tracking.person_timeout": "PERSON_TIMEOUT",
            "alerts.min_seconds_between_alerts": "MIN_SECONDS_BETWEEN_ALERTS",
            "alerts.telegram_token": "TELEGRAM_TOKEN",
            "alerts.telegram_chat_id": "TELEGRAM_CHAT_ID",
            "recording.recording_enabled": "RECORDING_ENABLED",
            "recording.video_fps": "VIDEO_FPS",
            "recording.intruder_clip_seconds": "INTRUDER_CLIP_SECONDS"
        }
        
        # Flatten settings for easier access
        flat_settings = {}
        for category, items in settings.items():
            for key, value in items.items():
                flat_key = f"{category}.{key}"
                if flat_key in setting_map:
                    flat_settings[setting_map[flat_key]] = value
        
        # Update config file contents
        for line in lines:
            line_updated = False
            for setting_name, setting_value in flat_settings.items():
                if line.strip().startswith(setting_name + " ="):
                    # Format value based on type
                    if isinstance(setting_value, str):
                        value_str = f'"{setting_value}"'
                    elif isinstance(setting_value, bool):
                        value_str = str(setting_value)
                    else:
                        value_str = str(setting_value)
                    
                    new_line = f"{setting_name} = {value_str}\n"
                    new_lines.append(new_line)
                    updated_settings.append(setting_name)
                    line_updated = True
                    break
            
            if not line_updated:
                new_lines.append(line)
        
        # Write updated config file
        with open(config_file, "w") as f:
            f.writelines(new_lines)
            
        # Report which settings were successfully updated
        return jsonify({
            "success": True, 
            "updated_settings": updated_settings,
            "backup_file": os.path.basename(backup_file)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route('/change_password', methods=['POST'])
@login_required
def update_password():
    """Change admin password"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            return jsonify({"success": False, "error": "All fields are required"})
            
        if new_password != confirm_password:
            return jsonify({"success": False, "error": "New passwords don't match"})
            
        # Change password
        username = current_user.id
        success = change_password(username, current_password, new_password)
        
        if success:
            return jsonify({"success": True, "message": "Password changed successfully"})
        else:
            return jsonify({"success": False, "error": "Current password is incorrect"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route('/system_status')
@login_required
def system_status():
    """Get system status information"""
    status = {}
    
    # Check camera
    try:
        import cv2
        camera_index = getattr(config, "CAMERA_INDEX", 0)
        cap = cv2.VideoCapture(camera_index)
        camera_status = "Available" if cap.isOpened() else "Unavailable"
        cap.release()
    except:
        camera_status = "Error"
    
    status["camera"] = camera_status
    
    # Check directories
    dirs_to_check = [
        ("dataset_dir", config.DATASET_DIR),
        ("recordings_dir", config.RECORDINGS_DIR),
        ("intruders_dir", config.INTRUDERS_DIR),
        ("logs_dir", config.LOGS_DIR)
    ]
    
    for name, path in dirs_to_check:
        status[name] = "Available" if os.path.exists(path) else "Missing"
    
    # Check face recognition
    try:
        import face_recognition
        face_recognition_status = "Available"
    except:
        face_recognition_status = "Missing"
    
    status["face_recognition"] = face_recognition_status
    
    # Check encodings file
    if os.path.exists(config.ENCODINGS_FILE):
        try:
            import pickle
            with open(config.ENCODINGS_FILE, "rb") as f:
                data = pickle.load(f)
            if "encodings" in data and "names" in data:
                status["encodings"] = f"Available ({len(data['encodings'])} faces)"
            else:
                status["encodings"] = "Invalid format"
        except:
            status["encodings"] = "Corrupted"
    else:
        status["encodings"] = "Missing"
    
    # Check detection process
    try:
        import psutil
        detection_running = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline'])
                if 'intruder_detection.py' in cmdline:
                    detection_running = True
                    break
        
        status["detection"] = "Running" if detection_running else "Stopped"
    except:
        status["detection"] = "Unknown"
    
    # Get system info
    try:
        import platform
        status["os"] = f"{platform.system()} {platform.release()}"
        status["python"] = platform.python_version()
        
        import psutil
        mem = psutil.virtual_memory()
        status["memory_used"] = f"{mem.percent}%"
        status["cpu_usage"] = f"{psutil.cpu_percent()}%"
        
        disk = psutil.disk_usage('/')
        status["disk_usage"] = f"{disk.percent}%"
    except:
        pass
    
    return jsonify({"success": True, "status": status})
from flask import Blueprint, render_template, jsonify, Response
from flask_login import login_required
import os
import config
import time
import cv2
from datetime import datetime
import subprocess
import sys
import threading
import numpy as np

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Add global variables to manage the camera feed
camera = None
camera_lock = threading.Lock()

@bp.route('/')
@login_required
def index():
    return render_template('dashboard.html')

@bp.route('/stats')
@login_required
def get_stats():
    """Get statistics for the dashboard"""
    try:
        # Count recordings
        recordings_path = config.RECORDINGS_DIR
        recordings_count = len([f for f in os.listdir(recordings_path) if f.endswith(('.avi', '.mp4'))]) if os.path.exists(recordings_path) else 0
        
        # Count known people
        dataset_path = config.DATASET_DIR
        known_people = len([f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f))]) if os.path.exists(dataset_path) else 0
        
        # Count intruder alerts
        intruder_path = os.path.join(config.INTRUDERS_DIR, "images")
        intruder_count = len([f for f in os.listdir(intruder_path) if f.endswith(('.jpg', '.png'))]) if os.path.exists(intruder_path) else 0
        
        # Calculate storage used
        storage_used = 0
        for folder in [config.RECORDINGS_DIR, config.DATASET_DIR, config.INTRUDERS_DIR]:
            if os.path.exists(folder):
                for root, _, files in os.walk(folder):
                    for file in files:
                        storage_used += os.path.getsize(os.path.join(root, file))
        
        # Convert to appropriate unit (MB or GB)
        if storage_used > 1024 * 1024 * 1024:  # > 1GB
            storage_str = f"{storage_used / (1024 * 1024 * 1024):.2f} GB"
        else:
            storage_str = f"{storage_used / (1024 * 1024):.2f} MB"
        
        # Get recent activity
        activity_log_path = os.path.join(config.LOGS_DIR, "activity_log.txt")
        activity = []
        if os.path.exists(activity_log_path):
            with open(activity_log_path, "r") as f:
                # Get last 20 lines
                lines = f.readlines()[-20:]
                activity = [line.strip() for line in lines]
        
        # System status
        detection_running = False
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'python' in proc.info['name'].lower():
                    cmdline = " ".join(proc.info['cmdline'])
                    if 'intruder_detection.py' in cmdline:
                        detection_running = True
                        break
        except:
            pass
            
        return jsonify({
            'success': True,
            'recordings_count': recordings_count,
            'known_people': known_people,
            'intruder_count': intruder_count,
            'storage_used': storage_str,
            'activity': activity,
            'detection_running': detection_running,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/start_detection')
@login_required
def start_detection():
    """Start intruder detection process"""
    try:
        # Check if already running
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "intruder_detection.py")
        subprocess.Popen([sys.executable, script_path])
        return jsonify({'success': True, 'message': 'Intruder detection started'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/stop_detection')
@login_required
def stop_detection():
    """Stop intruder detection process"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline'])
                if 'intruder_detection.py' in cmdline:
                    try:
                        pid = proc.info['pid']
                        process = psutil.Process(pid)
                        process.terminate()
                        return jsonify({'success': True, 'message': 'Intruder detection stopped'})
                    except:
                        pass
        return jsonify({'success': False, 'error': 'Detection process not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def get_camera():
    """Get or initialize the camera"""
    global camera
    with camera_lock:
        if camera is None:
            # Try to initialize the camera
            camera = cv2.VideoCapture(config.CAMERA_INDEX if hasattr(config, 'CAMERA_INDEX') else 0)
            # Set resolution to improve performance
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return camera

def is_detection_running():
    """Check if intruder detection is running"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline']) if proc.info['cmdline'] else ""
                if 'intruder_detection.py' in cmdline:
                    return True
        return False
    except:
        return False

def create_unavailable_frame(message):
    """Create a frame showing camera unavailable message"""
    # Create a blank dark frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add camera icon with slash
    cv2.rectangle(frame, (250, 180), (390, 300), (0, 0, 100), 2)  # Camera body
    cv2.rectangle(frame, (320, 160), (350, 180), (0, 0, 100), 2)  # Camera top
    cv2.line(frame, (200, 150), (440, 330), (0, 0, 255), 4)  # Red slash
    
    # Add message
    cv2.putText(frame, message, (150, 360), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    cv2.putText(frame, "Start detection to view live feed", (120, 400), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                
    # Convert to JPEG
    ret, buffer = cv2.imencode('.jpg', frame)
    return buffer.tobytes()

def generate_frames():
    """Generator function to yield video frames"""
    try:
        while True:
            # First check if detection is running
            detection_running = is_detection_running()
            if not detection_running:
                # Detection not running - show "unavailable" frame
                blank_frame = create_unavailable_frame("Detection not running")
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + blank_frame + b'\r\n')
                time.sleep(1)  # Check again after 1 second
                continue
                
            # Try to get camera
            cam = get_camera()
            if not cam or not cam.isOpened():
                # Camera not available
                blank_frame = create_unavailable_frame("Camera not available")
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + blank_frame + b'\r\n')
                time.sleep(1)
                continue
                
            success, frame = cam.read()
            if not success:
                time.sleep(0.1)
                continue
                
            # Add timestamp to the frame
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            # Yield the frame in the response
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Small delay to control frame rate (10 FPS)
            time.sleep(0.1)
    except Exception as e:
        print(f"Error in generate_frames: {str(e)}")
        blank_frame = create_unavailable_frame("Error: " + str(e))
        yield (b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + blank_frame + b'\r\n')
    finally:
        pass

@bp.route('/video_feed')
@login_required
def video_feed():
    """Route to stream the live camera feed"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route('/camera_status')
@login_required
def camera_status():
    """Check if camera is available"""
    cam = get_camera()
    if cam and cam.isOpened():
        return jsonify({'success': True, 'available': True})
    else:
        return jsonify({'success': True, 'available': False})
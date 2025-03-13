from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
import os
import config
from datetime import datetime

bp = Blueprint('logs', __name__, url_prefix='/logs')

@bp.route('/')
@login_required
def index():
    return render_template('logs.html')

@bp.route('/list')
@login_required
def list_logs():
    """Get list of available log files"""
    try:
        result = []
        logs_path = config.LOGS_DIR
        
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)
            return jsonify({'success': True, 'logs': []})
        
        for file in os.listdir(logs_path):
            if file.endswith(('.txt', '.log')):
                file_path = os.path.join(logs_path, file)
                modification_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                size_kb = os.path.getsize(file_path) / 1024
                
                # Count lines
                line_count = 0
                try:
                    with open(file_path, 'r') as f:
                        for _ in f:
                            line_count += 1
                except:
                    pass
                
                result.append({
                    'filename': file,
                    'date': modification_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': f"{size_kb:.2f} KB",
                    'lines': line_count
                })
        
        # Sort by modification date (newest first)
        result.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({'success': True, 'logs': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/content')
@login_required
def get_log_content():
    """Get content of a specific log file"""
    try:
        filename = request.args.get('filename')
        if not filename:
            return jsonify({'success': False, 'error': 'Filename is required'})
        
        file_path = os.path.join(config.LOGS_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'Log file not found'})
        
        try:
            with open(file_path, 'r') as f:
                content = f.readlines()
                
            # Return most recent entries first (limited to 1000 lines)
            content = content[-1000:]
                
            return jsonify({'success': True, 'content': content})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error reading log file: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/clear', methods=['POST'])
@login_required
def clear_log():
    """Clear a log file"""
    try:
        filename = request.form.get('filename')
        if not filename:
            return jsonify({'success': False, 'error': 'Filename is required'})
        
        file_path = os.path.join(config.LOGS_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'Log file not found'})
        
        # Clear file by opening in write mode
        with open(file_path, 'w') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log cleared by admin\n")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
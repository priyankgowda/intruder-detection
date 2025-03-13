from flask import Blueprint, render_template, jsonify, send_file, request, current_app
from flask_login import login_required
import os
import time
from datetime import datetime
import config
import mimetypes

bp = Blueprint('recordings', __name__, url_prefix='/recordings')

@bp.route('/')
@login_required
def index():
    return render_template('recordings.html')

@bp.route('/list')
@login_required
def list_recordings():
    """Get list of available recordings"""
    try:
        result = []
        recordings_path = config.RECORDINGS_DIR
        
        # Ensure directories exist
        if not os.path.exists(recordings_path):
            os.makedirs(recordings_path)
        
        intruder_videos_path = os.path.join(config.INTRUDERS_DIR, "videos")
        intruder_images_path = os.path.join(config.INTRUDERS_DIR, "images")
        
        if not os.path.exists(intruder_videos_path):
            os.makedirs(intruder_videos_path)
        
        if not os.path.exists(intruder_images_path):
            os.makedirs(intruder_images_path)
        
        # Get intruder videos
        if os.path.exists(intruder_videos_path):
            for file in os.listdir(intruder_videos_path):
                if file.endswith(('.avi', '.mp4')):
                    file_path = os.path.join(intruder_videos_path, file)
                    creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    
                    # Get corresponding image if available
                    image_name = file.replace('.avi', '.jpg').replace('.mp4', '.jpg')
                    image_path = os.path.join(config.INTRUDERS_DIR, "images", image_name)
                    has_image = os.path.exists(image_path)
                    
                    result.append({
                        'id': file,
                        'filename': file,
                        'type': 'intruder',
                        'date': creation_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'size': f"{size_mb:.2f} MB",
                        'thumbnail': has_image
                    })
        
        # Get regular recordings
        if os.path.exists(recordings_path):
            for file in os.listdir(recordings_path):
                if file.endswith(('.avi', '.mp4')):
                    file_path = os.path.join(recordings_path, file)
                    creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    
                    result.append({
                        'id': file,
                        'filename': file,
                        'type': 'regular',
                        'date': creation_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'size': f"{size_mb:.2f} MB",
                        'thumbnail': False
                    })
        
        # Sort by date (newest first)
        result.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({'success': True, 'recordings': result})
    except Exception as e:
        current_app.logger.error(f"Error listing recordings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/thumbnail/<path:filename>')
@login_required
def get_thumbnail(filename):
    """Get thumbnail for recording"""
    try:
        # For intruder recordings, check if there's an image
        image_name = filename.replace('.avi', '.jpg').replace('.mp4', '.jpg')
        image_path = os.path.join(config.INTRUDERS_DIR, "images", image_name)
        
        if os.path.exists(image_path):
            return send_file(image_path, mimetype='image/jpeg')
        else:
            # Return a placeholder or error
            return jsonify({'success': False, 'error': 'Thumbnail not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error serving thumbnail: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/download/<path:filename>')
@login_required
def download_recording(filename):
    """Download a recording file with proper headers"""
    try:
        # Determine if it's an intruder recording or regular recording
        intruder_path = os.path.join(config.INTRUDERS_DIR, "videos", filename)
        regular_path = os.path.join(config.RECORDINGS_DIR, filename)
        
        if os.path.exists(intruder_path):
            file_path = intruder_path
        elif os.path.exists(regular_path):
            file_path = regular_path
        else:
            return jsonify({'success': False, 'error': 'Recording not found'}), 404
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # Determine MIME type based on extension
            if filename.endswith('.mp4'):
                mime_type = 'video/mp4'
            elif filename.endswith('.avi'):
                mime_type = 'video/x-msvideo'
            else:
                mime_type = 'application/octet-stream'  # Default
            
        # Return file with proper attachment headers for download
        # Use download_name instead of attachment_filename (which is deprecated)
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename,
            conditional=True  # Enable conditional responses
        )
    except Exception as e:
        current_app.logger.error(f"Error downloading recording: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/view/<path:filename>')
@login_required
def view_recording(filename):
    """Stream a recording file for viewing"""
    try:
        # Determine if it's an intruder recording or regular recording
        intruder_path = os.path.join(config.INTRUDERS_DIR, "videos", filename)
        regular_path = os.path.join(config.RECORDINGS_DIR, filename)
        
        if os.path.exists(intruder_path):
            file_path = intruder_path
        elif os.path.exists(regular_path):
            file_path = regular_path
        else:
            return jsonify({'success': False, 'error': 'Recording not found'}), 404
        
        # Get the file size for content-length header
        file_size = os.path.getsize(file_path)
        
        # Set explicit MIME type based on file extension
        if filename.endswith('.mp4'):
            mime_type = 'video/mp4'
        elif filename.endswith('.avi'):
            mime_type = 'video/x-msvideo'
        else:
            mime_type = 'video/mp4'  # Default to mp4
            
        # Set all required headers for video streaming
        response = send_file(
            file_path,
            mimetype=mime_type,
            conditional=True,  # Enable conditional responses
            etag=True,         # Enable ETag support
            last_modified=datetime.fromtimestamp(os.path.getmtime(file_path))  # Set last-modified
        )
        
        # Add content length header explicitly
        response.headers['Content-Length'] = file_size
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error viewing recording: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/delete', methods=['POST'])
@login_required
def delete_recording():
    """Delete a recording"""
    try:
        filename = request.form.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'error': 'Missing filename'})
        
        # Check both locations
        intruder_path = os.path.join(config.INTRUDERS_DIR, "videos", filename)
        regular_path = os.path.join(config.RECORDINGS_DIR, filename)
        
        deleted = False
        
        # Delete from intruders directory if exists
        if os.path.exists(intruder_path):
            os.remove(intruder_path)
            deleted = True
            
            # Also delete corresponding image if exists
            image_name = filename.replace('.avi', '.jpg').replace('.mp4', '.jpg')
            image_path = os.path.join(config.INTRUDERS_DIR, "images", image_name)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # Delete from regular recordings directory if exists
        if os.path.exists(regular_path):
            os.remove(regular_path)
            deleted = True
        
        if not deleted:
            return jsonify({'success': False, 'error': 'Recording not found'})
        
        return jsonify({'success': True, 'message': 'Recording deleted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error deleting recording: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
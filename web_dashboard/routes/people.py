from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from flask_login import login_required
import os
import json
import datetime
import config
from werkzeug.utils import secure_filename
import glob
import time
from datetime import datetime

# Check if the dataset directory exists, if not create it
if not os.path.exists(config.DATASET_DIR):
    os.makedirs(config.DATASET_DIR)
    print(f"Created dataset directory: {config.DATASET_DIR}")

bp = Blueprint('people', __name__, url_prefix='/people')

@bp.route('/')
@login_required
def index():
    """Render the people management page"""
    return render_template('people.html')

@bp.route('/list')
@login_required
def list_people():
    """Return list of people with basic info"""
    try:
        people = []
        
        # List all folders in dataset directory
        if os.path.exists(config.DATASET_DIR):
            person_folders = [f for f in os.listdir(config.DATASET_DIR) 
                             if os.path.isdir(os.path.join(config.DATASET_DIR, f))]
            
            for person in person_folders:
                person_dir = os.path.join(config.DATASET_DIR, person)
                # Count images
                images = glob.glob(os.path.join(person_dir, "*.jpg")) + glob.glob(os.path.join(person_dir, "*.png"))
                
                # Get last seen info (placeholder - would come from a database in a real system)
                last_seen = "Never" 
                
                people.append({
                    "name": person,
                    "image_count": len(images),
                    "last_seen": last_seen
                })
            
            # Sort by name
            people.sort(key=lambda x: x["name"].lower())
        
        return jsonify({"success": True, "people": people})
    except Exception as e:
        print(f"Error in list_people: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@bp.route('/details')
@login_required
def person_details():
    """Get detailed information about a person"""
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({"success": False, "error": "No name provided"})
        
        # Build path to person directory
        person_dir = os.path.join(config.DATASET_DIR, name)
        
        if not os.path.exists(person_dir):
            return jsonify({"success": False, "error": f"Person '{name}' not found"})
        
        # Get images
        image_extensions = ['*.jpg', '*.jpeg', '*.png']
        images = []
        for ext in image_extensions:
            images.extend(glob.glob(os.path.join(person_dir, ext)))
        
        # Format image data
        image_data = []
        for img_path in images:
            filename = os.path.basename(img_path)
            stat_info = os.stat(img_path)
            mod_time = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            image_data.append({
                "filename": filename,
                "date": mod_time,
                "size": round(stat_info.st_size / 1024, 2)  # Size in KB
            })
        
        # Sort by date (newest first)
        image_data.sort(key=lambda x: x["date"], reverse=True)
        
        # Get last seen info (placeholder)
        last_seen = "Never"  # In a real system, this would come from tracking data
        
        return jsonify({
            "success": True,
            "name": name,
            "image_count": len(images),
            "last_seen": last_seen,
            "images": image_data
        })
    except Exception as e:
        print(f"Error in person_details: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@bp.route('/image/<person>/<filename>')
@login_required
def get_image(person, filename):
    """Get a specific image for a person"""
    try:
        # Sanitize inputs to prevent path traversal
        safe_person = secure_filename(person)
        safe_filename = secure_filename(filename)
        
        # Build path to image
        image_path = os.path.join(config.DATASET_DIR, safe_person, safe_filename)
        
        if not os.path.exists(image_path):
            return "Image not found", 404
        
        return send_file(image_path, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error in get_image: {str(e)}")
        return "Error serving image", 500

@bp.route('/add', methods=['POST'])
@login_required
def add_person():
    """Add a new person"""
    try:
        name = request.form.get('name')
        if not name:
            return jsonify({"success": False, "error": "No name provided"})
        
        # Sanitize name to be safe for filesystem
        safe_name = secure_filename(name)
        
        # Create directory for person
        person_dir = os.path.join(config.DATASET_DIR, safe_name)
        
        if os.path.exists(person_dir):
            return jsonify({"success": False, "error": f"Person '{name}' already exists"})
        
        os.makedirs(person_dir, exist_ok=True)
        
        # Handle optional image upload
        image_file = request.files.get('image')
        learn_face = request.form.get('learn', 'false').lower() == 'true'
        
        if image_file and image_file.filename:
            # Save image
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(person_dir, filename)
            image_file.save(image_path)
            
            # Trigger face learning in a real system
            if learn_face:
                # This would be integrated with your face recognition system
                pass
        
        return jsonify({"success": True, "message": f"Person '{name}' added successfully"})
    except Exception as e:
        print(f"Error in add_person: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@bp.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    """Upload a new image for an existing person"""
    try:
        person = request.form.get('person')
        if not person:
            return jsonify({"success": False, "error": "No person specified"})
        
        # Sanitize name
        safe_person = secure_filename(person)
        
        # Check if person exists
        person_dir = os.path.join(config.DATASET_DIR, safe_person)
        if not os.path.exists(person_dir):
            return jsonify({"success": False, "error": f"Person '{person}' not found"})
        
        # Handle image upload
        image_file = request.files.get('image')
        learn_face = request.form.get('learn', 'false').lower() == 'true'
        
        if not image_file or not image_file.filename:
            return jsonify({"success": False, "error": "No image provided"})
        
        # Generate unique filename to avoid overwriting
        base_name = secure_filename(image_file.filename)
        base, ext = os.path.splitext(base_name)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{base}_{timestamp}{ext}"
        
        # Save image
        image_path = os.path.join(person_dir, filename)
        image_file.save(image_path)
        
        # Trigger face learning in a real system
        if learn_face:
            # This would be integrated with your face recognition system
            pass
        
        return jsonify({"success": True, "message": "Image uploaded successfully"})
    except Exception as e:
        print(f"Error in upload_image: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@bp.route('/delete_image', methods=['POST'])
@login_required
def delete_image():
    """Delete an image for a person"""
    try:
        person = request.form.get('person')
        filename = request.form.get('filename')
        
        if not person or not filename:
            return jsonify({"success": False, "error": "Person and filename must be specified"})
        
        # Sanitize inputs
        safe_person = secure_filename(person)
        safe_filename = secure_filename(filename)
        
        # Build path to image
        image_path = os.path.join(config.DATASET_DIR, safe_person, safe_filename)
        
        if not os.path.exists(image_path):
            return jsonify({"success": False, "error": "Image not found"})
        
        # Delete the file
        os.remove(image_path)
        
        # In a real system, you would also update your face recognition model here
        
        return jsonify({"success": True, "message": "Image deleted successfully"})
    except Exception as e:
        print(f"Error in delete_image: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@bp.route('/delete', methods=['POST'])
@login_required
def delete_person():
    """Delete a person and all their images"""
    try:
        name = request.form.get('name')
        if not name:
            return jsonify({"success": False, "error": "No name provided"})
        
        # Sanitize name
        safe_name = secure_filename(name)
        
        # Build path to person directory
        person_dir = os.path.join(config.DATASET_DIR, safe_name)
        
        if not os.path.exists(person_dir):
            return jsonify({"success": False, "error": f"Person '{name}' not found"})
        
        # Delete all files in the directory
        for file in os.listdir(person_dir):
            os.remove(os.path.join(person_dir, file))
        
        # Delete the directory itself
        os.rmdir(person_dir)
        
        # In a real system, you would also update your face recognition model here
        
        return jsonify({"success": True, "message": f"Person '{name}' deleted successfully"})
    except Exception as e:
        print(f"Error in delete_person: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
import sys
import os
import cv2
import pickle
import json
import numpy as np
import time
from datetime import datetime

def log_message(message, log_file=None, is_error=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {'ERROR: ' if is_error else ''}[FaceLearner] {message}"
    print(log_line)
    if log_file:
        with open(log_file, "a") as f:
            f.write(log_line + "\n")

def learn_face(image_path, name, encodings_file, output_file):
    logs = []
    success = False
    
    try:
        logs.append(f"Processing image: {image_path}")
        
        if not os.path.exists(image_path):
            logs.append(f"Image file not found: {image_path}")
            return False, logs
        
        image = cv2.imread(image_path)
        if image is None:
            logs.append("Failed to load image file")
            return False, logs
            
        max_size = 640
        h, w = image.shape[:2]
        if h > max_size or w > max_size:
            scale = max_size / max(h, w)
            image = cv2.resize(image, (int(w * scale), int(h * scale)))
            logs.append(f"Resized image to {image.shape[1]}x{image.shape[0]}")
        
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        try:
            import face_recognition
            
            logs.append("Detecting faces...")
            face_locations = face_recognition.face_locations(rgb_image, model="hog")
            
            if not face_locations:
                logs.append("No faces found in the image")
                return False, logs
                
            logs.append(f"Found {len(face_locations)} faces")
            
            largest_face = max(face_locations, key=lambda rect: (rect[2] - rect[0]) * (rect[1] - rect[3]))
            
            logs.append("Generating face encoding...")
            face_encodings = face_recognition.face_encodings(rgb_image, [largest_face])
            
            if not face_encodings:
                logs.append("Failed to encode face")
                return False, logs
                
            face_encoding = face_encodings[0]
            
            data = {"encodings": [], "names": []}
            if os.path.exists(encodings_file):
                try:
                    with open(encodings_file, "rb") as f:
                        data = pickle.load(f)
                    logs.append(f"Loaded existing encodings file with {len(data['encodings'])} faces")
                except Exception as e:
                    logs.append(f"Error loading encodings file: {str(e)}")
                    logs.append("Creating new encodings file")
            
            data["encodings"].append(face_encoding)
            data["names"].append(name)
            
            with open(encodings_file, "wb") as f:
                pickle.dump(data, f)
                
            logs.append(f"Successfully added {name} to encodings file")
            success = True
            
        except Exception as e:
            logs.append(f"Error in face recognition: {str(e)}")
            return False, logs
            
    except Exception as e:
        logs.append(f"Error processing face: {str(e)}")
        return False, logs
        
    return success, logs

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python face_learner.py <image_path> <name> <encodings_file> <output_file>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    name = sys.argv[2]
    encodings_file = sys.argv[3]
    output_file = sys.argv[4]
    
    success, logs = learn_face(image_path, name, encodings_file, output_file)
    
    result = {
        "success": success,
        "logs": logs
    }
    
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
        
    sys.exit(0 if success else 1)
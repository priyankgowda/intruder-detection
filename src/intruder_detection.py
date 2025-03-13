import os
import cv2
import pickle
import face_recognition
import numpy as np
import time
from datetime import datetime
import config
import alerts
from src.recorder import recorder
import atexit

# Near the top, create a global variable to track encodings
known_encodings = None
known_names = None
face_trackers = {}
present_people = {}

# Add this global variable at the top of the file
tracking_api_warning_shown = False

def log_message(message, is_error=False, console_only=True):
    """Technical logging function - only prints to console by default"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {'ERROR: ' if is_error else ''}{message}")
    
    # Detection log completely removed

def log_activity(message):
    """Human activity logging function - for important events"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    
    # Always log activities to the activity log
    log_file = os.path.join(config.LOGS_DIR, "activity_log.txt")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def reload_encodings():
    """Reload face encodings from file without restarting"""
    global known_encodings, known_names
    
    loaded_encodings, loaded_names = load_encodings()
    if loaded_encodings is not None:
        known_encodings = loaded_encodings
        known_names = loaded_names
        if len(known_encodings) > 0:
            log_message(f"Reloaded {len(known_encodings)} face encodings", console_only=True)
            # Try to update existing trackers with new identities
            if 'face_trackers' in globals() and face_trackers:
                update_tracker_identities()
        return True
    return False

# Add this function near the reload_encodings function
def update_tracker_identities():
    """Update existing tracker identities when face encodings are reloaded"""
    if not known_encodings or len(known_encodings) == 0:
        return  # Can't update without encodings
    
    updated_count = 0
    
    # Check each active tracker that has Intruder label
    for tracker_id, tracker_info in list(face_trackers.items()):
        if tracker_info["name"] == "Intruder":
            # Get current face position
            x, y, w, h = tracker_info["box"]
            
            # Get a small frame around the face for recognition
            face_img = video_capture.read()[1][y:y+h, x:x+w]
            if face_img.size == 0:
                continue
                
            # Resize for face_recognition
            small_face = cv2.resize(face_img, (0, 0), fx=0.25, fy=0.25)
            rgb_face = cv2.cvtColor(small_face, cv2.COLOR_BGR2RGB)
            
            # Try to detect and encode the face
            face_locations = face_recognition.face_locations(rgb_face)
            if not face_locations:
                continue
                
            face_encodings = face_recognition.face_encodings(rgb_face, face_locations)
            if not face_encodings:
                continue
                
            # Compare with known faces
            matches = face_recognition.compare_faces(
                known_encodings, face_encodings[0], 
                tolerance=config.FACE_RECOGNITION_TOLERANCE
            )
            
            if True in matches:
                face_distances = face_recognition.face_distance(known_encodings, face_encodings[0])
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    new_name = known_names[best_match_index]
                    old_name = tracker_info["name"]
                    
                    # Only update if we have a real name
                    if new_name != "Intruder" and old_name != new_name:
                        tracker_info["name"] = new_name
                        log_activity(f"Intruder identified as {new_name}")
                        log_activity(f"{new_name} entered the room")
                        present_people[new_name] = time.time()
                        updated_count += 1
    
    if updated_count > 0:
        log_message(f"Updated {updated_count} tracker identities after encodings reload", console_only=True)

# Update the load_encodings function to use the global variables
def load_encodings():
    """Load face encodings from file with minimal error messages"""
    if not os.path.exists(config.ENCODINGS_FILE):
        return None, None
        
    try:
        with open(config.ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            
        # Check if data is a dictionary with expected keys
        if not isinstance(data, dict) or "encodings" not in data or "names" not in data:
            create_empty_encodings_file()
            return None, None
        
        # Check if lists are empty or have different lengths    
        if not data["encodings"] or not data["names"] or len(data["encodings"]) != len(data["names"]):
            return None, None
            
        return data["encodings"], data["names"]
    except Exception:
        # The file might be corrupt, let's recreate it
        create_empty_encodings_file()
        return None, None

def create_empty_encodings_file():
    """Create an empty but valid encodings file"""
    try:
        data = {"encodings": [], "names": []}
        with open(config.ENCODINGS_FILE, "wb") as f:
            pickle.dump(data, f)
        log_message("Created new empty encodings file")
    except Exception as e:
        log_message(f"Error creating empty encodings file: {str(e)}", True)

# Update the function that creates the tracker
def create_tracker(tracker_type=None):
    global tracking_api_warning_shown
    
    # Try to create the specified tracker
    if tracker_type and hasattr(cv2, tracker_type):
        return cv2.TrackerKCF_create()
    
    # Log warning only once instead of repeatedly
    if not tracking_api_warning_shown:
        log_message("No OpenCV tracking API available, using custom tracking", is_error=True)
        tracking_api_warning_shown = True
    
    # Return alternative tracker silently without log message
    return SimpleTracker()

# Implement a basic tracker that doesn't rely on OpenCV's tracking API
class SimpleTracker:
    def __init__(self):
        self.bbox = None
        self.template = None
        self.last_position = None
        
    def init(self, frame, bbox):
        self.bbox = bbox
        x, y, w, h = [int(v) for v in bbox]
        self.template = frame[y:y+h, x:x+w].copy()
        self.last_position = bbox
        return True
        
    def update(self, frame):
        if self.last_position is None:
            return False, self.bbox
            
        # Get the previous position
        x, y, w, h = [int(v) for v in self.last_position]
        
        # Define search region (slightly larger than previous bbox)
        search_size = 10  # pixels to expand search area
        h_frame, w_frame = frame.shape[:2]
        
        # Make sure search area is within frame bounds
        x_start = max(0, x - search_size)
        y_start = max(0, y - search_size)
        x_end = min(w_frame, x + w + search_size)
        y_end = min(h_frame, y + h + search_size)
        
        # If search area is too small, return failure
        if x_end - x_start < w or y_end - y_start < h:
            return False, self.bbox
            
        # Simple template matching
        search_area = frame[y_start:y_end, x_start:x_end]
        try:
            result = cv2.matchTemplate(search_area, self.template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            # If confidence is too low, consider tracking lost
            if max_val < 0.5:  # Threshold for confidence
                return False, self.bbox
                
            # Update position with best match
            new_x = x_start + max_loc[0]
            new_y = y_start + max_loc[1]
            self.last_position = (new_x, new_y, w, h)
            
            # Update template occasionally to adapt to changes
            if max_val > 0.7:
                self.template = frame[new_y:new_y+h, new_x:new_x+w].copy()
                
            return True, self.last_position
        except:
            return False, self.bbox

def non_max_suppression(boxes, overlap_thresh):
    """Apply non-maximum suppression to avoid detecting the same face multiple times"""
    if len(boxes) == 0:
        return []
    
    # Convert to numpy array
    boxes = np.array(boxes)
    
    # Extract coordinates
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    
    # Calculate area of each box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    
    # Sort by confidence score (last column)
    idxs = np.argsort(boxes[:, 4])
    
    # Initialize list of picked indices
    pick = []
    
    # Keep looping while indexes remain
    while len(idxs) > 0:
        # Grab last index (highest confidence)
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        
        # Find coordinates of intersection
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        
        # Find dimensions of intersection
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        
        # Calculate IoU (intersection over union)
        overlap = (w * h) / area[idxs[:last]]
        
        # Delete indexes with IoU > threshold
        idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))
        
    return pick

# Add a function to check if a tracker already exists for a face
def tracker_exists_for_face(face_trackers, face_position, iou_threshold=0.5):
    """Check if there's already a tracker for this face position"""
    x, y, w, h = face_position
    
    for track_info in face_trackers.values():
        tx, ty, tw, th = track_info["box"]
        
        # Calculate IoU
        xx1 = max(tx, x)
        yy1 = max(ty, y)
        xx2 = min(tx + tw, x + w)
        yy2 = min(ty + th, y + h)
        
        if xx2 < xx1 or yy2 < yy1:
            continue
            
        intersection_area = (xx2 - xx1) * (yy2 - yy1)
        my_area = w * h
        tracker_area = tw * th
        union_area = my_area + tracker_area - intersection_area
        
        if intersection_area / union_area > iou_threshold:
            return True
            
    return False

# Update the intruder detection function to capture multiple images

def process_intruder(frame, face_location, name="Unknown"):
    """Process a detected intruder - save image, send alert, etc."""
    global last_alert_time
    
    current_time = time.time()
    # Check if enough time has passed since last alert
    if current_time - last_alert_time < config.MIN_SECONDS_BETWEEN_ALERTS:
        return
        
    last_alert_time = current_time
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    intruder_image = f"intruder_{timestamp}.jpg"
    intruder_video = f"intruder_{timestamp}.avi"
    
    # Save initial intruder image
    image_path = os.path.join(config.INTRUDERS_IMAGES_DIR, intruder_image)
    cv2.imwrite(image_path, frame)
    
    log_message("Intruder detected!", console_only=False)
    
    # Queue the alert with the image file
    alerts.queue_alert(image_path, intruder_video)
    
    # Capture additional images for training
    training_images = [image_path]  # Start with the initial image
    
    # Set up a timer to capture additional training images
    def capture_training_images():
        training_count = 1  # We already have one image
        
        while training_count < config.TRAINING_IMAGES_PER_PERSON:
            time.sleep(config.TRAINING_IMAGE_INTERVAL)
            
            # Check if detection is still running
            if not detection_active:
                break
                
            # Capture a new frame
            ret, additional_frame = video_capture.read()
            if not ret:
                continue
                
            # Save additional training image
            additional_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            additional_image = f"training_{name}_{additional_timestamp}.jpg"
            additional_path = os.path.join(config.INTRUDERS_IMAGES_DIR, additional_image)
            cv2.imwrite(additional_path, additional_frame)
            
            training_images.append(additional_path)
            training_count += 1
            
        # After capturing images, update the alert with all training images
        alerts.update_training_images(training_images)
    
    # Start the training image capture thread
    import threading
    training_thread = threading.Thread(target=capture_training_images)
    training_thread.daemon = True
    training_thread.start()

# Add a camera warmup function and optimize webcam initialization

def init_camera(camera_index=0):
    """Initialize the camera with proper settings and minimal warm-up period"""
    # Open the camera
    cap = cv2.VideoCapture(camera_index)
    
    # Configure camera settings
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering for lower latency
    
    # Shorter warm-up period
    for _ in range(5):  # Reduced from 10 to 5 frames
        cap.read()
    
    return cap

# Update detect_intruders to use the global variables
def detect_intruders():
    """Main function to detect intruders from webcam"""
    global known_encodings, known_names, detection_active, video_capture
    
    detection_active = True
    
    # Initialize camera first - don't wait for encodings
    log_message("Starting camera...", console_only=True)
    video_capture = init_camera(config.CAMERA_INDEX)
    
    # Quietly load face encodings in background without excessive error messages
    try:
        known_encodings, known_names = load_encodings()
        if known_encodings is None or not known_encodings:
            known_encodings = []
            known_names = []
    except Exception:
        known_encodings = []
        known_names = []
    
    # Initialize variables for tracking
    present_people = {}
    last_alert_time = 0
    frame_count = 0
    process_this_frame = 0
    next_track_id = 0
    face_trackers = {}
    
    # Initialize recorder if enabled
    if config.RECORDING_ENABLED:
        recorder.start()
    
    log_message("Intruder detection started", console_only=True)
    
    # Variables for tracking presence
    last_alert_time = 0
    process_this_frame = True
    
    # Dictionary to store active trackers
    face_trackers = {}
    next_track_id = 0
    
    # Dictionary to keep track of who's in the room
    present_people = {}
    
    # Create a sample tracker to check availability
    sample_tracker = create_tracker()
    tracker_available = sample_tracker is not None
    
    # Add a variable to track when we last reloaded
    last_reload_time = time.time()
    
    try:
        while True:
            # Read frame from webcam
            ret, frame = video_capture.read()
            if not ret:
                log_message("Failed to grab frame", True)
                break
            
            # Add frame to recorder if enabled
            if config.RECORDING_ENABLED:
                recorder.add_frame(frame)
            
            current_time = time.time()
            current_frame_people = set()
            
            # Check if it's time to reload encodings (every 10 seconds)
            if current_time - last_reload_time > 10:  # Every 10 seconds
                if reload_encodings() and 'face_trackers' in globals() and face_trackers:
                    # After reload, check if any "Intruder" can now be recognized
                    update_tracker_identities()
                last_reload_time = current_time
            
            # Update all active trackers if tracking is available
            if tracker_available:
                active_trackers = list(face_trackers.keys())
                for track_id in active_trackers:
                    tracker_info = face_trackers[track_id]
                    success, bbox = tracker_info["tracker"].update(frame)
                    
                    if success:
                        # Update tracker information
                        tracker_info["last_seen"] = current_time
                        tracker_info["box"] = bbox
                        
                        # Add to detected people
                        name = tracker_info["name"]
                        current_frame_people.add(name)
                        present_people[name] = current_time
                        
                        # Draw the tracking box
                        x, y, w, h = [int(v) for v in bbox]
                        
                        # Draw a box around the face
                        color = (0, 255, 0)  # Green for tracked faces
                        if name == "Intruder":  # Changed from "Unknown"
                            color = (0, 0, 255)  # Red for intruders
                        
                        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                        
                        # Draw a label with the name
                        cv2.rectangle(frame, (x, y-25), (x+w, y), color, cv2.FILLED)
                        cv2.putText(frame, name, (x+6, y-6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
                    else:
                        # If tracker lost for too long, remove it
                        if current_time - tracker_info["last_seen"] > config.TRACKER_TIMEOUT:
                            del face_trackers[track_id]
            
            # Only do face recognition periodically to save processing
            if process_this_frame:
                # Resize frame for faster face recognition
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                # Find all faces in the current frame
                face_locations = face_recognition.face_locations(rgb_small_frame)
                
                # Filter out overlapping face detections using NMS
                filtered_face_locations = []
                
                # Convert face_locations to format for NMS (left, top, right, bottom, score)
                boxes = []
                for top, right, bottom, left in face_locations:
                    boxes.append([left, top, right, bottom, 1.0])  # All faces have same confidence
                
                if boxes:
                    # NMS to filter out overlapping boxes
                    indices = non_max_suppression(boxes, config.NMS_IOU_THRESHOLD)
                    filtered_face_locations = [face_locations[i] for i in indices]
                else:
                    filtered_face_locations = []
                
                face_encodings = face_recognition.face_encodings(rgb_small_frame, filtered_face_locations)
                
                # Process each detected face
                for i, (face_encoding, face_location) in enumerate(zip(face_encodings, filtered_face_locations)):
                    top, right, bottom, left = face_location
                    
                    # Scale back up face locations
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    
                    # Calculate position for tracker
                    x, y, w, h = left, top, right-left, bottom-top
                    
                    # Try to recognize the face
                    name = "Intruder"  # Default name for everyone
                    
                    # Only attempt recognition if we have encodings
                    if known_encodings:
                        matches = face_recognition.compare_faces(
                            known_encodings, face_encoding, tolerance=config.FACE_RECOGNITION_TOLERANCE
                        )
                        
                        # Use the known face with the smallest distance and check confidence
                        if True in matches:
                            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                            best_match_index = np.argmin(face_distances)
                            best_match_distance = face_distances[best_match_index]
                            best_match_name = known_names[best_match_index]
                            
                            # Only accept if confidence is high enough
                            if matches[best_match_index] and best_match_distance < 0.6:  # Fixed threshold
                                # Check if this person was previously an Intruder
                                old_name = "Intruder"  # Default assumption
                                
                                # Look for matching trackers to see if identity changed
                                for track_id, track_info in face_trackers.items():
                                    tx, ty, tw, th = track_info["box"]
                                    # Check if this face location significantly overlaps with the tracker
                                    if (tx < x+w and tx+tw > x and ty < y+h and ty+th > y):
                                        old_name = track_info["name"]
                                        break
                                        
                                # If identity changed from Intruder to a known person, log it
                                if old_name == "Intruder" and best_match_name != "Intruder":
                                    log_activity(f"Intruder identified as {best_match_name}")
                                    log_activity(f"{best_match_name} entered the room")
                                    
                                name = best_match_name
                    
                    if tracker_available:
                        # Check if this face overlaps with any existing tracker
                        matched_tracker = False
                        best_overlap = 0
                        best_tracker_id = None

                        for track_id, tracker_info in face_trackers.items():
                            tx, ty, tw, th = tracker_info["box"]
                            
                            # Calculate IoU (Intersection over Union)
                            # First find intersection coordinates
                            xx1 = max(tx, x)
                            yy1 = max(ty, y)
                            xx2 = min(tx + tw, x + w)
                            yy2 = min(ty + th, y + h)
                            
                            # Calculate area of intersection and union
                            intersection_area = max(0, xx2 - xx1) * max(0, yy2 - yy1)
                            union_area = (tw * th) + (w * h) - intersection_area
                            
                            # Calculate IoU
                            iou = intersection_area / union_area if union_area > 0 else 0
                            
                            # Check if there's significant overlap
                            if iou > 0.3:  # 30% overlap threshold
                                matched_tracker = True
                                
                                # If this is a better match than previous ones, remember it
                                if iou > best_overlap:
                                    best_overlap = iou
                                    best_tracker_id = track_id
                                    
                        # Update the best matching tracker with new info
                        if matched_tracker and best_tracker_id is not None:
                            # Update tracker with new position
                            tracker_info = face_trackers[best_tracker_id]
                            
                            # Only update name if the new detection has a name
                            if name != "Intruder":
                                tracker_info["name"] = name
                                
                            # Re-initialize tracker with new position for better tracking
                            new_tracker = create_tracker()
                            if new_tracker:
                                try:
                                    success = new_tracker.init(frame, (x, y, w, h))
                                    if success:
                                        tracker_info["tracker"] = new_tracker
                                        tracker_info["box"] = (x, y, w, h)
                                        tracker_info["last_seen"] = current_time
                                except Exception as e:
                                    pass
                        
                        # If no match with existing tracker, create a new one
                        if not matched_tracker:
                            # Only create a new tracker if it doesn't overlap with any existing one
                            if not tracker_exists_for_face(face_trackers, (x, y, w, h), 0.4):
                                if name != "Intruder":  # Changed from "Unknown"
                                    # Person newly recognized
                                    if name not in present_people:
                                        log_activity(f"{name} entered the room")
                                    present_people[name] = current_time
                                elif current_time - last_alert_time > config.MIN_SECONDS_BETWEEN_ALERTS:
                                    # Handle intruder detection
                                    log_activity("Intruder detected!")
                                    last_alert_time = alerts.handle_intruder_detection(frame, current_time, last_alert_time)
                                    
                                # Create new tracker for this face
                                tracker = create_tracker()
                                if tracker:  # Only if tracker creation succeeded
                                    try:
                                        success = tracker.init(frame, (x, y, w, h))
                                        if success:
                                            face_trackers[next_track_id] = {
                                                "tracker": tracker,
                                                "name": name,
                                                "last_seen": current_time,
                                                "box": (x, y, w, h)
                                            }
                                            next_track_id += 1
                                    except Exception as e:
                                        log_message(f"Error initializing tracker: {e}", True)
                            else:
                                # Skip creating a duplicate tracker
                                pass
                    else:
                        # Simple persistence mode - just update the present people directly
                        if name != "Intruder":  # Changed from "Unknown"
                            if name not in present_people:
                                log_activity(f"{name} entered the room")
                            present_people[name] = current_time
                        elif current_time - last_alert_time > config.MIN_SECONDS_BETWEEN_ALERTS:
                            # Handle intruder detection
                            log_activity("Intruder detected!")  # Changed message
                            last_alert_time = alerts.handle_intruder_detection(frame, current_time, last_alert_time)
                        
                        # Draw the box in simple persistence mode
                        color = (0, 0, 255) if name == "Intruder" else (0, 255, 0)
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                        cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)
            
            # Process people who left the room
            for person in list(present_people.keys()):
                if current_time - present_people[person] > config.PERSON_TIMEOUT:
                    log_activity(f"{person} left the room")
                    del present_people[person]
            
            # Toggle frame processing flag
            process_this_frame = not process_this_frame
                
            # Display the resulting image
            cv2.imshow('Intruder Detection', frame)
            
            # Break loop on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        log_message(f"Error in intruder detection: {str(e)}", True)
    finally:
        # Stop recording
        if config.RECORDING_ENABLED:
            recorder.stop()
            
        # Release webcam and close windows
        video_capture.release()
        cv2.destroyAllWindows()
        log_message("Intruder detection stopped")

def get_reload_encodings_function():
    """Return a reference to the reload_encodings function"""
    return reload_encodings

def cleanup():
    """Clean up resources when detection is stopped"""
    global detection_active, video_capture
    
    detection_active = False
    
    # Release video capture if it's initialized
    if video_capture is not None:
        video_capture.release()
        video_capture = None
    
    log_message("Resources cleaned up", console_only=True)

# Make sure to call this function when stopping detection
atexit.register(cleanup)  # Add this near the top with other imports

if __name__ == "__main__":
    # Register reload function with alerts module
    from src import alerts
    alerts.set_reload_encodings_func(reload_encodings)
    
    # Start intruder detection
    detect_intruders()
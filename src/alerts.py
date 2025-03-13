import os
import requests
import cv2
from datetime import datetime
import config
import threading
import time
import queue
import face_recognition
import pickle
import shutil
import json

# Add to alerts.py at the top with other imports
import threading
alert_queue_lock = threading.Lock()

# Add these variables to track active training session
_active_training_lock = threading.Lock()
_active_training_image = None  # Stores the filename of the image currently being processed
_pending_alerts = []  # Queue for alerts that arrived during active training

# Dictionary to track sent alerts and their image files
sent_alerts = {}
last_update_id = 0
alert_queue = queue.Queue()
image_to_video_map = {}
conversation_states = {}  # {chat_id: {"state": "awaiting_name", "message_id": msg_id, "image_path": path}}
reload_encodings_func = lambda: False

def set_reload_encodings_func(func):
    """Set the function to reload encodings"""
    global reload_encodings_func
    reload_encodings_func = func
    log_message("Registered reload encodings function")

def log_message(message, is_error=False):
    """Log messages for alerts module"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {'ERROR: ' if is_error else ''}[Alerts] {message}")

def save_intruder_image(frame):
    """Save intruder image with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"intruder_{timestamp}.jpg"
    filepath = os.path.join(config.INTRUDERS_IMAGES_DIR, filename)
    
    cv2.imwrite(filepath, frame)
    log_message(f"Saved intruder image: {filepath}")
    
    return filepath

def is_valid_telegram_token(token):
    """Check if Telegram token has a valid format"""
    import re
    if not token or token == "TELEGRAM_TOKEN" or token == "telegram_bot_api_token":
        return False
    
    pattern = r'^\d+:[A-Za-z0-9_-]+$'
    return bool(re.match(pattern, token))

# Replace your send_telegram_alert function with this fixed version
def send_telegram_alert(image_path, video_path=None, include_buttons=True):
    """Send a Telegram alert with the image and optionally video"""
    if not config.TELEGRAM_ENABLED or not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
        
    try:
        chat_id = config.TELEGRAM_CHAT_ID
        image_filename = os.path.basename(image_path)
        
        # Create caption
        caption = "🚨 *INTRUDER DETECTED* 🚨\n\n"
        caption += "A new person has been detected."
        
        # Only include buttons if requested
        if include_buttons:
            # UPDATED: Combined the buttons into a single "Known person? (add name)" button
            keyboard = [
                [
                    {"text": "👤 Known person? (add name)", "callback_data": f"name:{image_filename}"}
                ],
                [
                    {"text": "⚠️ Intruder", "callback_data": f"intruder:{image_filename}"}
                ]
            ]
            reply_markup = {"inline_keyboard": keyboard}
        else:
            # No buttons for informational alerts during an active session
            reply_markup = None
            caption += "\n\n_(Another face identification is in progress. This is just a notification.)_"
            
        # Send the photo
        url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendPhoto"
        
        if not os.path.exists(image_path):
            log_message(f"Photo file not found: {image_path}", True)
            return False
        
        try:
            with open(image_path, "rb") as photo:
                files = {"photo": photo}
                data = {
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "Markdown",
                    "reply_markup": json.dumps(reply_markup) if reply_markup else None
                }
                log_message(f"Sending Telegram alert to chat ID: {chat_id}")
                response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok") and "result" in result:
                    message_id = result["result"]["message_id"]
                    sent_alerts[message_id] = {
                        "file_path": image_path,
                        "timestamp": time.time()
                    }
                    if video_path:
                        image_to_video_map[image_path] = video_path
                    log_message(f"Telegram alert sent successfully (ID: {message_id})")
                else:
                    log_message("Telegram alert sent but couldn't get message ID")
                return True
            else:
                log_message(f"Failed to send Telegram alert: {response.text}", True)
                return False
        except Exception as e:
            log_message(f"Error sending Telegram alert: {str(e)}", True)
            return False
    except Exception as e:
        log_message(f"Error in send_telegram_alert: {str(e)}", True)
        return False

# Replace your process_alert_queue function
def process_alert_queue():
    """Background thread function to process alert queue"""
    while True:
        try:
            # Get next alert from queue
            alert_data = alert_queue.get()
            
            # Extract data from different possible formats
            if isinstance(alert_data, dict):
                photo_path = alert_data.get("photo_path")
                video_path = None  # No video path in this format
                include_buttons = True
            elif isinstance(alert_data, tuple) and len(alert_data) == 2:
                photo_path, video_path = alert_data
                
                # Check if this is active training image
                with _active_training_lock:
                    is_active = (_active_training_image == os.path.basename(photo_path))
                include_buttons = is_active
            else:
                log_message(f"Unknown alert data format: {alert_data}", True)
                alert_queue.task_done()
                continue
                
            # Send the alert
            success = send_telegram_alert(photo_path, video_path, include_buttons)
            
            if not success:
                log_message("Failed to send alert", True)
                
            alert_queue.task_done()
            
        except Exception as e:
            log_message(f"Error processing alert queue: {str(e)}", True)
            time.sleep(1)
            try:
                alert_queue.task_done()  # Make sure to mark task as done
            except:
                pass

def start_alert_queue_processing():
    """Start a background thread to process alerts from the queue"""
    thread = threading.Thread(target=process_alert_queue, daemon=True)
    thread.start()
    log_message("Started alert queue processing thread")
    return thread

def handle_intruder_detection(frame, current_time, last_alert_time):
    """Handle all intruder detection logic including saving image and sending alerts"""
    intruder_img_path = save_intruder_image(frame)
    intruder_video_path = None
    if hasattr(config, 'RECORDING_ENABLED') and config.RECORDING_ENABLED:
        from src.recorder import recorder
        intruder_video_path = recorder.save_intruder_clip(frame)
        if intruder_video_path:
            image_to_video_map[intruder_img_path] = intruder_video_path
            log_message(f"Mapped image {os.path.basename(intruder_img_path)} to video {os.path.basename(intruder_video_path)}")
    
    if hasattr(config, 'TELEGRAM_ENABLED') and config.TELEGRAM_ENABLED:
        alert_queue.put({
            "photo_path": intruder_img_path,
            "caption": "Intruder detected!"
        })
        log_message("Alert queued for background sending")
        
    return current_time

# Update the process_telegram_updates function to properly handle callback data
def process_telegram_updates():
    """Check for Telegram updates to process callbacks"""
    global last_update_id
    
    if not hasattr(config, 'TELEGRAM_TOKEN') or not config.TELEGRAM_TOKEN:
        return
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            updates = response.json()
            if updates.get("ok") and "result" in updates:
                for update in updates["result"]:
                    if update.get("update_id", 0) > last_update_id:
                        last_update_id = update["update_id"]
                    
                    if "message" in update and "text" in update["message"]:
                        handle_text_message(update["message"])
                    
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        callback_data = callback.get("data", "")
                        message_id = callback.get("message", {}).get("message_id")
                        chat_id = callback.get("message", {}).get("chat", {}).get("id")
                        
                        # Parse callback data which should be in format "action:filename"
                        if ":" in callback_data:
                            action, image_filename = callback_data.split(":", 1)
                            
                            # Handle "Add Name" button
                            if action == "name" and message_id:
                                try:
                                    if message_id in sent_alerts:
                                        image_path = sent_alerts[message_id]["file_path"]
                                        
                                        # Set conversation state
                                        conversation_states[chat_id] = {
                                            "state": "awaiting_name",
                                            "message_id": message_id,
                                            "image_path": image_path
                                        }
                                        
                                        # Acknowledge the callback
                                        confirm_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/answerCallbackQuery"
                                        confirm_data = {
                                            "callback_query_id": callback["id"],
                                            "text": "Please type the person's name"
                                        }
                                        requests.post(confirm_url, data=confirm_data)
                                        
                                        # Update the message
                                        edit_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/editMessageCaption"
                                        edit_data = {
                                            "chat_id": chat_id,
                                            "message_id": message_id,
                                            "caption": "👤 Please type this person's name to train the system:"
                                        }
                                        edit_response = requests.post(edit_url, data=edit_data)
                                        
                                        if edit_response.status_code != 200:
                                            log_message(f"Error editing caption: {edit_response.text}", True)
                                except Exception as e:
                                    log_message(f"Error handling 'name' callback: {str(e)}", True)
                            
                            # Handle "Intruder" button
                            elif action == "intruder" and message_id:
                                try:
                                    # Acknowledge the callback
                                    confirm_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/answerCallbackQuery"
                                    confirm_data = {
                                        "callback_query_id": callback["id"],
                                        "text": "Person confirmed as intruder"
                                    }
                                    requests.post(confirm_url, data=confirm_data)
                                    
                                    # Update the message
                                    edit_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/editMessageCaption"
                                    edit_data = {
                                        "chat_id": chat_id,
                                        "message_id": message_id,
                                        "caption": "⚠️ This person has been confirmed as an INTRUDER."
                                    }
                                    edit_response = requests.post(edit_url, data=edit_data)
                                    
                                    # Send confirmation message
                                    send_message_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
                                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    send_message_data = {
                                        "chat_id": chat_id,
                                        "text": f"⚠️ {timestamp}: User {callback.get('from', {}).get('username', 'Someone')} confirmed this person as an INTRUDER."
                                    }
                                    requests.post(send_message_url, data=send_message_data)
                                    
                                except Exception as e:
                                    log_message(f"Error handling 'intruder' callback: {str(e)}", True)
                        
                        # Handle legacy callback data formats
                        elif callback_data == "yes_know_name" and message_id:
                            try:
                                if message_id in sent_alerts:
                                    image_path = sent_alerts[message_id]["file_path"]
                                    conversation_states[chat_id] = {
                                        "state": "awaiting_name",
                                        "message_id": message_id,
                                        "image_path": image_path
                                    }
                                    confirm_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/answerCallbackQuery"
                                    confirm_data = {
                                        "callback_query_id": callback["id"],
                                        "text": "Please type the person's name"
                                    }
                                    requests.post(confirm_url, data=confirm_data)
                                    
                                    edit_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/editMessageCaption"
                                    edit_data = {
                                        "chat_id": chat_id,
                                        "message_id": message_id,
                                        "caption": "Please type this person's name to train the system:"
                                    }
                                    edit_response = requests.post(edit_url, data=edit_data)
                                    
                                    if edit_response.status_code != 200:
                                        log_message(f"Error editing caption: {edit_response.text}", True)
                            except Exception as e:
                                log_message(f"Error handling yes_know_name: {str(e)}", True)
                                
                        elif callback_data == "no_dont_know_name" and message_id:
                            if handle_known_person(message_id):
                                send_message_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                send_message_data = {
                                    "chat_id": chat_id,
                                    "text": f"✅ {timestamp}: Image and video files have been deleted from the intruder database."
                                }
                                requests.post(send_message_url, json=send_message_data)
                                
                        elif callback_data == "unknown":
                            confirm_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/answerCallbackQuery"
                            confirm_data = {
                                "callback_query_id": callback["id"],
                                "text": "Processing..."
                            }
                            requests.post(confirm_url, data=confirm_data)
                                
                            send_message_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%:%S")
                            send_message_data = {
                                "chat_id": chat_id,
                                "text": f"⚠️ {timestamp}: User {callback.get('from', {}).get('username', 'Someone')} confirmed this person as an UNKNOWN intruder."
                            }
                            requests.post(send_message_url, data=send_message_data)
                                
                            edit_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/editMessageCaption"
                            edit_data = {
                                "chat_id": chat_id,
                                "message_id": message_id,
                                "caption": "⚠️ This alert has been handled - person was confirmed as UNKNOWN"
                            }
                            requests.post(edit_url, data=edit_data)
    except Exception as e:
        log_message(f"Error processing Telegram updates: {str(e)}", True)

def handle_text_message(message):
    """Handle text messages for learning new faces"""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    
    if chat_id in conversation_states and conversation_states[chat_id]["state"] == "awaiting_name":
        try:
            state = conversation_states[chat_id]
            message_id = state["message_id"]
            image_path = state["image_path"]
            
            if not os.path.exists(image_path):
                send_message_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
                error_data = {
                    "chat_id": chat_id,
                    "text": f"❌ Error: The image file cannot be found."
                }
                requests.post(send_message_url, json=error_data)
                del conversation_states[chat_id]
                return
            
            name = text.strip()
            name = ''.join(c for c in name if c.isalnum() or c in ' _-')
            
            if not name:
                send_message_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
                error_data = {
                    "chat_id": chat_id,
                    "text": f"❌ Please provide a valid name."
                }
                requests.post(send_message_url, json=error_data)
                return
                
            send_message_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
            processing_data = {
                "chat_id": chat_id,
                "text": f"Training system to recognize {name}... Please wait."
            }
            requests.post(send_message_url, json=processing_data)
            
            try:
                success = learn_new_face(image_path, name)
                
                if success:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    success_data = {
                        "chat_id": chat_id,
                        "text": f"✅ {timestamp}: Successfully trained the system to recognize {name}!"
                    }
                    requests.post(send_message_url, json=success_data)
                    
                    try:
                        save_to_dataset(image_path, name)
                    except Exception as e:
                        log_message(f"Error saving to dataset: {str(e)}", True)
                    
                    if message_id in sent_alerts:
                        try:
                            handle_known_person(message_id)
                        except Exception as e:
                            log_message(f"Error cleaning up files: {str(e)}", True)
                else:
                    error_data = {
                        "chat_id": chat_id,
                        "text": f"❌ Could not train the system. No clear face detected in the image."
                    }
                    requests.post(send_message_url, json=error_data)
            except Exception as e:
                log_message(f"Error in face learning process: {str(e)}", True)
                error_data = {
                    "chat_id": chat_id,
                    "text": f"❌ Error training the system: {str(e)}"
                }
                requests.post(send_message_url, json=error_data)
                
            del conversation_states[chat_id]
        except Exception as e:
            log_message(f"Error handling text message: {str(e)}", True)
            try:
                send_message_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
                error_data = {
                    "chat_id": chat_id,
                    "text": f"❌ An error occurred while processing your request."
                }
                requests.post(send_message_url, json=error_data)
            except:
                pass
            if chat_id in conversation_states:
                del conversation_states[chat_id]

def learn_new_face(image_path, name):
    """Learn a new face from an intruder image and add to encodings using external process"""
    try:
        import subprocess
        import json
        import os
        import sys
        
        output_file = os.path.join(config.LOGS_DIR, f"face_learner_{int(time.time())}.json")
        face_learner_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "face_learner.py")
        
        log_message(f"Starting face learning process for {name}...")
        
        process = subprocess.Popen([
            sys.executable,
            face_learner_script,
            image_path,
            name,
            config.ENCODINGS_FILE,
            output_file
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            stdout, stderr = process.communicate(timeout=30)
            
            if stdout:
                log_message(f"Face learner output: {stdout.decode('utf-8', errors='ignore')}")
            if stderr:
                log_message(f"Face learner error: {stderr.decode('utf-8', errors='ignore')}", True)
                
        except subprocess.TimeoutExpired:
            process.kill()
            log_message("Face learning process timed out after 30 seconds", True)
            return False
            
        if os.path.exists(output_file):
            try:
                with open(output_file, "r") as f:
                    result = json.load(f)
                
                success = result.get("success", False)
                logs = result.get("logs", [])
                
                for log in logs:
                    log_message(f"FaceLearner: {log}")
                    
                if success:
                    if reload_encodings_func():
                        log_message("Successfully reloaded face encodings after adding new face")
                    else:
                        log_message("Note: Face added but encodings not reloaded automatically")
                
                return success
                
            except Exception as e:
                log_message(f"Error reading face learner result: {str(e)}", True)
                return False
        else:
            log_message("Face learner did not produce output file", True)
            return False
            
    except Exception as e:
        log_message(f"Error running face learner: {str(e)}", True)
        return False

def save_to_dataset(image_path, name):
    """Save the face image to the dataset folder for future training"""
    try:
        person_dir = os.path.join(config.DATASET_DIR, name)
        os.makedirs(person_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = os.path.join(person_dir, f"{timestamp}.jpg")
        
        image = cv2.imread(image_path)
        cv2.imwrite(target_path, image)
        
        log_message(f"Saved face image to dataset: {target_path}")
        return True
    except Exception as e:
        log_message(f"Error saving to dataset: {str(e)}", True)
        return False

def handle_known_person(message_id):
    """Handle when a user marks an intruder as known in Telegram"""
    if message_id in sent_alerts:
        alert_info = sent_alerts[message_id]
        image_path = alert_info["file_path"]
        
        files_deleted = []
        
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                files_deleted.append(f"Image: {os.path.basename(image_path)}")
                log_message(f"Deleted intruder image: {image_path}")
            except Exception as e:
                log_message(f"Failed to delete intruder image: {str(e)}", True)
        
        if image_path in image_to_video_map:
            video_path = image_to_video_map[image_path]
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    files_deleted.append(f"Video: {os.path.basename(video_path)}")
                    log_message(f"Deleted intruder video: {video_path}")
                except Exception as e:
                    log_message(f"Failed to delete intruder video: {str(e)}", True)
            
            del image_to_video_map[image_path]
        
        if files_deleted:
            log_message(f"Deleted files: {', '.join(files_deleted)}")
            return True
        else:
            log_message("No files were found to delete", True)
            return False
    else:
        log_message(f"No alert found with ID: {message_id}", True)
        return False

def start_telegram_polling():
    """Start a background thread to poll for Telegram updates"""
    if not hasattr(config, 'TELEGRAM_ENABLED') or not config.TELEGRAM_ENABLED:
        return None
        
    def polling_task():
        while True:
            process_telegram_updates()
            time.sleep(5)
            
    thread = threading.Thread(target=polling_task, daemon=True)
    thread.start()
    log_message("Started Telegram polling thread")
    return thread

telegram_polling_thread = None
alert_processing_thread = None

if __name__ != "__main__":
    alert_processing_thread = start_alert_queue_processing()
    
    if hasattr(config, 'TELEGRAM_ENABLED') and config.TELEGRAM_ENABLED:
        telegram_polling_thread = start_telegram_polling()

# Update the queue_alert function in alerts.py
def queue_alert(image_path, video_path=None):
    """Queue an alert for sending in background"""
    global _active_training_image, _pending_alerts
    
    # Get just the filename for tracking
    image_filename = os.path.basename(image_path)
    
    with _active_training_lock:
        # Check if we're currently in an active training session
        if _active_training_image is not None:
            # Store this alert for later (no buttons)
            _pending_alerts.append((image_path, video_path))
            log_message(f"Alert queued for later (training in progress): {image_filename}")
            return
        else:
            # No active training - make this the active one
            _active_training_image = image_filename
    
    # Add to main alert queue
    with alert_queue_lock:
        alert_queue.put((image_path, video_path))
    log_message("Alert queued for background sending")

# Update the alert sending function in alerts.py
def process_alerts():
    """Background thread to process the alert queue"""
    global _active_training_image, _pending_alerts
    
    while True:
        # Get the next alert from the queue
        image_path, video_path = alert_queue.get()
        
        try:
            # Extract filename for logging
            image_filename = os.path.basename(image_path)
            
            # Check if video exists and map them together
            if video_path:
                video_filename = os.path.basename(video_path)
                log_message(f"Mapped image {image_filename} to video {video_filename}")
            
            # Send the alert with buttons only if this is the active training image
            with _active_training_lock:
                is_active_training = (_active_training_image == image_filename)
            
            if is_active_training:
                # Send with interactive buttons
                send_telegram_alert(image_path, video_path, include_buttons=True)
            else:
                # Send as information only (no buttons)
                send_telegram_alert(image_path, video_path, include_buttons=False)
                
        except Exception as e:
            log_message(f"Error processing alert: {str(e)}", True)
        finally:
            alert_queue.task_done()

# Update the training completion handler
def complete_face_learning(person_name, success=True):
    """Called when face learning is complete"""
    global _active_training_image, _pending_alerts
    
    # Clear the active training flag
    with _active_training_lock:
        _active_training_image = None
        
        # Check if we have pending alerts
        if _pending_alerts:
            # Get the next pending alert
            next_alert = _pending_alerts.pop(0)
            image_path, video_path = next_alert
            new_active_image = os.path.basename(image_path)
            _active_training_image = new_active_image
            
            # Process this alert with buttons now
            with alert_queue_lock:
                alert_queue.put({"photo_path": image_path, "caption": "Intruder detected!"})
                log_message(f"Processing next pending alert: {new_active_image}")
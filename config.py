import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
INTRUDERS_DIR = os.path.join(BASE_DIR, "intruders")  # Directory for saved intruder images

# Add these new directory paths
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
INTRUDERS_IMAGES_DIR = os.path.join(INTRUDERS_DIR, "images")
INTRUDERS_VIDEOS_DIR = os.path.join(INTRUDERS_DIR, "videos")

# Create directories if they don't exist
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(INTRUDERS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(INTRUDERS_IMAGES_DIR, exist_ok=True)
os.makedirs(INTRUDERS_VIDEOS_DIR, exist_ok=True)

# Face recognition settings
ENCODINGS_FILE = os.path.join(BASE_DIR, "encodings.pickle")
CAMERA_INDEX = 0

# Detection thresholds and parameters
NMS_IOU_THRESHOLD = 0.5  # Non-maximum suppression threshold (0.5 is typical)

# Face recognition settings (for normal operation)
FACE_RECOGNITION_TOLERANCE = 0.6  # Lower is stricter matching (0.6 is typical)
FACE_CONFIDENCE_THRESHOLD = 0.5    # Confidence threshold (higher = more strict)

# Testing values - uncomment to identify yourself as intruder:
# FACE_RECOGNITION_TOLERANCE = 0.4     # Lower = stricter matching
# FACE_CONFIDENCE_THRESHOLD = 0.9      # Higher = requires more confidence

TRACKER_TIMEOUT = 1.0  # Seconds to keep a tracker after losing the face
PERSON_TIMEOUT = 5.0  # Same as above, used in different parts of code
MIN_SECONDS_BETWEEN_ALERTS = 10  # Minimum seconds between sending alerts
PRESENCE_TIMEOUT = 5.0  # Time before considering a person has left the area

# Telegram settings - check both uppercase and lowercase environment variables
TELEGRAM_ENABLED = True  # Set to True to enable Telegram alerts

# Try uppercase names first, then lowercase
TELEGRAM_TOKEN = os.environ.get("telegram_bot_api_token", "")
TELEGRAM_CHAT_ID = os.environ.get("telegram_chat_id", "")

# Recording settings
RECORDING_ENABLED = True
RECORDING_FPS = 10  # Lower FPS for continuous recording to save space
RECORDING_QUALITY = 70  # 0-100, higher is better quality (for continuous)
RECORDING_RESOLUTION = (640, 480)  # Lower resolution for continuous recording
RECORDING_SEGMENT_MINUTES = 10  # Split recordings into segments of this many minutes

# Intruder clip settings
INTRUDER_CLIP_SECONDS_BEFORE = 5  # Seconds of footage before intruder detection to include
INTRUDER_CLIP_SECONDS = 10  # Seconds of footage after intruder detection to include
INTRUDER_RECORDING_FPS = 15  # Higher FPS for intruder clips
INTRUDER_RECORDING_QUALITY = 85  # Higher quality for intruder clips

# Add these lines to your config file

# Intruder video clip recording settings
INTRUDER_CLIP_SECONDS_BEFORE = 5  # How many seconds before detection to include in clip
INTRUDER_CLIP_SECONDS_AFTER = 10  # How many seconds after detection to continue recording
INTRUDER_CLIP_FPS = 20  # Frame rate for intruder clips

# Face detection and recognition settings
FRAMES_TO_SKIP = 3  # Process every Nth frame for face detection (higher = faster but less accurate)

# Web dashboard access settings
WEB_PORT = 5000  # Port for the web dashboard
SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key_change_in_production")  # Flask secret key

# Add these configuration parameters to your config file

# Face training settings
TRAINING_IMAGES_PER_PERSON = 3  # Number of images to capture for training
TRAINING_IMAGE_INTERVAL = 1.0   # Seconds between training image captures

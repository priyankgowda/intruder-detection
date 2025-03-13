import os
import json
import hashlib
from flask_login import UserMixin
import os

# Path to credentials file
CREDENTIALS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "data", 
    "admin_credentials.json"
)

def ensure_credentials_exist():
    """Create default admin credentials if file doesn't exist"""
    if not os.path.exists(os.path.dirname(CREDENTIALS_FILE)):
        os.makedirs(os.path.dirname(CREDENTIALS_FILE))
        
    if not os.path.exists(CREDENTIALS_FILE):
        # Create default credentials (username: admin, password: admin)
        default_credentials = {
            "admin": hash_password("admin")
        }
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(default_credentials, f)
        print("Created default admin credentials (admin/admin)")

def hash_password(password):
    """Hash a password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """Authenticate a user and return User object if valid"""
    ensure_credentials_exist()
    
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            credentials = json.load(f)
        
        if username in credentials:
            stored_hash = credentials[username]
            input_hash = hash_password(password)
            if stored_hash == input_hash:
                return User(username)
        
        return None
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None

class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, id):
        self.id = id
        
    @staticmethod
    def get(user_id):
        """Get a user by ID"""
        ensure_credentials_exist()
        
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                credentials = json.load(f)
            
            if user_id in credentials:
                return User(user_id)
        except:
            pass
        
        return None

def change_password(username, current_password, new_password):
    """Change password for a user"""
    if authenticate_user(username, current_password):
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                credentials = json.load(f)
            
            credentials[username] = hash_password(new_password)
            
            with open(CREDENTIALS_FILE, "w") as f:
                json.dump(credentials, f)
                
            return True
        except Exception as e:
            print(f"Error changing password: {e}")
    
    return False
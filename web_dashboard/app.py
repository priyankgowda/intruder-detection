from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
import os
import sys
import mimetypes
from urllib.parse import urlparse

# Add project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Import configuration
import config
from web_dashboard.authentication import User, authenticate_user
from web_dashboard.routes import register_routes

# Initialize Flask app
app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')
app.secret_key = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = os.path.join(config.DATASET_DIR)

# Set response headers to prevent caching for dynamic content
@app.after_request
def add_header(response):
    # Only add no-cache headers for HTML responses
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Update your login route

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    # Clear any existing flash messages when loading the login page
    session.pop('_flashes', None)
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = authenticate_user(username, password)
        if user:
            login_user(user)
            # Set a new login success message
            flash('Login successful', 'success')
            
            # Get next parameter or default to dashboard
            # Updated to use urlparse instead of url_parse
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard.index')
                
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

# Register all routes
register_routes(app)

@app.route('/')
def index():
    """Root URL redirects to dashboard if logged in, otherwise to login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    else:
        return redirect(url_for('login'))

@app.route('/sidebar-toggle', methods=['POST'])
@login_required
def sidebar_toggle():
    """Toggle sidebar collapsed state in session"""
    if 'sidebar_collapsed' in session:
        session['sidebar_collapsed'] = not session['sidebar_collapsed']
    else:
        session['sidebar_collapsed'] = True
    return '', 204  # No content response

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', 
                          error_title='Page Not Found',
                          error_message='The page you requested does not exist.',
                          error_details='Please check the URL and try again.'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html',
                          error_title='Server Error',
                          error_message='An internal server error occurred.',
                          error_details='Please try again later.'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html',
                          error_title='Access Denied',
                          error_message='You do not have permission to access this resource.',
                          error_details='Please log in with the appropriate credentials.'), 403

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
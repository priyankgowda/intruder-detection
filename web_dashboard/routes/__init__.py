from web_dashboard.routes import dashboard, recordings, logs, people, settings

def register_routes(app):
    """Register all routes with the Flask app"""
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(recordings.bp)
    app.register_blueprint(logs.bp)
    app.register_blueprint(people.bp)
    app.register_blueprint(settings.bp)
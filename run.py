"""
Page Auditor Pro - Application Entry Point

This file imports the application factory 'create_app' from our new
'auditor_pro' package and starts the development server.
"""

from auditor_pro import create_app, db, socketio
from auditor_pro.models import User, Project
import os

# Create the application instance using the factory
config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_name)

@app.shell_context_processor
def make_shell_context():
    """
    Makes the database instance and models available in the
    Flask shell for easy testing and debugging.
    """
    return {'db': db, 'User': User, 'Project': Project}

if __name__ == '__main__':
    """
    Main execution block for running the app directly.
    """
    port = int(os.environ.get('PORT', 5001))

    # We must use socketio.run() to start the server
    # This enables WebSocket (and long-polling) support.
    # We set allow_unsafe_werkzeug=True to allow the reloader to work.
    print(f"Starting SocketIO server on http://127.0.0.1:{port}")
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        allow_unsafe_werkzeug=app.config['DEBUG']
    )
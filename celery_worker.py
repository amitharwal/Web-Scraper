"""
Celery Worker Entry Point
"""

from auditor_pro import create_app, celery
import os

config_name = os.environ.get('FLASK_CONFIG', 'development')

# We still create the app to ensure the context is available for tasks,
# but we no longer need to access app.celery_app here.
app = create_app(config_name)
app.app_context().push()
"""
Authentication Blueprint.
This file just initializes the Blueprint.
"""
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, template_folder='../../templates/auth')

# Import routes at the bottom to avoid circular imports
from . import routes
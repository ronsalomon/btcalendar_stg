import sys
import os

# Add your project directory to the sys.path
project_home = os.path.abspath(os.path.dirname(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the Flask application instance
from app import awp_sync_deltas_web_auth.py as application

# Optionally, if you need to set any environment variables, you can do so here:
# os.environ['FLASK_CONFIG'] = 'production'
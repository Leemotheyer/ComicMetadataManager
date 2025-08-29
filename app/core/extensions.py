"""
Flask extensions for the Comic Metadata Manager
"""

# Placeholder extensions - the actual app doesn't use these
# but they're imported by app/__init__.py

class SQLAlchemy:
    """Placeholder SQLAlchemy class"""
    def init_app(self, app):
        pass

class APScheduler:
    """Placeholder APScheduler class"""
    def init_app(self, app):
        pass

# Database extension
db = SQLAlchemy()

# Scheduler extension
scheduler = APScheduler()

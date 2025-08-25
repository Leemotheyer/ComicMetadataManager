"""
Comic Metadata Manager - Main Application Package
"""

from flask import Flask
from app.core.config import Config
from app.core.extensions import db, scheduler
from app.api.routes import api_bp
from app.core.routes import main_bp

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__, static_folder='../static', template_folder='../templates')
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    scheduler.init_app(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    
    return app
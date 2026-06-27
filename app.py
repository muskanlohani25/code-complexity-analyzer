"""
app.py

This is the entry point for the Code Complexity Analyzer application.
It initializes the Flask app instance and registers the main blueprint containing routes.
"""

from flask import Flask
from routes import main_bp


def create_app() -> Flask:
    """Flask application factory. Creates, configures, and returns the app instance.

    Returns:
        The configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Simple development configuration
    app.config['SECRET_KEY'] = 'code-complexity-analyzer-key-1942'
    
    # Register routing blueprints
    app.register_blueprint(main_bp)
    
    return app


if __name__ == '__main__':
    app = create_app()
    # Run application on local development server
    # Enabling debug=True enables hot reloading during development
    app.run(host='0.0.0.0', port=5001, debug=True)

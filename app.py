from flask import Flask
from config import Config
from models import db
from flask_mail import Mail
import os

mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    mail.init_app(app)

    with app.app_context():
        # This will create tables if they don't exist
        # We wrap in try-except so it doesn't crash if DB isn't setup yet
        try:
            db.create_all()
        except Exception as e:
            print(f"Database connection error or tables already exist. Error: {e}")

    # Register blueprints/routes here
    from routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    # Create the uploads directory for PDFs
    os.makedirs(os.path.join(app.root_path, 'uploads'), exist_ok=True)
    # Create directory for profile pictures
    os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'profile_pics'), exist_ok=True)
    app.run(debug=True)

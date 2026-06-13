from app import create_app
from models import db, SavedFriend

app = create_app()
with app.app_context():
    # Only creates tables that don't exist
    db.create_all()
    print("Database synced with new models.")

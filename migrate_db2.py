from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(50) UNIQUE;"))
        db.session.execute(text("UPDATE users SET username = name;"))
        db.session.commit()
        print("Migration successful: username column added and populated.")
    except Exception as e:
        print("Error or already migrated:", str(e))
        db.session.rollback()

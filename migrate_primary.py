from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE saved_timetables ADD COLUMN is_primary BOOLEAN DEFAULT FALSE;"))
        db.session.commit()
        print("Migration successful: is_primary column added.")
    except Exception as e:
        print("Error or already migrated:", str(e))
        db.session.rollback()

from app import create_app
app = create_app()
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE users ADD COLUMN matric_no VARCHAR(50) UNIQUE;"))
        db.session.execute(text("ALTER TABLE users ADD COLUMN year VARCHAR(20);"))
        db.session.execute(text("ALTER TABLE users ADD COLUMN course VARCHAR(50);"))
        db.session.execute(text("ALTER TABLE users ADD COLUMN group_name VARCHAR(50);"))
        db.session.commit()
        print("Migration successful.")
    except Exception as e:
        print("Error or already migrated:", str(e))
        db.session.rollback()

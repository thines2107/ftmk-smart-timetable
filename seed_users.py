from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if admin:
        admin.name = 'admin'
        
    student = User.query.filter_by(role='student').first()
    if student:
        student.name = 'student'
        
    db.session.commit()
    print("Usernames updated to 'admin' and 'student'.")

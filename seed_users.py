from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    # 1. Create Admin
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            name='Administrator',
            email='admin@utem.edu.my',
            role='admin',
            username='admin_ftmk',
            matric_no='ADMIN001'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print("Admin user created successfully!")
    else:
        print("Admin user already exists.")
        
    # 2. Create Test Student (Optional)
    student = User.query.filter_by(role='student').first()
    if not student:
        student = User(
            name='Test Student',
            email='student@utem.edu.my',
            role='student',
            username='student1',
            matric_no='B032410001',
            course='BITA',
            year='Year 3'
        )
        student.set_password('student123')
        db.session.add(student)
        print("Test student created successfully!")
    else:
        print("Student user already exists.")
        
    db.session.commit()
    print("\n--- Default Credentials ---")
    print("Admin Login: admin@utem.edu.my | Password: admin123")
    print("User Login:  student@utem.edu.my | Password: student123")

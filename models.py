from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student') # 'admin' or 'student'
    
    # New Registration Fields
    username = db.Column(db.String(50), unique=True, nullable=True)
    matric_no = db.Column(db.String(50), unique=True, nullable=True)
    year = db.Column(db.String(20), nullable=True)
    course = db.Column(db.String(50), nullable=True)
    group_name = db.Column(db.String(50), nullable=True)
    
    # Profile Picture
    profile_pic = db.Column(db.String(255), nullable=True, default='default.png')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Timetable(db.Model):
    __tablename__ = 'timetable'
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(50))   # e.g., BITA, BITC
    semester = db.Column(db.String(50))      # e.g., Semester 2 Session 2025 / 2026
    group_name = db.Column(db.String(50))    # e.g., S1G1
    subject_code = db.Column(db.String(50))  # e.g., BITP1123
    subject_name = db.Column(db.String(200)) 
    class_type = db.Column(db.String(50))    # LEC / LAB
    day = db.Column(db.String(20))           # Monday, Tuesday, etc.
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    room = db.Column(db.String(100))
    lecturer_name = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'semester': self.semester,
            'group_name': self.group_name,
            'subject_code': self.subject_code,
            'subject_name': self.subject_name,
            'class_type': self.class_type,
            'day': self.day,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'room': self.room,
            'lecturer_name': self.lecturer_name
        }

class SavedTimetable(db.Model):
    __tablename__ = 'saved_timetables'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False, default="My Saved Timetable")
    data = db.Column(db.Text, nullable=False) # Will store JSON string of the timetable combination
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('saved_timetables', lazy=True))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'data': json.loads(self.data),
            'is_primary': self.is_primary,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class SavedFriend(db.Model):
    __tablename__ = 'saved_friends'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_matric = db.Column(db.String(50), nullable=False)
    friend_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('saved_friends', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'friend_matric': self.friend_matric,
            'friend_name': self.friend_name
        }

class LecturerProfile(db.Model):
    __tablename__ = 'lecturer_profiles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(100))
    email = db.Column(db.String(120))
    department = db.Column(db.String(100))
    block = db.Column(db.String(50))
    office_room = db.Column(db.String(100))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'title': self.title,
            'email': self.email,
            'department': self.department,
            'block': self.block,
            'office_room': self.office_room
        }

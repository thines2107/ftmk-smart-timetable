from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from models import db, Timetable, User, SavedTimetable, SavedFriend, LecturerProfile
from pdf_extractor import extract_timetable_from_pdf
from generator import generate_combinations
from datetime import datetime
import os
import functools
import uuid
import threading
import pandas as pd
from fuzzywuzzy import process
from flask import current_app
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

bp = Blueprint('main', __name__)

@bp.route('/seed_admin_fptt')
def seed_admin_fptt():
    try:
        if not User.query.filter_by(username='admin_fptt').first():
            new_admin = User(
                username='admin_fptt',
                name='Admin FPTT',
                email='admin_fptt@utem.edu.my',
                role='admin',
                matric_no='ADMIN02'
            )
            new_admin.set_password('admin')
            db.session.add(new_admin)
            db.session.commit()
            return "Success: Admin FPTT created (username: admin_fptt, pass: admin)"
        return "Admin FPTT already exists"
    except Exception as e:
        return str(e)

@bp.context_processor
def inject_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return dict(current_user=user)
    return dict(current_user=None)
EXTRACTION_PROGRESS = {}

def background_extraction_task(app, filepath, task_id, semester_name):
    with app.app_context():
        try:
            EXTRACTION_PROGRESS[task_id] = {'percent': 0, 'message': 'Starting extraction...', 'status': 'processing'}
            data = extract_timetable_from_pdf(filepath, EXTRACTION_PROGRESS, task_id, semester_name)
            
            EXTRACTION_PROGRESS[task_id] = {'percent': 100, 'message': 'Saving to database...', 'status': 'processing'}
            for entry in data:
                st = datetime.strptime(entry['start_time'], '%H:%M:%S').time()
                et = datetime.strptime(entry['end_time'], '%H:%M:%S').time()
                new_t = Timetable(
                    course_code=entry.get('course_code', 'UNKNOWN'),
                    semester=entry.get('semester_name', 'Unknown Semester'),
                    group_name=entry.get('group_name', 'UNKNOWN'),
                    subject_code=entry['subject_code'],
                    subject_name=entry.get('subject_name', ''),
                    class_type=entry['class_type'],
                    day=entry['day'],
                    start_time=st,
                    end_time=et,
                    room=entry['room'],
                    lecturer_name=entry['lecturer_name']
                )
                db.session.add(new_t)
            db.session.commit()
            EXTRACTION_PROGRESS[task_id] = {'percent': 100, 'message': f'Extracted {len(data)} records successfully!', 'status': 'completed'}
        except Exception as e:
            EXTRACTION_PROGRESS[task_id] = {'percent': 0, 'message': str(e), 'status': 'error'}

def login_required(role=None):
    def wrapper(fn):
        @functools.wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('main.login'))
            if role and session.get('role') != role:
                flash('Unauthorized access.')
                return redirect(url_for('main.login'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.permanent = False
            session['user_id'] = user.id
            session['role'] = user.role
            
            if user.role == 'admin':
                return redirect(url_for('main.admin_ui'))
            else:
                return redirect(url_for('main.student_ui'))
        flash('Invalid credentials.')
    
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('main.admin_ui'))
        return redirect(url_for('main.student_ui'))
        
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        username = data.get('username')
        email = data.get('email')
        matric_no = data.get('matric_no')
        password = data.get('password')
        course = data.get('course')
        year = data.get('year')
        group_name = data.get('group_name')
        
        if not all([name, username, email, matric_no, password, course, year, group_name]):
            return jsonify({'error': 'All fields are required.'}), 400
            
        import re
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password) or not re.search(r'[^A-Za-z0-9]', password):
            return jsonify({'error': 'Password does not meet complexity requirements.'}), 400
            
        if User.query.filter_by(email=email).first() or User.query.filter_by(matric_no=matric_no).first() or User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username, Email, or Matric No already exists.'}), 400
            
        new_user = User(
            name=name,
            username=username,
            email=email,
            matric_no=matric_no,
            course=course,
            year=year,
            group_name=group_name,
            role='student'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        try:
            db.session.commit()
            return jsonify({'message': 'Registration successful! You can now login.'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Database error occurred.'}), 500
            
    return render_template('register.html')

@bp.route('/api/check_username', methods=['GET'])
def check_username():
    username = request.args.get('username')
    if not username:
        return jsonify({'taken': False}), 200
        
    user = User.query.filter_by(username=username).first()
    return jsonify({'taken': user is not None}), 200

@bp.route('/api/check_email', methods=['GET'])
def check_email():
    email = request.args.get('email')
    if not email:
        return jsonify({'taken': False}), 200
        
    user = User.query.filter_by(email=email).first()
    return jsonify({'taken': user is not None}), 200

@bp.route('/api/check_matric', methods=['GET'])
def check_matric():
    matric_no = request.args.get('matric_no')
    if not matric_no:
        return jsonify({'taken': False}), 200
        
    user = User.query.filter_by(matric_no=matric_no).first()
    return jsonify({'taken': user is not None}), 200

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@bp.route('/student')
@login_required(role='student')
def student_ui():
    """Student portal for selecting subjects and generating timetables."""
    # Fetch distinct courses and subjects for dropdowns
    courses = db.session.query(Timetable.course_code).distinct().all()
    courses = [c[0] for c in courses if c[0]]
    
    subjects = db.session.query(Timetable.subject_code, Timetable.subject_name).distinct().all()
    user = User.query.get(session['user_id'])
    
    return render_template('student.html', courses=courses, subjects=subjects, current_user=user)

@bp.route('/student/lecturers')
@login_required(role='student')
def student_lecturers():
    """Directory of all lecturers, subjects they teach, and their full schedules."""
    # Query all valid records
    records = db.session.query(Timetable).filter(
        Timetable.lecturer_name != None,
        Timetable.lecturer_name != '',
    ).all()
    
    lecturers = {}
    for r in records:
        lname = str(r.lecturer_name).strip().upper()
        if not lname or lname == 'TBA' or 'UNKNOWN' in lname:
            continue
            
        if lname not in lecturers:
            lecturers[lname] = {
                'subjects': set(),
                'schedule': []
            }
            
        subj_info = f"{r.subject_code} - {r.subject_name}"
        lecturers[lname]['subjects'].add(subj_info)
        
        # Format the schedule entry
        start_t = r.start_time.strftime('%H:%M') if r.start_time else ''
        end_t = r.end_time.strftime('%H:%M') if r.end_time else ''
        
        lecturers[lname]['schedule'].append({
            'day': r.day,
            'time': f"{start_t} - {end_t}" if start_t and end_t else "TBA",
            'room': r.room if r.room else "TBA",
            'subject_code': r.subject_code,
            'group_name': r.group_name
        })

    # Sort days chronologically for the schedules and remove duplicates (if any exist)
    day_order = {'MONDAY': 1, 'TUESDAY': 2, 'WEDNESDAY': 3, 'THURSDAY': 4, 'FRIDAY': 5, 'SATURDAY': 6, 'SUNDAY': 7}
    
    # Fetch all profiles
    profiles_db = LecturerProfile.query.all()
    profiles_list = [p.name.upper() for p in profiles_db]
    profiles_dict = {p.name.upper(): p.to_dict() for p in profiles_db}
    
    for lname in lecturers:
        lecturers[lname]['subjects'] = sorted(list(lecturers[lname]['subjects']))
        
        # Fuzzy match to find email and room from profiles
        lecturers[lname]['profile'] = None
        if profiles_list:
            match, score = process.extractOne(lname, profiles_list)
            if score > 80:  # If confidence is > 80%
                lecturers[lname]['profile'] = profiles_dict[match]
                
        # Use a dict to deduplicate exact same schedule slots (in case of DB dupes)
        unique_sched = {}
        for s in lecturers[lname]['schedule']:
            sig = f"{s['day']}|{s['time']}|{s['room']}|{s['subject_code']}|{s['group_name']}"
            if sig not in unique_sched:
                unique_sched[sig] = s
                
        # Sort schedule by day then time
        sched_list = list(unique_sched.values())
        sched_list.sort(key=lambda x: (
            day_order.get(str(x['day']).upper(), 99),
            x['time']
        ))
        
        lecturers[lname]['schedule'] = sched_list
        
    sorted_lecturers = dict(sorted(lecturers.items()))
    user = User.query.get(session['user_id'])
    
    return render_template('lecturers.html', lecturers=sorted_lecturers, current_user=user)

@bp.route('/student/social')
@login_required(role='student')
def student_social():
    """Social timetable overlay page."""
    user = User.query.get(session['user_id'])
    
    # Ensure current user has a primary timetable
    has_primary = SavedTimetable.query.filter_by(user_id=user.id, is_primary=True).first() is not None
    saved_friends = SavedFriend.query.filter_by(user_id=user.id).order_by(SavedFriend.created_at.desc()).all()
    
    return render_template('social.html', current_user=user, has_primary=has_primary, saved_friends=saved_friends)

@bp.route('/api/social/add_friend', methods=['POST'])
@login_required(role='student')
def add_friend():
    data = request.json
    friend_matric = data.get('matric_no')
    
    if not friend_matric:
        return jsonify({'error': 'Matric number is required.'}), 400
        
    # Prevent adding self
    user = User.query.get(session['user_id'])
    if user.matric_no.lower() == friend_matric.lower():
        return jsonify({'error': 'You cannot add yourself.'}), 400
        
    friend = User.query.filter(User.matric_no.ilike(friend_matric), User.role == 'student').first()
    if not friend:
        return jsonify({'error': 'Student not found with that matric number.'}), 404
        
    # Check if already added
    existing = SavedFriend.query.filter_by(user_id=session['user_id'], friend_matric=friend.matric_no).first()
    if existing:
        return jsonify({'error': 'Friend already in your saved list.'}), 400
        
    new_friend = SavedFriend(
        user_id=session['user_id'],
        friend_matric=friend.matric_no,
        friend_name=friend.name
    )
    db.session.add(new_friend)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Friend added successfully!'})

@bp.route('/api/social/remove_friend/<int:id>', methods=['DELETE'])
@login_required(role='student')
def remove_friend(id):
    friend = SavedFriend.query.filter_by(id=id, user_id=session['user_id']).first()
    if not friend:
        return jsonify({'error': 'Friend not found.'}), 404
        
    db.session.delete(friend)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Friend removed.'})

@bp.route('/student/analytics')
@login_required(role='student')
def student_analytics():
    user = User.query.get(session['user_id'])
    my_primary = SavedTimetable.query.filter_by(user_id=user.id, is_primary=True).first()
    
    if not my_primary:
        return render_template('analytics.html', current_user=user, has_primary=False)
        
    import json
    data = json.loads(my_primary.data)
    
    # Calculate stats
    total_classes = 0
    total_hours = 0
    days_count = {}
    type_count = {'Lecture': 0, 'Lab': 0}
    
    for bundle in data:
        for cls in bundle.get('classes', []):
            total_classes += 1
            
            # Calculate hours
            try:
                # time might be HH:MM or HH:MM:SS
                fmt = '%H:%M:%S' if cls['start_time'].count(':') == 2 else '%H:%M'
                st = datetime.strptime(cls['start_time'], fmt)
                et = datetime.strptime(cls['end_time'], fmt)
                diff = (et - st).total_seconds() / 3600.0
                total_hours += diff
                
                # Day count
                day = cls['day']
                days_count[day] = days_count.get(day, 0) + diff
                
                # Class Type count
                ctype = cls.get('class_type', '').upper()
                if 'KUL' in ctype or 'LEC' in ctype:
                    type_count['Lecture'] += diff
                elif 'MAK' in ctype or 'LAB' in ctype:
                    type_count['Lab'] += diff
            except Exception as e:
                pass
                
    busiest_day = max(days_count, key=days_count.get) if days_count else "None"
    
    stats = {
        'total_classes': total_classes,
        'total_hours': round(total_hours, 1),
        'busiest_day': busiest_day,
        'days_count': days_count,
        'type_count': type_count
    }
    
    return render_template('analytics.html', current_user=user, has_primary=True, stats=stats)

@bp.route('/student/classmates')
@login_required(role='student')
def student_classmates():
    user = User.query.get(session['user_id'])
    my_primary = SavedTimetable.query.filter_by(user_id=user.id, is_primary=True).first()
    
    if not my_primary:
        return render_template('classmates.html', current_user=user, has_primary=False)
        
    import json
    my_data = json.loads(my_primary.data)
    
    # Extract my subject-group signatures
    my_subjects = {}
    for bundle in my_data:
        subj = bundle.get('subject')
        grp = bundle.get('group_name')
        if subj and grp:
            my_subjects[f"{subj}|{grp}"] = {'subject': subj, 'group': grp, 'classmates': []}
            
    # Find all other primary timetables
    all_primaries = SavedTimetable.query.filter(SavedTimetable.is_primary == True, SavedTimetable.user_id != user.id).all()
    
    for pt in all_primaries:
        pt_data = json.loads(pt.data)
        for bundle in pt_data:
            subj = bundle.get('subject')
            grp = bundle.get('group_name')
            sig = f"{subj}|{grp}"
            if sig in my_subjects:
                # We have a match!
                friend_user = User.query.get(pt.user_id)
                if friend_user:
                    my_subjects[sig]['classmates'].append({
                        'name': friend_user.name,
                        'course': friend_user.course
                    })
                    
    return render_template('classmates.html', current_user=user, has_primary=True, subjects=my_subjects)

@bp.route('/api/timetable/social', methods=['POST'])
@login_required(role='student')
def api_social_timetable():
    data = request.json
    friend_matric = data.get('matric_no')
    
    if not friend_matric:
        return jsonify({'error': 'Matric number is required.'}), 400
        
    friend = User.query.filter(User.matric_no.ilike(friend_matric), User.role == 'student').first()
    if not friend:
        return jsonify({'error': 'Student not found with that matric number.'}), 404
        
    friend_primary = SavedTimetable.query.filter_by(user_id=friend.id, is_primary=True).first()
    if not friend_primary:
        return jsonify({'error': 'This student has not set a Primary Timetable yet.'}), 404
        
    my_primary = SavedTimetable.query.filter_by(user_id=session['user_id'], is_primary=True).first()
    if not my_primary:
        return jsonify({'error': 'You must set a Primary Timetable in your Saved Timetables first.'}), 400
        
    import json
    return jsonify({
        'friend_name': friend.name,
        'friend_course': friend.course,
        'friend_data': json.loads(friend_primary.data),
        'my_data': json.loads(my_primary.data)
    })

@bp.route('/admin')
@login_required(role='admin')
def admin_ui():
    """Admin portal to view and manage data."""
    records = Timetable.query.all()
    # Group records by semester, then by course code
    grouped_records = {}
    for r in records:
        s = r.semester if r.semester else 'Unknown Semester'
        c = r.course_code if r.course_code else 'UNKNOWN'
        
        if s not in grouped_records:
            grouped_records[s] = {}
        if c not in grouped_records[s]:
            grouped_records[s][c] = []
            
        grouped_records[s][c].append(r)
        
    grouped_records = dict(sorted(grouped_records.items()))
    user = User.query.get(session['user_id'])
        
    return render_template('admin.html', grouped_records=grouped_records, current_user=user)

@bp.route('/api/admin/sync_lecturers', methods=['POST'])
@login_required(role='admin')
def sync_lecturers():
    try:
        from scraper import scrape_ftmk_staff
        profiles = scrape_ftmk_staff()
        
        if not profiles:
            return jsonify({'error': 'No profiles found or scraper failed. Check internet connection.'}), 500
            
        added_count = 0
        updated_count = 0
        
        for p in profiles:
            existing = LecturerProfile.query.filter_by(name=p['name']).first()
            if existing:
                existing.title = p['title']
                existing.email = p['email']
                existing.department = p['department']
                existing.block = p['block']
                existing.office_room = p['office_room']
                updated_count += 1
            else:
                new_prof = LecturerProfile(**p)
                db.session.add(new_prof)
                added_count += 1
                
        db.session.commit()
        return jsonify({'message': f'Synced successfully. Added {added_count}, Updated {updated_count} profiles.'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/students')
@login_required(role='admin')
def admin_students():
    """Admin portal to view and manage registered students."""
    users = User.query.filter_by(role='student').all()
    user_data = []
    for u in users:
        timetable_count = SavedTimetable.query.filter_by(user_id=u.id).count()
        user_data.append({
            'id': u.id,
            'name': u.name,
            'matric_no': u.matric_no,
            'course': u.course,
            'year': u.year,
            'email': u.email,
            'saved_timetables': timetable_count
        })
    user = User.query.get(session['user_id'])
    return render_template('admin_students.html', users=user_data, current_user=user)

@bp.route('/api/admin/student/add', methods=['POST'])
@login_required(role='admin')
def admin_add_student():
    data = request.json
    name = data.get('name')
    username = data.get('username')
    email = data.get('email')
    matric_no = data.get('matric_no')
    password = data.get('password')
    course = data.get('course')
    year = data.get('year')
    group_name = data.get('group_name')
    
    if not all([name, username, email, matric_no, password, course, year]):
        return jsonify({'error': 'Required fields missing.'}), 400
        
    if User.query.filter_by(email=email).first() or User.query.filter_by(matric_no=matric_no).first() or User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username, Email, or Matric No already exists.'}), 400
        
    new_user = User(
        name=name,
        username=username,
        email=email,
        matric_no=matric_no,
        course=course,
        year=year,
        group_name=group_name,
        role='student'
    )
    new_user.set_password(password)
    db.session.add(new_user)
    try:
        db.session.commit()
        return jsonify({'message': 'Student created successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/admin/student/edit', methods=['POST'])
@login_required(role='admin')
def admin_edit_student():
    data = request.json
    student_id = data.get('id')
    
    if not student_id:
        return jsonify({'error': 'Student ID required'}), 400
        
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        return jsonify({'error': 'Student not found'}), 404
        
    student.name = data.get('name', student.name)
    student.course = data.get('course', student.course)
    student.year = data.get('year', student.year)
    student.group_name = data.get('group_name', student.group_name)
    
    # Check uniqueness if changed
    new_email = data.get('email')
    if new_email and new_email != student.email:
        if User.query.filter_by(email=new_email).first():
            return jsonify({'error': 'Email already exists.'}), 400
        student.email = new_email
        
    new_matric = data.get('matric_no')
    if new_matric and new_matric != student.matric_no:
        if User.query.filter_by(matric_no=new_matric).first():
            return jsonify({'error': 'Matric No already exists.'}), 400
        student.matric_no = new_matric
        
    if data.get('password'):
        student.set_password(data['password'])
        
    try:
        db.session.commit()
        return jsonify({'message': 'Student updated successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/admin/student/delete/<int:id>', methods=['DELETE'])
@login_required(role='admin')
def admin_delete_student(id):
    student = User.query.get(id)
    if not student or student.role != 'student':
        return jsonify({'error': 'Student not found'}), 404
        
    try:
        SavedTimetable.query.filter_by(user_id=student.id).delete()
        SavedFriend.query.filter_by(user_id=student.id).delete()
        SavedFriend.query.filter_by(friend_matric=student.matric_no).delete()
        
        db.session.delete(student)
        db.session.commit()
        return jsonify({'message': 'Student deleted successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/lecturers')
@login_required(role='admin')
def admin_lecturers():
    """Admin portal to view lecturer workloads."""
    records = db.session.query(Timetable).filter(
        Timetable.lecturer_name != None,
        Timetable.lecturer_name != ''
    ).all()
    
    workload = {}
    for r in records:
        lname = str(r.lecturer_name).strip().upper()
        if not lname or lname == 'TBA' or 'UNKNOWN' in lname:
            continue
            
        if lname not in workload:
            workload[lname] = {
                'subjects': set(),
                'total_classes': 0,
                'total_hours': 0.0
            }
            
        subj_info = f"{r.subject_code} - {r.subject_name}"
        workload[lname]['subjects'].add(subj_info)
        workload[lname]['total_classes'] += 1
        
        if r.start_time and r.end_time:
            from datetime import datetime, date
            dummy_date = date.today()
            st = datetime.combine(dummy_date, r.start_time)
            et = datetime.combine(dummy_date, r.end_time)
            hours = (et - st).total_seconds() / 3600.0
            workload[lname]['total_hours'] += hours
            
    # Convert subjects to list and sort
    for lname in workload:
        workload[lname]['subjects'] = sorted(list(workload[lname]['subjects']))
        workload[lname]['total_hours'] = round(workload[lname]['total_hours'], 1)
        
    sorted_workload = dict(sorted(workload.items()))
    
    profiles = LecturerProfile.query.all()
    user = User.query.get(session['user_id'])
    
    return render_template('admin_lecturers.html', workload=sorted_workload, profiles=profiles, current_user=user)

@bp.route('/api/admin/lecturer/add', methods=['POST'])
@login_required(role='admin')
def admin_add_lecturer():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Name is required'}), 400
        
    if LecturerProfile.query.filter_by(name=name).first():
        return jsonify({'error': 'Lecturer profile already exists'}), 400
        
    new_prof = LecturerProfile(
        name=name,
        title=data.get('title'),
        email=data.get('email'),
        department=data.get('department'),
        block=data.get('block'),
        office_room=data.get('office_room')
    )
    db.session.add(new_prof)
    try:
        db.session.commit()
        return jsonify({'message': 'Profile added successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/admin/lecturer/edit', methods=['POST'])
@login_required(role='admin')
def admin_edit_lecturer():
    data = request.json
    prof_id = data.get('id')
    if not prof_id:
        return jsonify({'error': 'ID is required'}), 400
        
    prof = LecturerProfile.query.get(prof_id)
    if not prof:
        return jsonify({'error': 'Profile not found'}), 404
        
    prof.name = data.get('name', prof.name)
    prof.title = data.get('title', prof.title)
    prof.email = data.get('email', prof.email)
    prof.department = data.get('department', prof.department)
    prof.block = data.get('block', prof.block)
    prof.office_room = data.get('office_room', prof.office_room)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/admin/lecturer/delete/<int:id>', methods=['DELETE'])
@login_required(role='admin')
def admin_delete_lecturer(id):
    prof = LecturerProfile.query.get(id)
    if not prof:
        return jsonify({'error': 'Profile not found'}), 404
        
    try:
        db.session.delete(prof)
        db.session.commit()
        return jsonify({'message': 'Profile deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/timetable/bulk_delete', methods=['POST'])
@login_required(role='admin')
def bulk_delete():
    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': 'No records selected for deletion.'}), 400
        
    try:
        Timetable.query.filter(Timetable.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'message': f'Deleted {len(ids)} records successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/timetable/update', methods=['POST'])
@login_required(role='admin')
def update_record():
    data = request.json
    record_id = data.get('id')
    
    if not record_id:
        return jsonify({'error': 'Record ID is required.'}), 400
        
    try:
        record = Timetable.query.get(record_id)
        if not record:
            return jsonify({'error': 'Record not found.'}), 404
            
        old_subject_name = record.subject_name
            
        record.subject_code = data.get('subject_code', record.subject_code)
        new_subject_name = data.get('subject_name', record.subject_name)
        record.subject_name = new_subject_name
        
        record.class_type = data.get('class_type', record.class_type)
        record.day = data.get('day', record.day)
        record.group_name = data.get('group_name', record.group_name)
        record.room = data.get('room', record.room)
        record.lecturer_name = data.get('lecturer_name', record.lecturer_name)
        
        # Handle time safely
        from datetime import datetime
        try:
            if data.get('start_time'):
                record.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            if data.get('end_time'):
                record.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Invalid time format. Use HH:MM.'}), 400
            
        updated_ids = [record.id]
        
        # Propagate subject_name changes globally based on subject_code
        if new_subject_name != old_subject_name and new_subject_name and 'UNKNOWN' not in new_subject_name.upper():
            affected = Timetable.query.filter_by(subject_code=record.subject_code).all()
            for a in affected:
                if a.subject_name != new_subject_name:
                    a.subject_name = new_subject_name
                    if a.id not in updated_ids:
                        updated_ids.append(a.id)
            
        db.session.commit()
        return jsonify({
            'message': 'Record updated successfully.', 
            'updated_ids': updated_ids, 
            'subject_name': new_subject_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/upload', methods=['POST'])
def handle_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    semester_name = request.form.get('semester_name', 'Unknown Semester')
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        # Using a fixed uploads path
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        task_id = str(uuid.uuid4())
        app = current_app._get_current_object()
        
        thread = threading.Thread(target=background_extraction_task, args=(app, filepath, task_id, semester_name))
        thread.start()
        
        return jsonify({'task_id': task_id, 'message': 'Upload successful. Processing started.'}), 200
            
    return jsonify({'error': 'Invalid file type'}), 400

@bp.route('/api/progress/<task_id>')
@login_required(role='admin')
def get_progress(task_id):
    progress = EXTRACTION_PROGRESS.get(task_id, {'percent': 0, 'message': 'Unknown task', 'status': 'error'})
    return jsonify(progress)

@bp.route('/api/timetable')
def get_timetable():
    # Filtering query parameters
    course = request.args.get('course')
    subject = request.args.get('subject')
    day = request.args.get('day')
    group = request.args.get('group')

    query = Timetable.query

    if course:
        query = query.filter(Timetable.course_code == course)
    if subject:
        query = query.filter(Timetable.subject_code == subject)
    if day:
        query = query.filter(Timetable.day == day)
    if group:
        query = query.filter(Timetable.group_name == group)

    records = query.all()
    return jsonify({'data': [r.to_dict() for r in records]})

@bp.route('/api/generate', methods=['POST'])
def api_generate_timetable():
    data = request.json
    selected_subjects = data.get('subjects', []) # e.g. ['BITP1123', 'BITS1323']
    
    no_night = data.get('no_night', False)
    no_morning = data.get('no_morning', False)
    free_day = data.get('free_day', '')
    preferred_group = data.get('preferred_group', '')
    blocked_rules = data.get('blocked_rules', [])
    
    if not selected_subjects:
        return jsonify({'error': 'No subjects selected'}), 400
        
    # Fetch logged-in student's course for smart filtering
    user_id = session.get('user_id')
    student_course = None
    if user_id:
        user = User.query.get(user_id)
        if user:
            student_course = user.course
            
    # Group the database records into the format required by generator.py
    subjects_data = {}
    for subj in selected_subjects:
        base_query = Timetable.query.filter_by(subject_code=subj)
        
        classes = base_query.all()
        if not classes:
            continue
            
        if not classes:
            continue
            
        # Determine if this subject requires a LAB and/or LEC globally
        requires_lab = any(c.class_type.upper() == 'LAB' for c in classes if c.class_type)
        requires_lec = any(c.class_type.upper() == 'LEC' for c in classes if c.class_type)
            
        groups_dict = {}
        for c in classes:
            # Group by both course code and group name to prevent cross-course merging of "S1G1"
            g_key = f"{c.course_code}_{c.group_name}"
            if g_key not in groups_dict:
                groups_dict[g_key] = {'group_name': c.group_name, 'subject': subj, 'course_code': c.course_code, 'classes': []}
            groups_dict[g_key]['classes'].append(c.to_dict())
            
        # Prioritization Filter: If legitimate groups exist, remove the fallback UNKNOWN GROUP
        valid_groups = [g for g in groups_dict.keys() if "UNKNOWN GROUP" not in g.upper()]
        if valid_groups:
            # Delete any keys containing UNKNOWN GROUP
            keys_to_delete = [k for k in groups_dict.keys() if "UNKNOWN GROUP" in k.upper()]
            for k in keys_to_delete:
                del groups_dict[k]
            
        # STRICT LEC/LAB VALIDATION
        # Filter out any group bundle that is missing a required class type
        strict_groups_list = []
        for g_bundle in groups_dict.values():
            has_lab = any(c['class_type'].upper() == 'LAB' for c in g_bundle['classes'] if c.get('class_type'))
            has_lec = any(c['class_type'].upper() == 'LEC' for c in g_bundle['classes'] if c.get('class_type'))
            
            is_valid = True
            if requires_lab and not has_lab:
                is_valid = False
            if requires_lec and not has_lec:
                is_valid = False
                
            if is_valid:
                strict_groups_list.append(g_bundle)
                
        # If the strict validation wiped out all groups (bad data), fallback to all groups
        if not strict_groups_list:
            strict_groups_list = list(groups_dict.values())
            
        # ADVANCED BLACKLIST FILTER
        final_groups_list = []
        from datetime import datetime
        fmt = '%H:%M'
        for g_bundle in strict_groups_list:
            bundle_subject = g_bundle['subject']
            bundle_section = g_bundle['group_name']
            
            is_blocked = False
            for rule in blocked_rules:
                # 1. Subject Check
                if rule['subject'] != 'ANY' and rule['subject'] != bundle_subject:
                    continue # Rule doesn't apply to this subject
                    
                # 2. Section Check
                if rule['section'] and rule['section'] != 'ANY':
                    if rule['section'] not in bundle_section.upper():
                        continue # Rule doesn't apply to this section
                        
                # 3. Day / Time Check
                rule_day = rule['day']
                rule_start = rule['start_time']
                rule_end = rule['end_time']
                
                if rule_day != 'ANY' or rule_start or rule_end:
                    time_overlap = False
                    for c in g_bundle['classes']:
                        if rule_day != 'ANY' and c['day'] != rule_day:
                            continue
                            
                        c_start = datetime.strptime(c['start_time'], fmt) if c.get('start_time') else None
                        c_end = datetime.strptime(c['end_time'], fmt) if c.get('end_time') else None
                        
                        r_start = datetime.strptime(rule_start, fmt) if rule_start else None
                        r_end = datetime.strptime(rule_end, fmt) if rule_end else None
                        
                        if c_start and c_end:
                            # If rule specifies both start and end
                            if r_start and r_end:
                                if c_start < r_end and r_start < c_end:
                                    time_overlap = True
                            # If rule specifies only start (after this time)
                            elif r_start:
                                if c_end > r_start:
                                    time_overlap = True
                            # If rule specifies only end (before this time)
                            elif r_end:
                                if c_start < r_end:
                                    time_overlap = True
                            # If rule specifies no time but specifies Day
                            else:
                                time_overlap = True
                                
                    if not time_overlap:
                        continue # Rule time condition didn't match any class
                        
                # If the code reaches here, the bundle perfectly matches the block rule!
                is_blocked = True
                break
                
            if not is_blocked:
                final_groups_list.append(g_bundle)
                
        # If the blacklist was too aggressive, it's the student's fault, but we'll try to generate anyway if empty
        if not final_groups_list:
            final_groups_list = strict_groups_list
            
        subjects_data[subj] = final_groups_list
        
    result = generate_combinations(
        subjects_data, 
        no_night=no_night, 
        no_morning=no_morning, 
        free_day=free_day,
        preferred_group=preferred_group,
        student_course=student_course
    )
    
    return jsonify({
        'valid_combinations': result.get('combinations', []),
        'perfect_match': result.get('perfect_match', False)
    })

@bp.route('/api/timetable/save', methods=['POST'])
def save_timetable():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    timetable_data = data.get('timetable_data')
    
    if not timetable_data:
        return jsonify({'error': 'No timetable data provided'}), 400
        
    import json
    saved = SavedTimetable(
        user_id=session['user_id'],
        data=json.dumps(timetable_data)
    )
    db.session.add(saved)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Timetable saved successfully!'})

@bp.route('/api/timetable/saved', methods=['GET'])
def get_saved_timetables():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    saved = SavedTimetable.query.filter_by(user_id=session['user_id']).order_by(SavedTimetable.created_at.desc()).all()
    return jsonify({'data': [s.to_dict() for s in saved]})

@bp.route('/api/timetable/set_primary', methods=['POST'])
@login_required(role='student')
def set_primary_timetable():
    data = request.json
    timetable_id = data.get('id')
    
    if not timetable_id:
        return jsonify({'error': 'Timetable ID is required'}), 400
        
    # Verify the timetable belongs to the user
    timetable = SavedTimetable.query.filter_by(id=timetable_id, user_id=session['user_id']).first()
    if not timetable:
        return jsonify({'error': 'Timetable not found or unauthorized'}), 404
        
    # Reset all others to false
    SavedTimetable.query.filter_by(user_id=session['user_id']).update({'is_primary': False})
    
    # Set this one to true
    timetable.is_primary = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Primary timetable updated'})

@bp.route('/api/timetable/saved/<int:id>', methods=['DELETE'])
def delete_saved_timetable(id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    saved = SavedTimetable.query.filter_by(id=id, user_id=session['user_id']).first()
    if not saved:
        return jsonify({'error': 'Saved timetable not found'}), 404
        
    db.session.delete(saved)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Saved timetable deleted!'})

@bp.route('/api/student/lecturer_email', methods=['GET'])
@login_required()
def get_lecturer_email():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'email': ''})
    
    lecturers = LecturerProfile.query.all()
    if not lecturers:
        return jsonify({'email': ''})
        
    names = [l.name for l in lecturers]
    best_match = process.extractOne(name, names)
    
    if best_match and best_match[1] >= 80:
        matched_lecturer = next((l for l in lecturers if l.name == best_match[0]), None)
        if matched_lecturer:
            return jsonify({'email': matched_lecturer.email or ''})
            
    return jsonify({'email': ''})

# ---------------------------------------------------------
# PROFILE & SETTINGS
# ---------------------------------------------------------

@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Check if updating profile picture
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                filename = secure_filename(f"user_{user.id}_{file.filename}")
                filepath = os.path.join(current_app.root_path, 'static', 'uploads', 'profile_pics', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                user.profile_pic = filename
                db.session.commit()
                flash('Profile picture updated successfully!', 'success')
                return redirect(url_for('main.profile'))
                
        # Handle regular profile updates
        user.name = request.form.get('name', user.name)
        if user.role == 'student':
            user.course = request.form.get('course', user.course)
            user.year = request.form.get('year', user.year)
            user.group_name = request.form.get('group_name', user.group_name)
            
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile'))
        
    return render_template('profile.html', current_user=user)

# ---------------------------------------------------------
# PASSWORD RESET (FORGOT PASSWORD)
# ---------------------------------------------------------

def send_reset_email(user):
    from app import mail
    token = get_reset_token(user)
    msg = Message('Password Reset Request',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[user.email])
    
    reset_link = url_for('main.reset_token', token=token, _external=True)
    msg.body = f'''To reset your password, visit the following link:
{reset_link}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
    return True

def get_reset_token(user, expires_sec=1800):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'user_id': user.id}, salt='password-reset-salt')

def verify_reset_token(token):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token, salt='password-reset-salt', max_age=1800)
    except:
        return None
    return User.query.get(data['user_id'])

@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if 'user_id' in session:
        return redirect(url_for('main.student_ui'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            if send_reset_email(user):
                flash('An email has been sent with instructions to reset your password.', 'info')
                return redirect(url_for('main.login'))
            else:
                flash('Failed to send email. Please ensure email server is configured properly.', 'danger')
        else:
            flash('There is no account with that email. You must register first.', 'warning')
            
    return render_template('forgot_password.html')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if 'user_id' in session:
        return redirect(url_for('main.student_ui'))
        
    user = verify_reset_token(token)
    if not user:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('main.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('main.reset_token', token=token))
            
        user.set_password(password)
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('reset_password.html')

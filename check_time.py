from app import create_app
from models import db, SavedTimetable
import json

app = create_app()
with app.app_context():
    st = SavedTimetable.query.first()
    if st:
        data = json.loads(st.data)
        if len(data) > 0 and 'classes' in data[0] and len(data[0]['classes']) > 0:
            cls = data[0]['classes'][0]
            print("Start time:", cls.get('start_time'))
            print("Class type:", cls.get('class_type'))
        else:
            print("No classes in first bundle")
    else:
        print("No saved timetables.")

from app import create_app
from models import db, SavedTimetable
import json

app = create_app()
with app.app_context():
    st = SavedTimetable.query.first()
    if st:
        data = json.loads(st.data)
        if len(data) > 0:
            print(data[0].keys())
            print(data[0].get('group_name'))
            print(data[0].get('subject_code', data[0]['classes'][0].get('subject_code')))
    else:
        print("No saved timetables.")

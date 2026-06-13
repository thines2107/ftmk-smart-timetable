import pdfplumber
import pandas as pd
import re

def extract_timetable_from_pdf(filepath, progress_dict=None, task_id=None, semester_name="Unknown Semester"):
    """
    Extracts tabular data from the uploaded FTMK UTeM timetable PDF.
    This logic depends heavily on the grid structure of the PDF.
    """
    extracted_data = []

    # Map column index to time blocks based on standard UTeM format 
    # (starts at 8 AM, goes till 11 PM)
    time_blocks = [
        "08:00:00", "09:00:00", "10:00:00", "11:00:00", "12:00:00", 
        "13:00:00", "14:00:00", "15:00:00", "16:00:00", "17:00:00", 
        "18:00:00", "19:00:00", "20:00:00", "21:00:00", "22:00:00", "23:00:00"
    ]

    subject_mapping = {}

    with pdfplumber.open(filepath) as pdf:
        total_pages = len(pdf.pages)
        current_course_code = "UNKNOWN"
        current_group_name = "UNKNOWN"
        for i, page in enumerate(pdf.pages):
            if progress_dict is not None and task_id is not None:
                percent = int((i / total_pages) * 100)
                progress_dict[task_id] = {
                    'percent': percent, 
                    'message': f'Processing Page {i+1} of {total_pages}',
                    'status': 'processing'
                }
            
            # Extract course and group from page text header
            page_text = page.extract_text()
            if page_text:
                for line in page_text.split('\n'):
                    # Aggressively clean standard UTeM headers and floating timetable artifacts
                    clean_line = re.sub(r'(?i).*?JADUAL WAKTU.*?\d{4}/\d{4}', '', line)
                    clean_line = re.sub(r'(?i).*?SESI \d{4}/\d{4}', '', clean_line)
                    clean_line = re.sub(r'\b\d{1,2}:\d{2}\b', '', clean_line) # strip times like 08:00
                    clean_line = re.sub(r'^\s*20\d{2}\s+', '', clean_line) # strip chunked years like 2026
                    clean_line = re.sub(r'\b08\b|\b09\b', '', clean_line) # strip grid boundary numbers
                    clean_line = clean_line.strip()
                    
                    match = re.search(r'^([A-Za-z0-9\-\(\)&\.\s]+?)\s+(S\d+(?:G\d+)?(?:(?:-|_)[A-Za-z0-9]+)?)\b', clean_line)
                    if match:
                        current_course_code = match.group(1).strip()
                        current_group_name = match.group(2).replace(" ", "")
                        break
                        
                    # Fallback for standalone headers that completely lack a Group ID (e.g. "FEEDER DCS BITM")
                    # We check if it strictly has uppercase words and contains known FTMK acronyms
                    match_fallback = re.search(r'^([A-Z0-9\-\(\)&\.\s]{5,})$', clean_line)
                    if match_fallback:
                        pot_course = match_fallback.group(1).strip()
                        # Reject plain English or layout artifacts, accept specifically if it looks like a UTeM course
                        if not re.search(r'[a-z]', pot_course) and any(x in pot_course for x in ['BIT', 'DCS', 'FEEDER', 'DIP']):
                            current_course_code = pot_course
                            current_group_name = "UNKNOWN GROUP"
                            break
                            
            tables = page.extract_tables()
            if not tables:
                continue
                
            # Usually, the timetable grid is the first large table.
            # Below it, there is a "Course Summary" table mapping codes to names.
            # We iterate over tables to isolate them based on headers.
            for table in tables:
                if len(table) < 2:
                    continue
                    
                header = [str(x).strip().lower() if x else '' for x in table[0]]
                
                # Check if it's the Summary Table (e.g. ['no.', 'subjects'])
                is_summary = ('subjects' in header or 'no.' in header)
                is_timetable = ('day' in header)
                
                if not is_summary and not is_timetable:
                    # Check if it's a headerless continuation table
                    for r in table[:3]:
                        if r and r[0] and str(r[0]).strip().capitalize() in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                            is_timetable = True
                            break

                if is_summary:
                    for row in table[1:]:
                        if row and len(row) >= 2 and row[1]:
                            text = str(row[1]).strip()
                            # Extracts e.g., "BITS 1323 SUBJECT NAME" into BITS1323
                            match = re.search(r'^([A-Z]+)\s*(\d+)\s+(.+)', text)
                            if match:
                                sub_code = match.group(1) + match.group(2)
                                subject_mapping[sub_code] = match.group(3)

                # Check if it's the Main Timetable Table
                elif is_timetable:
                    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    
                    # If it's a continuation table without a header, don't skip the first row
                    start_idx = 1 if 'day' in header else 0
                    
                    for row in table[start_idx:]: 
                        if not row or not row[0]:
                            continue
                        day = str(row[0]).strip().capitalize()
                        if day not in days_of_week:
                            continue
                            
                        # Iterate through cells corresponding to time columns
                        # The start of the time grid is usually index 1
                        time_idx = 1
                        while time_idx < len(row) and time_idx - 1 < len(time_blocks):
                            cell_text = row[time_idx]
                            
                            if cell_text and cell_text.strip() and cell_text.strip().lower() not in ['break', 'ko-kurikulum']:
                                cell_lines = cell_text.strip().split('\n')
                                if len(cell_lines) >= 3:
                                    subject_code = cell_lines[0].strip().replace(" ", "")
                                    class_type_raw = cell_lines[1].strip() # "LAB - HUAWEI"
                                    lecturer = cell_lines[2].strip() if len(cell_lines) > 2 else ""
                                    
                                    class_type = "LEC" if "LEC" in class_type_raw.upper() else "LAB" if "LAB" in class_type_raw.upper() else "OTHER"
                                    room = class_type_raw.split('-')[-1].strip() if '-' in class_type_raw else class_type_raw
                                    
                                    # Determine how many columns this class spans by checking adjacent empty/None cells
                                    span = 1
                                    while time_idx + span < len(row) and row[time_idx + span] is None:
                                        span += 1
                                        
                                    start_time = time_blocks[time_idx - 1]
                                    end_time = time_blocks[time_idx - 1 + span] if time_idx - 1 + span < len(time_blocks) else "23:59:00"

                                    extracted_data.append({
                                        'course_code': current_course_code,
                                        'group_name': current_group_name,
                                        'semester_name': semester_name,
                                        'subject_code': subject_code,
                                        'class_type': class_type,
                                        'day': day,
                                        'start_time': start_time,
                                        'end_time': end_time,
                                        'room': room,
                                        'lecturer_name': lecturer
                                    })
                                    time_idx += span - 1 # Skip spanned columns
                            time_idx += 1

    # Attach subject_name from mapping
    for data in extracted_data:
        data['subject_name'] = subject_mapping.get(data['subject_code'], 'Unknown Subject Name')

    return extracted_data

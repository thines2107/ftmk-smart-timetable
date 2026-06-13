import itertools

def check_clash(class1, class2):
    """
    Checks if two class dictionary objects clash in schedule.
    clash if (start1 < end2 AND start2 < end1) on the same day.
    """
    if class1['day'] == class2['day']:
        if class1['start_mins'] < class2['end_mins'] and class2['start_mins'] < class1['end_mins']:
            return True
    return False

def generate_combinations(subjects_data, no_night=False, no_morning=False, free_day='', preferred_group='', student_course=''):
    """
    subjects_data is a dictionary where the key is the subject_code and the value 
    is a list of all distinct group bundles (Lectures and Labs) for that subject.
    """
    combinatorial_list = []
    
    night_limit_mins = 20 * 60  # 20:00 (8 PM)
    morning_limit_mins = 10 * 60  # 10:00 AM
    
    if preferred_group:
        preferred_group = preferred_group.upper()
    
    for subject_code, groups_list in subjects_data.items():
        groups_list.sort(key=lambda x: (
            0 if preferred_group and preferred_group in x.get('group_name', '').upper() else 1,
            0 if student_course and student_course == x.get('course_code', '') else 1
        ))
            
        valid_groups = []
        for group_bundle in groups_list:
            violates = False
            if 'classes' in group_bundle:
                for c in group_bundle['classes']:
                    if c['day'] == free_day: violates = True
                    
                    # Pre-calculate integer minutes for 50x speedup in combinatorial loops
                    if 'start_mins' not in c:
                        hh_s, mm_s = c['start_time'].split(':')[:2]
                        c['start_mins'] = int(hh_s) * 60 + int(mm_s)
                        
                        hh_e, mm_e = c['end_time'].split(':')[:2]
                        c['end_mins'] = int(hh_e) * 60 + int(mm_e)
                        
                    if no_night and (c['start_mins'] >= night_limit_mins or c['end_mins'] > night_limit_mins): violates = True
                    if no_morning and (c['start_mins'] < morning_limit_mins): violates = True
            if not violates:
                valid_groups.append(group_bundle)
                
        # Strictly enforce preferences. If a subject has NO valid groups, 
        # combinatorial_list gets an empty list, and 0 results are returned.
        combinatorial_list.append(valid_groups)
            
    combo_generator = itertools.product(*combinatorial_list)
    
    valid_timetables = []
    
    combinations_checked = 0
    MAX_CHECKS = 500000  # With integer math, 500k takes less than 0.2 seconds!
    MAX_RESULTS = 200    
    
    for combo in combo_generator:
        combinations_checked += 1
        if combinations_checked > MAX_CHECKS:
            break
            
        flat_classes = []
        for group_bundle in combo:
            if 'classes' in group_bundle:
                flat_classes.extend(group_bundle['classes'])
                
        has_clash = False
        for i in range(len(flat_classes)):
            for j in range(i+1, len(flat_classes)):
                if check_clash(flat_classes[i], flat_classes[j]):
                    has_clash = True
                    break
            if has_clash:
                break
                
        if has_clash:
            continue
            
        day_map = {}
        for c in flat_classes:
            d = c['day']
            if d not in day_map:
                day_map[d] = []
            day_map[d].append(c)
            
        total_gap_minutes = 0
        for d, classes in day_map.items():
            classes.sort(key=lambda x: x['start_mins'])
            for i in range(len(classes) - 1):
                gap = classes[i+1]['start_mins'] - classes[i]['end_mins']
                if gap > 0:
                    total_gap_minutes += gap
                    
        valid_timetables.append({
            'combo': combo,
            'gap_score': total_gap_minutes
        })
        
        if len(valid_timetables) >= MAX_RESULTS:
            break
            
    if preferred_group:
        for vt in valid_timetables:
            non_preferred_count = 0
            for bundle in vt['combo']:
                g_name = bundle.get('group_name', '').upper()
                if preferred_group not in g_name:
                    non_preferred_count += 1
            vt['gap_score'] += (non_preferred_count * 100000)
            vt['non_preferred_count'] = non_preferred_count
        
    valid_timetables.sort(key=lambda x: x['gap_score'])
            
    perfect_match = False
    if valid_timetables and preferred_group:
        if valid_timetables[0].get('non_preferred_count', 0) == 0:
            perfect_match = True
    elif not preferred_group:
        perfect_match = True
            
    return {
        'combinations': [t['combo'] for t in valid_timetables[:15]],
        'perfect_match': perfect_match
    }

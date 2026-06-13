import itertools
from datetime import datetime

def check_clash(class1, class2):
    """
    Checks if two class dictionary objects clash in schedule.
    clash if (start1 < end2 AND start2 < end1) on the same day.
    """
    if class1['day'] == class2['day']:
        fmt = '%H:%M'
        start1 = datetime.strptime(class1['start_time'], fmt)
        end1 = datetime.strptime(class1['end_time'], fmt)
        start2 = datetime.strptime(class2['start_time'], fmt)
        end2 = datetime.strptime(class2['end_time'], fmt)
        
        if start1 < end2 and start2 < end1:
            return True
    return False

def generate_combinations(subjects_data, no_night=False, no_morning=False, free_day='', preferred_group=''):
    """
    subjects_data is a dictionary where the key is the subject_code and the value 
    is a list of all distinct group bundles (Lectures and Labs) for that subject.
    """
    combinatorial_list = []
    
    fmt = '%H:%M'
    night_limit = datetime.strptime('20:00', fmt)
    morning_limit = datetime.strptime('10:00', fmt)
    
    if preferred_group:
        preferred_group = preferred_group.upper()
    
    for subject_code, groups_list in subjects_data.items():
        # Optimization 1: Sort by preferred group so itertools checks them first
        if preferred_group:
            groups_list.sort(key=lambda x: 0 if preferred_group in x.get('group_name', '').upper() else 1)
            
        # Optimization 2: Pre-filter groups that violate hard preferences
        valid_groups = []
        for group_bundle in groups_list:
            violates = False
            if 'classes' in group_bundle:
                for c in group_bundle['classes']:
                    if c['day'] == free_day: violates = True
                    start_dt = datetime.strptime(c['start_time'], fmt)
                    end_dt = datetime.strptime(c['end_time'], fmt)
                    if no_night and (start_dt >= night_limit or end_dt > night_limit): violates = True
                    if no_morning and (start_dt < morning_limit): violates = True
            if not violates:
                valid_groups.append(group_bundle)
                
        # Fallback to all groups if strict preferences filter out everything for a subject
        if valid_groups:
            combinatorial_list.append(valid_groups)
        else:
            combinatorial_list.append(groups_list)
            
    # Optimization 3: Use a generator, DO NOT cast to list!
    combo_generator = itertools.product(*combinatorial_list)
    
    valid_timetables = []
    
    combinations_checked = 0
    MAX_CHECKS = 100000  # Strict CPU timeout prevention
    MAX_RESULTS = 200    # Stop early if we have enough valid timetables
    
    for combo in combo_generator:
        combinations_checked += 1
        if combinations_checked > MAX_CHECKS:
            break
            
        flat_classes = []
        for group_bundle in combo:
            if 'classes' in group_bundle:
                flat_classes.extend(group_bundle['classes'])
                
        # Check all pairs for time clashes
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
            
        # Gap Score Calculation (Optimization)
        day_map = {}
        for c in flat_classes:
            d = c['day']
            if d not in day_map:
                day_map[d] = []
            day_map[d].append(c)
            
        total_gap_minutes = 0
        for d, classes in day_map.items():
            classes.sort(key=lambda x: datetime.strptime(x['start_time'], fmt))
            for i in range(len(classes) - 1):
                c1_end = datetime.strptime(classes[i]['end_time'], fmt)
                c2_start = datetime.strptime(classes[i+1]['start_time'], fmt)
                gap = (c2_start - c1_end).total_seconds() / 60.0
                if gap > 0:
                    total_gap_minutes += gap
                    
        valid_timetables.append({
            'combo': combo,
            'gap_score': total_gap_minutes
        })
        
        if len(valid_timetables) >= MAX_RESULTS:
            break
            
    # Priority Group Scoring Bonus
    if preferred_group:
        for vt in valid_timetables:
            non_preferred_count = 0
            for bundle in vt['combo']:
                g_name = bundle.get('group_name', '').upper()
                if preferred_group not in g_name:
                    non_preferred_count += 1
            vt['gap_score'] += (non_preferred_count * 100000)
            vt['non_preferred_count'] = non_preferred_count
        
    # Sort valid timetables so the lowest gap score comes first
    valid_timetables.sort(key=lambda x: x['gap_score'])
            
    # Determine if the top option is a perfect match
    perfect_match = False
    if valid_timetables and preferred_group:
        if valid_timetables[0].get('non_preferred_count', 0) == 0:
            perfect_match = True
    elif not preferred_group:
        perfect_match = True
            
    # Extract just the combinations from the sorted list
    # Only return the top 15 to save network bandwidth and browser rendering memory
    return {
        'combinations': [t['combo'] for t in valid_timetables[:15]],
        'perfect_match': perfect_match
    }

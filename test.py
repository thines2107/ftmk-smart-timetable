import re
test_cases = [
    "FEEDER DCS BITM S3-DE",
    "FEEDER DCS BITM S3G1",
    "FEEDER DCS BITM S3 G1",
    "FEEDER DCS BITM",
    "1 BITA S1G1",
    "1 BITA",
    "A random line with lowercase",
    "08:00 09:00",
    "MONDAY",
    "SUBJECT NO"
]

for clean_line in test_cases:
    match = re.search(r"^([A-Z0-9\-\(\)&\.\s]{5,}?)(?:\s+(S\d+(?:G\d+)?(?:(?:-|_)[A-Za-z0-9]+)?))?$", clean_line)
    
    if match:
        course = match.group(1).strip()
        group = match.group(2) if match.group(2) else "UNKNOWN GROUP"
        
        # Only accept if course name has letters, isnt just times, and seems legit
        # We can dynamically check uppercase ratio and length
        if re.search(r"[A-Z]", course) and not re.search(r"[a-z]", course):
            print(f"MATCH: {clean_line} -> Course: {course} | Group: {group}")
        else:
            print(f"FAIL: {clean_line}")
    else:
        print(f"FAIL: {clean_line}")

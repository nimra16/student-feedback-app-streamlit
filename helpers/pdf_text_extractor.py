import pandas as pd
from PyPDF2 import PdfReader

def extract_feedback_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

    rows = []
    faculty_name = None
    course_name = None
    class_name = None
    capture_comments = False
    
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith("teacher name:"):
            faculty_name = line.split(":")[1].strip()
        elif line.lower().startswith("course title::"):
            course_name = line.split(":")[1].strip()
        elif line.lower().startswith("class:"):
            class_name = line.split(":")[1].strip()
        elif "comments for teacher and course" in line.lower():     
            print(line)
            capture_comments = True 
            continue  # Skip header line itself

        elif any(word in line.lower() for word in ["for teacher", "for course"]):  # Assuming these are feedback lines
            target = "Teacher" if "for teacher" in line.lower() else "Course"
            comment = line.lower().split("for teacher")
            # print(len(comment), comment)
            rows.append({
                "FacultyName": faculty_name,
                "Course": course_name,
                "Comments": line,
                "Target": target,
                "Class": class_name
            })

    return pd.DataFrame(rows)

import pandas as pd
from PyPDF2 import PdfReader
import os
def extract_feedback_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    lines = text.splitlines()
    i =0 
    rows = []
    faculty_name = os.path.splitext(pdf_file.name)[0]
    course_name = None
    class_name = None
    term = None
    
    
    for i in range(0,len(lines)):
        line = lines[i].strip()
        # print(line + "\n")
        if not line:
            continue
        elif ("comments report") in line.lower():
            print(lines[i+1] + "\n\n" + lines[i+2] + "\n\n")
            line  = lines[i+1].strip()
            if "class:" in line.lower():
                class_name = line.lower().split("class:")[1].strip()
            if "term:" in line.lower():                
                term = line.lower().split("term:")[1].strip()
                term  = term.lower().split("class")[0].strip()
            course_name = lines[i+2]
            lines = lines[i+2:]
            break

    for line in lines:   
        if "comments for teacher and course" in line.lower():
            continue                       
        elif any(word in line.lower() for word in ["for teacher", "for course"]):
            # Assuming these are feedback lines
            target = "Teacher" if "for teacher" in line.lower() else "Course"
            comment = line.lower().split("for teacher")[1].strip() if "for teacher" in line.lower() else line.lower().split("for course")[1].strip()
            # print(len(comment), comment)
            rows.append({
                "FacultyName": faculty_name if faculty_name else "Unknown",
                "Course": course_name if course_name else "Unknown",
                "Comments": comment,
                "Target": target,
                "Class": class_name if class_name else "Unknown",   
                "Semester": term if term else "Unknown",
            })

    return pd.DataFrame(rows)

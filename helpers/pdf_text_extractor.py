import pandas as pd
from PyPDF2 import PdfReader
import os
def extract_feedback_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    lines = text.splitlines()

    blocks = []
    rows = []
    faculty_name = os.path.splitext(pdf_file.name)[0]

    # Step 1: Identify start indices of each course block
    for i in range(len(lines) - 2):
        if not lines[i].strip():
            continue
        elif "comments report" in lines[i].lower() and "term:" in lines[i+1].lower():
            blocks.append(i)

    # Step 2: Process each block
    for b in range(len(blocks)):
        i = blocks[b]
        next_i = blocks[b + 1] if b + 1 < len(blocks) else len(lines)

        course_name = lines[i+2].strip()
        class_line = lines[i+1].strip().lower()
        
        # Extract term and class
        class_name = None
        term = None
        if "class:" in class_line:
            class_name = class_line.split("class:")[1].strip()
        if "term:" in class_line:
            term = class_line.split("term:")[1].split("class")[0].strip()

        # Step 3: Process comments in this block
        for line in lines[i+3:next_i]:
            line = line.strip()
            if not line or "comments for teacher and course" in line.lower():
                continue
            elif any(word in line.lower() for word in ["for teacher", "for course"]):
                target = "Teacher" if "for teacher" in line.lower() else "Course"
                comment = line.lower().split("for teacher")[1].strip() if "for teacher" in line.lower() else line.lower().split("for course")[1].strip()
                rows.append({
                    "FacultyName": faculty_name if faculty_name else "Unknown",
                    "Course": course_name if course_name else "Unknown",
                    "Comments": comment,
                    "Target": target,
                    "Class": class_name if class_name else "Unknown",   
                    "Semester": term if term else "Unknown",
                })
    return pd.DataFrame(rows)

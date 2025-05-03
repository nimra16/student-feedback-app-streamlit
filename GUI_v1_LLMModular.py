import pandas as pd
import streamlit as st
import os
import warnings
from helpers.pdf_text_extractor import extract_feedback_from_pdf
from helpers.processFeedbak import process_and_display_feedback
warnings.filterwarnings("ignore")

# =========================================
# Utility Functions
# =========================================


# =========================================
# Streamlit UI Starts
# =========================================

st.set_page_config(layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1rem; padding-bottom: 1rem; }
  .center-title { text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='center-title'>Teacher Feedback Analysis Dashboard</h1>", unsafe_allow_html=True)

columns = ['FacultyName', 'Course', 'Comments', 'Target', 'Class']
columns_str = ", ".join(f"**{col}**" for col in columns)
aspect_categories = ["Teaching Pedagogy", "Knowledge", "Fair in Assessment", "Experience", "Behavior"]

input_mode = st.radio("Select Input Mode", ["Multiple Teachers (CSV/XLSX)", "Individual Teacher (PDF)"])

if input_mode == "Multiple Teachers (CSV/XLSX)":
    st.markdown(f"\n 📁 Upload **CSV or Excel** file with columns: {columns_str}")
    uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"], label_visibility="collapsed")

    if uploaded_file:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df = df[df['Target'].str.contains('Teacher', case=False, na=False)]

        semester_name = os.path.splitext(uploaded_file.name)[0]
        teachers = sorted(df['FacultyName'].dropna().unique())

        selected_teacher = st.sidebar.selectbox("Select a Teacher", teachers)
        if selected_teacher:
            process_and_display_feedback(df, selected_teacher, semester_name)

elif input_mode == "Individual Teacher (PDF)":
    pdf_file = st.file_uploader("Upload PDF", type="pdf")
    if pdf_file:
        with st.spinner("Extracting feedback from PDF..."):
            df = extract_feedback_from_pdf(pdf_file)

        if not df.empty:
            teacher_dfRaw = df[df['Target'].str.contains('Teacher', case=False, na=False)]
            selected_teacher = teacher_dfRaw['FacultyName'].iloc[0]                    
            selected_course = teacher_dfRaw['Course'].iloc[0]
            selected_class = teacher_dfRaw['Class'].iloc[0]
            semester_name = teacher_dfRaw['Semester'].iloc[0] if 'Semester' in teacher_dfRaw.columns else "Individual Teacher"

            st.sidebar.markdown(f"**Teacher:** {selected_teacher}")
            st.sidebar.markdown(f"**Course:** {selected_course}")
            st.sidebar.markdown(f"**Class:** {selected_class}")
            st.sidebar.markdown(f"**Semester:** {semester_name}")

            process_and_display_feedback(teacher_dfRaw, selected_teacher, semester_name)

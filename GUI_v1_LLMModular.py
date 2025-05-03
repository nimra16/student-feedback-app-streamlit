import pandas as pd
import streamlit as st
import os
import tempfile
from helpers.llm_processor import process_teacher_feedback_with_llm
from helpers.llm_processor_ollama import process_teacher_feedback_with_llm

from helpers.graph_generator import generate_bar_chart, generate_wordcloud
from helpers.pdf_generator import PDF
from helpers.pdf_text_extractor import extract_feedback_from_pdf  # Your custom extractor

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

input_mode = st.radio("Select Input Mode", ["Multiple Teachers (CSV/XLSX)", "Single Teacher (PDF)"])

columns = ['FacultyName', 'Course', 'Comments', 'Target', 'Class']
columns_str = ", ".join(f"**{col}**" for col in columns)

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
            processed_file_path = f"Datasets/{semester_name}/{selected_teacher}_processed_feedback.csv"

            if os.path.exists(processed_file_path):
                teacher_df = pd.read_csv(processed_file_path)
            else:
                st.info("Processing feedback with LLM... Please wait ⌛")
                teacher_df = process_teacher_feedback_with_llm(df, selected_teacher, semester_name)
                st.success("Processing complete ✅")

            aspect_categories = ["Teaching Pedagogy", "Knowledge", "Fair in Assessment", "Experience", "Behavior"]
            selected_course = st.sidebar.selectbox("Select a Course (Optional)", ['All'] + sorted(teacher_df['Course'].unique()))
            selected_class = "All"

            selected_aspects = st.sidebar.multiselect("Select Aspects to Include in Report", options=aspect_categories, default=aspect_categories)

            if selected_course != 'All':
                class_options = sorted(teacher_df[teacher_df['Course'] == selected_course]['Class'].astype(str).unique())
                selected_class = st.sidebar.selectbox("Select a Class (Optional)", ['All'] + class_options)

                if selected_class != 'All':
                    teacher_df = teacher_df[(teacher_df['Course'] == selected_course) & (teacher_df['Class'].astype(str) == selected_class)]
                    st.markdown(f"### Feedback Report for {selected_teacher} | **Course: {selected_course} | Class: {selected_class}**")
                else:
                    teacher_df = teacher_df[teacher_df['Course'] == selected_course]
                    st.markdown(f"### Feedback Report for {selected_teacher} | **Course: {selected_course}**")
            else:
                st.markdown(f"### Overall Feedback Report for {selected_teacher}")

elif input_mode == "Single Teacher (PDF)":
    pdf_file = st.file_uploader("Upload PDF", type="pdf")
    if pdf_file:
        with st.spinner("Extracting feedback from PDF..."):
            df = extract_feedback_from_pdf(pdf_file)

        if not df.empty:
            teacher_df = df[df['Target'].str.contains('Teacher', case=False, na=False)]
            selected_teacher = teacher_df['FacultyName'].iloc[0]
            selected_course = teacher_df['Course'].iloc[0]
            selected_class = teacher_df['Class'].iloc[0]
            semester_name = "SingleTeacher"

            st.sidebar.markdown(f"**Teacher:** {selected_teacher}")
            st.sidebar.markdown(f"**Course:** {selected_course}")
            st.sidebar.markdown(f"**Class:** {selected_class}")

            processed_file_path = f"Datasets/{semester_name}/{selected_teacher}_processed_feedback.csv"

            if os.path.exists(processed_file_path):
                teacher_df = pd.read_csv(processed_file_path)
            else:
                st.info("Processing feedback with LLM... Please wait ⌛")
                teacher_df = process_teacher_feedback_with_llm(df, selected_teacher, semester_name)
                st.success("Processing complete ✅")

            aspect_categories = ["Teaching Pedagogy", "Knowledge", "Fair in Assessment", "Experience", "Behavior"]
            selected_aspects = st.sidebar.multiselect("Select Aspects to Include in Report", options=aspect_categories, default=aspect_categories)

            st.markdown(f"### Feedback Report for {selected_teacher} | **Course: {selected_course} | Class: {selected_class}**")

else:
    teacher_df = None

# ============ COMMON TO BOTH PATHS ============
if 'teacher_df' in locals() and teacher_df is not None and not teacher_df.empty:
    # Generate bar chart
    bar_graph_path = generate_bar_chart(teacher_df, selected_aspects)

    # Generate word clouds
    wordcloud_images = generate_wordcloud(teacher_df, selected_aspects)

    wordcloud_paths = []
    for aspect, wc_img in wordcloud_images:
        img_path = os.path.join(tempfile.gettempdir(), f"{aspect}_wordcloud.png")
        wc_img.to_file(img_path)
        wordcloud_paths.append((aspect, img_path))

    pdf = PDF()
    pdf.add_page()
    pdf.add_teacher_info(selected_teacher, selected_course, selected_class)
    total_respondents = teacher_df['Comments'].dropna().count()
    pdf.add_respondents_info(total_respondents)
    pdf.add_bar_chart_image(bar_graph_path)

    for aspect, path in wordcloud_paths:
        aspect_df = teacher_df[
            teacher_df[f"{aspect}_terms"].fillna("").str.strip().pipe(lambda s: (s != "") & (s.str.lower() != "none"))
        ]
        discussed_count = len(aspect_df)
        pdf.add_aspect_info(aspect, discussed_count, total_respondents, path, aspect_df)

    os.makedirs(f"Reports/{semester_name}", exist_ok=True)

    def sanitize_filename(s):
        import re
        return re.sub(r'[<>:"/\\|?*\s]+', '_', s)

    safe_teacher = sanitize_filename(selected_teacher)
    safe_course = sanitize_filename(selected_course)
    safe_class = sanitize_filename(selected_class)

    pdf_path = os.path.join("Reports", semester_name, f"{safe_teacher}_{safe_course}_{safe_class}.pdf")

    try:
        pdf.output(pdf_path, dest='F')
        st.success(f"PDF report saved to: {pdf_path}")
    except Exception as e:
        st.error(f"Failed to save PDF report: {e}")

    with open(pdf_path, "rb") as f:
        st.download_button(
            label="Download Full Feedback Report (PDF)",
            data=f,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf"
        )

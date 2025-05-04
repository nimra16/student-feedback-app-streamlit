import os
import tempfile
from helpers.llm_processor import process_teacher_feedback_with_llm
from helpers.graph_generator import generate_bar_chart, generate_wordcloud
from helpers.pdf_generator import PDF
import streamlit as st
import pandas as pd
def sanitize_filename(s):
    import re
    return re.sub(r'[<>:"/\\|?*\s]+', '_', s)

def generate_absa_report(teacher_df, selected_teacher, selected_course, selected_class, selected_aspects, semester_name):
    bar_graph_path = generate_bar_chart(teacher_df, selected_aspects)
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

    os.makedirs("Reports/" + semester_name, exist_ok=True)
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
        st.download_button("Download Full Feedback Report (PDF)", f, os.path.basename(pdf_path), mime="application/pdf")

def process_and_display_feedback(df, selected_teacher, semester_name,):
    processed_file_path = f"Datasets/{semester_name}/{selected_teacher}_processed_feedback.csv"
    if os.path.exists(processed_file_path):
        teacher_df = pd.read_csv(processed_file_path)
    else:
        st.info("Processing feedback with LLM... Please wait ⌛")
        teacher_dfRaw = df[df['FacultyName'] == selected_teacher].copy()
        teacher_df = process_teacher_feedback_with_llm(teacher_dfRaw, selected_teacher, semester_name)
        st.success("Processing complete ✅")

    aspect_categories = ["Teaching Pedagogy", "Knowledge", "Fair in Assessment", "Experience", "Behavior"]

    selected_aspects = st.sidebar.multiselect("Select Aspects to Include in Report", options=aspect_categories, default=aspect_categories)

    selected_course = st.sidebar.selectbox("Select a Course (Optional)", ['All'] + sorted(teacher_df['Course'].unique()))
    selected_class = "All"

    if selected_course != 'All':
        class_options = sorted(teacher_df[teacher_df['Course'] == selected_course]['Class'].astype(str).unique())
        selected_class = st.sidebar.selectbox("Select a Class (Optional)", ['All'] + class_options)

        if selected_class != 'All':
            teacher_df = teacher_df[(teacher_df['Course'] == selected_course) & (teacher_df['Class'].astype(str) == selected_class)]
            st.markdown(f"### Feedback Report for {selected_teacher} | **Course: {selected_course} | Class: {selected_class}** | **Semester: {semester_name}**")
        else:
            teacher_df = teacher_df[teacher_df['Course'] == selected_course]
            st.markdown(f"### Feedback Report for {selected_teacher} | **Course: {selected_course}** | **Semester: {semester_name}**")
    else:
        st.markdown(f"### Feedback Report for {selected_teacher} | **Semester: {semester_name}**")  

    generate_absa_report(teacher_df, selected_teacher, selected_course, selected_class, selected_aspects, semester_name)

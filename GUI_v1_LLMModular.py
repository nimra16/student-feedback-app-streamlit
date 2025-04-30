import pandas as pd
import streamlit as st
import os
import tempfile
from helpers.llm_processor import process_teacher_feedback_with_llm
from helpers.graph_generator import generate_bar_chart, generate_wordcloud
from helpers.pdf_generator import PDF

# =========================================
# Streamlit UI Starts
# =========================================

st.set_page_config(layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1rem; padding-bottom: 1rem; }
  .center-title { text-align: center; }
  .wordcloud-title { text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='center-title'>Teacher Feedback Analysis Dashboard</h1>", unsafe_allow_html=True)

# File uploader widget that allows both CSV and Excel files
import streamlit as st

columns = ['FacultyName', 'Course', 'Comments', 'Target', 'Class']

# Display custom instruction above the uploader
columns_str = ", ".join(f"**{col}**" for col in columns)  # Bold but inline

# Custom message with tight formatting
st.markdown(f"""
 📁 Upload **CSV or Excel** file that contains at least the following columns: {columns_str}
""")

# File uploader with default label hidden
uploaded_file = st.file_uploader(
    label="Upload file", 
    type=["csv", "xlsx"], 
    label_visibility="collapsed"
)


if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    # st.text(df.columns)
    # print(len(df))
    # df = df.dropna(subset=['FacultyName', 'Comments'])
    aspect_categories = ["Teaching Pedagogy", "Knowledge", "Fair in Assessment", "Experience", "Behavior"]

    df = df[df['Target'].str.contains('Teacher', case=False, na=False)]
    semester_name = os.path.splitext(uploaded_file.name)[0]
    teachers = sorted(df['FacultyName'].dropna().unique())
    # print(len(teachers), len(df))

    #Sidebar Teacher selection logic
    selected_teacher = st.sidebar.selectbox("Select a Teacher", teachers)
    
    if selected_teacher:
        processed_file_path = f"Datasets/{semester_name}/{selected_teacher}_processed_feedback.csv"

        if os.path.exists(processed_file_path):
            teacher_df = pd.read_csv(processed_file_path)
        else:
            st.info("Processing feedback with LLM... Please wait ⏳")
            teacher_df = process_teacher_feedback_with_llm(df, selected_teacher, semester_name)
            st.success("Processing complete ✅")


        selected_course = "All"
        selected_class = "All"

        selected_aspects = st.sidebar.multiselect(
            "Select Aspects to Include in Report",
            options=aspect_categories,
            default=aspect_categories
        )

        courses = sorted(teacher_df['Course'].unique().tolist())
        selected_course = st.sidebar.selectbox("Select a Course (Optional)", ['All'] + courses)
        # Add multiselect for aspects (after course selection)



        if selected_course != 'All':
            class_options = sorted(teacher_df[teacher_df['Course'] == selected_course]['Class'].astype(str).unique().tolist())
            selected_class = st.sidebar.selectbox("Select a Class (Optional)", ['All'] + class_options)

            if selected_class != 'All':
                teacher_df = teacher_df[(teacher_df['Course'] == selected_course) & (teacher_df['Class'].astype(str) == selected_class)]
                st.markdown(f"### Feedback Report for {selected_teacher} | **Course: {selected_course} | Class: {selected_class}**")
            else:
                teacher_df = teacher_df[teacher_df['Course'] == selected_course]
                st.markdown(f"### Feedback Report for {selected_teacher} | **Course: {selected_course}**")
        else:
            st.markdown(f"### Overall Feedback Report for {selected_teacher}")


        # Generate bar chart
        bar_graph_path =generate_bar_chart(teacher_df, selected_aspects)


        # Generate word clouds
        wordcloud_images = generate_wordcloud(teacher_df, selected_aspects)

        wordcloud_paths = []
        for aspect, wc_img in wordcloud_images:
            img_path = os.path.join(tempfile.gettempdir(), f"{aspect}_wordcloud.png")
            wc_img.to_file(img_path)
            wordcloud_paths.append((aspect, img_path))

        # Generate PDF
        pdf = PDF()
        pdf.add_page()
        pdf.add_teacher_info(selected_teacher, selected_course, selected_class if selected_course != 'All' else 'All')

        # Add total respondents on the first page
        total_respondents = teacher_df['Comments'].dropna().count()
        pdf.add_respondents_info(total_respondents)

        # Add sentiment analysis bar chart
        pdf.add_bar_chart_image(bar_graph_path)

        for aspect, path in wordcloud_paths:
            aspect_df = teacher_df[
                teacher_df[f"{aspect}_terms"].fillna("").str.strip().pipe(lambda s: (s != "") & (s.str.lower() != "none") )
                
            ]
            discussed_count = len(aspect_df)            
            pdf.add_aspect_info(aspect, discussed_count, total_respondents, path, aspect_df)

        os.makedirs("Reports/"+semester_name, exist_ok=True)
        import re
        import os

        def sanitize_filename(s):
            s = re.sub(r'\s+', '', s)
            s = re.sub(r'[<>:"/\\|?*]', '_', s)
            return s.replace(' ', '_')

        safe_teacher = sanitize_filename(selected_teacher)
        safe_course = sanitize_filename(selected_course)
        safe_class = sanitize_filename(selected_class)

        pdf_path = os.path.join("Reports", semester_name, f"{safe_teacher}_{safe_course}_{safe_class}.pdf")

        # pdf_path = os.path.join("Reports/"+semester_name, f"{selected_teacher.replace(' ', '_')}_{selected_course}_{selected_class.replace(':', '')}.pdf")

        try:
            pdf.output(pdf_path, dest='F')  # 'F' stands for File
            st.success(f"PDF report saved to: {pdf_path}")
        except Exception as e:
            st.error(f"Failed to save PDF report: {e}")
        # Provide option to download it via Streamlit
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="Download Full Feedback Report (PDF)",
                data=f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf"
            )

else:
    st.info("Please upload a CSV file to begin.")

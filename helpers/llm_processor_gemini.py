import pandas as pd
import re
import os
# import ollama # Remove this line
import streamlit as st
from helpers.utils import parse_json_safe

# Add Google AI import
import google.generativeai as genai

# Configure Google AI with API key from secrets
# This should ideally be done once outside the function if possible,
# but inside the function works if called per request.
# For Streamlit, initializing here is common.
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Google AI API key not found in Streamlit secrets. Please add GOOGLE_API_KEY.")
    # Handle error - maybe return None or raise an exception
    # For now, let's assume the key is there for the function to work.

# =========================================
# Helper Functions for LLM Processing
# =========================================
# Function to parse LLM JSON safely (assuming this is defined elsewhere)
# from helpers.utils import parse_json_safe

# Function to ask the LLM for feedback analysis using Google AI
def ask_llm(input_content, system_prompt, model_name='gemma-3-12b-it'): # Use a suitable Gemini model
    if "GOOGLE_API_KEY" not in st.secrets:
        return None # Or handle error appropriately

    try:
        model = genai.GenerativeModel(
            model_name,
            system_instruction=[system_prompt] # Use system_instruction for Gemini 1.5+
        )
        response = model.generate_content(
            contents=[{"role": "user", "parts": [input_content]}],
            generation_config=genai.types.GenerationConfig(
                response_mime_type='application/json' # Specify JSON output for Gemini 1.5+
            )
        )
        # Gemini returns text directly in response.text
        response_text = response.text.strip()
        return response_text
    except Exception as e:
        st.error(f"Error calling Google Gemini API: {e}")
        return None # Return None or handle error

# Function to process teacher feedback dataframe with LLM
def process_teacher_feedback_with_llm(df, selected_teacher, semester_name):
    # ... (system_prompt and initial setup remains the same) ...
    system_prompt = """
    You are an expert in Aspect-Based Sentiment Analysis (ABSA). Your task is to analyze teacher reviews and extract aspect-specific information based on the following predefined aspect categories:

    - Teaching Pedagogy
    - Knowledge
    - Fair in Assessment
    - Experience
    - Behavior

    For each aspect category that is **explicitly or implicitly mentioned** in the review:
    1. Identify and extract the **aspect term(s) or phrase(s)** used in the review that are related to the aspect category.These extracted terms should be the substrings from the review.
    2. if multiple terms are found, return them as a list. If no terms are found, return "None" for aspect terms and polarity.
    3. Determine the **sentiment polarity** expressed toward that aspect category. Choose one of: {Positive, Negative, Neutral}.
    4. Do not include any explanation or additional information in your response.
    5. Return the output in a structured JSON format as follows:
    ```json
    {
    "Aspect Category": {
        "Aspect Terms": "..." OR [...],
        "Polarity": "..."
    },
    ...
    }
    ```
    """
    aspects = ["Teaching Pedagogy", "Knowledge", "Fair in Assessment", "Experience", "Behavior"]
    term_columns = [f"{aspect}_terms" for aspect in aspects]
    polarity_columns = [f"{aspect}_polarity" for aspect in aspects]

    teacher_df = df[df['FacultyName'] == selected_teacher].copy()

    # Add empty columns if they don't exist
    for col in term_columns + polarity_columns:
        if col not in teacher_df.columns:
            teacher_df[col] = ""

    indices_to_process = teacher_df.index

    # Change the model name to a Gemini model available via API
    model_name = 'gemini-1.5-flash' # Recommended balance of cost/performance for this task
    # Or 'gemini-1.5-pro' for potentially better accuracy at higher cost/latency

    progress_bar = st.progress(0)
    total = len(indices_to_process)

    for idx_num, idx in enumerate(indices_to_process):
        feedback = teacher_df.at[idx, 'Comments']
        if (
            pd.isna(feedback) or
            feedback.strip() == "" or
            re.fullmatch(r"[.\s]*", feedback) or
            len(feedback.strip().split()) <= 1 or
            feedback.strip().lower().replace(".", "").replace(" ", "") in {"na", "n/a"}
        ):
            continue

        try:
            # Call the new function
            result_json = ask_llm(feedback, system_prompt, model_name=model_name)

            if result_json is None: # Handle API error case
                 print(f"Skipping index {idx} due to API error.")
                 continue

            teacher_df.at[idx, "llm_response"] = result_json

            result_dict = parse_json_safe(result_json)

            if result_dict:
                 for aspect in aspects:
                     if aspect in result_dict:
                         aspect_data = result_dict[aspect]

                         aspect_terms = "None"
                         polarity = "Neutral"

                         if isinstance(aspect_data, dict):
                             aspect_terms = aspect_data.get("Aspect Terms", "None")
                             polarity = aspect_data.get("Polarity", "Neutral")
                         elif isinstance(aspect_data, list):
                             aspect_terms = aspect_data
                             polarity = result_dict.get("Polarity", "Neutral") # Handle list case where polarity might be top-level? (Less likely with your prompt)
                         elif isinstance(aspect_data, str): # Less likely with your prompt, but included for robustness
                             aspect_terms = aspect_data
                             polarity = result_dict.get("Polarity", "Neutral")

                         if isinstance(aspect_terms, list):
                             aspect_terms = ",".join(aspect_terms) if aspect_terms else "None"
                         else:
                             aspect_terms = str(aspect_terms)


                         teacher_df.at[idx, f"{aspect}_terms"] = aspect_terms
                         teacher_df.at[idx, f"{aspect}_polarity"] = polarity

        except Exception as e:
            print(f"Error processing index {idx} or parsing JSON: {e}")
            print(f"Response received (if any): {result_json}")
            print()
            continue

        # Update progress
        progress_bar.progress((idx_num + 1) / total)

    progress_bar.empty()

    os.makedirs("Datasets/"+semester_name, exist_ok=True)
    processed_path = f"Datasets/{semester_name}/{selected_teacher}_processed_feedback.csv"
    teacher_df.to_csv(processed_path, index=False)
    return teacher_df
import pandas as pd
import re
import os
import requests
import streamlit as st
from helpers.utils import parse_json_safe


api_url = st.secrets["NGROK_URL"] 

# Function to ask the LLM for feedback analysis

def ask_ollama_api(input_content, system_prompt, model_name, ngrok_url):
    url = f"{ngrok_url}/api/chat"
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': input_content}
        ],
        'stream': False  # make sure to set stream=False if you want single JSON
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            # If you want only the assistant's reply:
            reply = data.get("message", {}).get("content", "").strip()
            return reply
        except Exception as e:
            return f"Error parsing JSON: {e}\nRaw text: {response.text}"
    else:
        return f"Error: {response.status_code} - {response.text}"



# def ask_ollama(input_content, system_prompt, model_name):
#     response = ollama.chat(model=model_name, messages=[
#         {'role': 'system', 'content': system_prompt},
#         {'role': 'user', 'content': input_content}
#     ])
#     response_text = response['message']['content'].strip()
#     return response_text


# Function to process teacher feedback dataframe with LLM
def process_teacher_feedback_with_llm(teacher_df, selected_teacher, semester_name, aspects):
    system_prompt = """
    You are an expert in Aspect-Based Sentiment Analysis (ABSA). Your task is to analyze teacher reviews and extract aspect-specific information for the following predefined categories:

    - Teaching Pedagogy  
    - Knowledge  
    - Fair in Assessment  
    - Experience  
    - Behavior  

    Instructions:
    1. For each aspect category **explicitly or implicitly mentioned** in the review:
    - Extract the **exact aspect term(s) or phrase(s)** from the review text. Only include substrings that appear verbatim in the review.
    - If multiple terms/phrases are found, return them as a list.
    - If no relevant phrase is found for a category, return `"Aspect Terms": None` and `"Polarity": None`.

    2. Determine the **sentiment polarity** toward each mentioned aspect: one of `{Positive, Negative, Neutral}`.

    3. Return the output in the following structured JSON format **without any explanation or commentary**:

    ```json
    {
    "Teaching Pedagogy": {
        "Aspect Terms": [...], 
        "Polarity": "..."
    },
    "Knowledge": {
        "Aspect Terms": [...], 
        "Polarity": "..."
    },
    ...
    }

    """
    # aspects = ["Teaching Pedagogy", "Knowledge", "Fair in Assessment", "Experience", "Behavior"]
    term_columns = [f"{aspect}_terms" for aspect in aspects]
    polarity_columns = [f"{aspect}_polarity" for aspect in aspects]

    # teacher_df = df[df['FacultyName'] == selected_teacher].copy()

    # Add empty columns if they don't exist
    for col in term_columns + polarity_columns:
        if col not in teacher_df.columns:
            teacher_df[col] = ""

    indices_to_process = teacher_df.index

    model_name = 'mistral'  # The model name to use
    
    progress_bar = st.progress(0)
    total = len(indices_to_process)

    for idx_num, idx in enumerate(indices_to_process):
        feedback = teacher_df.at[idx, 'Comments']
        if (
            pd.isna(feedback) or 
            feedback.strip() == "" or 
            re.fullmatch(r"[.\s]*", feedback) or 
            len(feedback.strip()) < 8 or 
            feedback.strip().lower().replace(".", "").replace(" ", "") in {"na", "n/a", "nocomments", "nocomment", "noany", "none"}
        ):
            continue
        
        try:
            # Replace with your actual API URL
            result_json = ask_ollama_api(feedback, system_prompt, model_name = model_name, ngrok_url=api_url)
            teacher_df.at[idx, "llm_response"] = result_json

            result_dict = parse_json_safe(result_json)

            if result_dict:
                for aspect in aspects:
                    if aspect in result_dict:
                        # Extract aspect terms and polarity
                        aspect_data = result_dict[aspect]

                        # Initialize defaults
                        aspect_terms = "None"
                        polarity = "Neutral"

                        if isinstance(aspect_data, dict):
                            # Case: aspect is a dict containing Aspect Terms and Polarity
                            aspect_terms = aspect_data.get("Aspect Terms", "None")
                            polarity = aspect_data.get("Polarity", "Neutral")
                        elif isinstance(aspect_data, list):
                            # Case: aspect is a list of aspect terms, polarity might be separately given
                            aspect_terms = aspect_data
                            polarity = result_dict.get("Polarity", "Neutral")
                        elif isinstance(aspect_data, str):
                            # Very rare case: if it's just a plain string
                            aspect_terms = aspect_data
                            polarity = result_dict.get("Polarity", "Neutral")
                        # Convert aspect_terms to comma-separated string if it's a list
                        if isinstance(aspect_terms, list):
                            aspect_terms = ",".join(aspect_terms) if aspect_terms else "None"
                        else:
                            aspect_terms = str(aspect_terms)


                        # Save to dataframe
                        teacher_df.at[idx, f"{aspect}_terms"] = aspect_terms
                        teacher_df.at[idx, f"{aspect}_polarity"] = polarity 
                        # print(f"Aspect: {aspect}, Terms: {aspect_terms}, Polarity: {polarity}")                        
        except Exception as e:
            print(f"Error at index {idx}: {e}")
            # print(f"Response: {result_json}")
            print()
            continue
        
        # Update progress
        progress_bar.progress((idx_num + 1) / total)

    progress_bar.empty()  # Remove progress bar after completion

    os.makedirs("Datasets/"+semester_name, exist_ok=True)
    processed_path = f"Datasets/{semester_name}/{selected_teacher}_processed_feedback.csv"
    teacher_df.to_csv(processed_path, index=False)
    return teacher_df

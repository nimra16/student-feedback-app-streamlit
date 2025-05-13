import re
import json
import textwrap

# Helper function to wrap text
def wrap_text(text, width=80):
    return "<br>".join(textwrap.wrap(text, width=width))



def parse_json_safe(response_text):
    try:
        # Remove markdown code block markers
        response_text = response_text.strip().strip("```json").strip("```")

        # Replace Python-style None with JSON null
        response_text = response_text.replace(": None", ": null")

        # Fix common issues like trailing commas
        response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)

        # Extract JSON substring
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        json_substring = response_text[json_start:json_end]

        # print(f"Extracted JSON substring: {json_substring}")
        return json.loads(json_substring)

    except Exception as e:
        print(f"JSON parsing failed: {e}\nRaw response: {response_text}")
        return None
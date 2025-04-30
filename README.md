
# 🧠 Connecting a Local Ollama Server to a Cloud Streamlit App Using Ngrok

This guide explains how to run [Ollama](https://ollama.com) on your **local machine** and make it accessible to a **cloud-hosted Streamlit app** using [Ngrok](https://ngrok.com/).

---

## 📦 Prerequisites

- ✅ Ollama installed locally → [Download here](https://ollama.com/download)
- ✅ Ngrok installed → [Download here](https://ngrok.com/download)
- ✅ A cloud-hosted Streamlit app (e.g., on [Streamlit Community Cloud](https://streamlit.io/cloud), AWS, or others)

---

## 🚀 Step-by-Step Instructions

### ✅ 1. Start Ollama on Localhost with External Access

By default, Ollama listens on `localhost`, which is **not accessible from outside** your machine. To fix that:

#### On Windows:

```cmd
set OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

#### On Linux/macOS:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

#### Or using the CLI flag:

```bash
ollama serve --host 0.0.0.0
```

---

### ✅ 2. Verify Ollama is Running

Run this in your terminal:

```bash
curl http://localhost:11434
```

You should get a JSON response indicating that the server is live.

---

### ✅ 3. Expose Ollama Port with Ngrok

Run the following command:

```bash
ngrok http 11434
```
If you get multiple tunnels cant run error, then Run and run previous again

```bash
taskkill /F /IM ngrok.exe 
```


Ngrok will give you a URL like:

```
https://your-ngrok-url.ngrok-free.app
```

To verify, Ollama is running on provided ngrok url, Run this in your terminal:

```bash
curl https://your-ngrok-url.ngrok-free.app
```
You should get a JSON response indicating that the server is live.



Copy this URL. You’ll use it to connect your cloud app to Ollama.


---

### ✅ 4. Use in Streamlit (Example Python Code)

In your Streamlit app (or any Python client), use the following code to send prompts to your local Ollama server via Ngrok:

```python
import requests

def ask_ollama_api(prompt_text, model_name, ngrok_url):
    url = f"{ngrok_url}/api/generate"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'model': model_name,
        'prompt': prompt_text,
        'stream': False  # Important for simple JSON response
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get('response', '').strip()
    else:
        return f"Error: {response.status_code} - {response.text}"

# Example usage:
response = ask_ollama_api(
    prompt_text="Explain sentiment of: 'The teacher wasn't helpful at all'",
    model_name="your-model-name",
    ngrok_url="https://your-ngrok-url.ngrok-free.app"
)
print(response)
```

---

## 🛠️ Tips

- Your Ngrok URL changes every time unless you have a paid account with a reserved domain.
- Always make sure Ngrok is running when you deploy your Streamlit app.
- Use Streamlit secrets to store the Ngrok URL securely (`.streamlit/secrets.toml`).

---

## ✅ Example `secrets.toml`

```toml
NGROK_URL = "https://your-ngrok-url.ngrok-free.app"
```

Then in your app:

```python
import streamlit as st

ngrok_url = st.secrets["NGROK_URL"]
```

---

## 📬 Need Help?

If you get a `404` or `JSONDecodeError`, check:
- Is Ollama running on `0.0.0.0`?
- Is Ngrok correctly tunneling port `11434`?
- Are you using the correct endpoint (`/api/generate` for non-chat, `/api/chat` for chat-based)?



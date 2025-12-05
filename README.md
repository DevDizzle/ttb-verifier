# 🍷 TTB Label Verifier (AI-Powered)

**Live Demo:** [https://ttb-verifier-550651297425.us-central1.run.app](https://ttb-verifier-550651297425.us-central1.run.app)

## Overview
This is a full-stack automated compliance agent designed to simulate the TTB alcohol label approval process. It accepts a product label image and form data, then uses **Multimodal Generative AI** (Google Gemini 2.0 Flash) to semantically verify if the label matches the application details.

## ✨ Features
* **AI Verification:** Uses Gemini 2.0 Flash to "read" and reason about label text, replacing brittle OCR+Regex pipelines.
* **Fuzzy Matching:** Handles minor formatting differences (e.g., "40%" vs "Alc. 40% by Vol") natively.
* **Compliance Checks:** Verifies Brand Name, Class/Type, ABV, Net Contents, and the presence of the mandatory **Government Warning**.
* **Instant Feedback:** Provides a clear "Match/Mismatch" dashboard with detailed findings.

## 🛠 Tech Stack
* **Frontend:** HTML5, Bootstrap 5 (Server-rendered for simplicity).
* **Backend:** Python **FastAPI**.
* **AI/ML:** **Google Vertex AI** (Gemini 2.0 Flash).
* **Infrastructure:** **Google Cloud Run** (Serverless container).

## 🚀 How to Run Locally

### Prerequisites
* Python 3.10+
* Google Cloud Project with `Vertex AI API` enabled.
* `gcloud` CLI installed and authenticated.

### Installation
1.  Clone the repository:
    ```bash
    git clone https://github.com/DevDizzle/ttb-verifier.git
    cd ttb-verifier
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Set your Google Cloud Project ID:
    ```bash
    # Linux/Mac
    export GOOGLE_CLOUD_PROJECT="paperrec-ai"
    # Windows
    set GOOGLE_CLOUD_PROJECT=paperrec-ai
    ```

4.  Run the server:
    ```bash
    uvicorn app.main:app --reload
    ```
5.  Open `http://127.0.0.1:8000` in your browser.

## 🧠 Architectural Decisions & Approach

### Why Gemini 2.0 Flash vs. Tesseract OCR?
Traditional OCR (Tesseract) outputs unstructured text that requires complex Regular Expressions to parse. By using a **Multimodal LLM (Gemini 2.0)**, we can treat the image verification as a *reasoning* task. The model understands that "Kentucky Straight Bourbon" matches the form input "Bourbon" semantically, which makes the system significantly more robust to real-world label variations.

### Infrastructure (Cloud Run)
The application is containerized (Docker) and deployed to **Google Cloud Run**. This was chosen for:
* **Scale-to-Zero:** Cost-efficient when not in use.
* **Simplicity:** A single command deploys both the API and the UI.
* **Security:** Managed HTTPS out of the box.

### Security Note
For this MVP, the service runs using the default Compute Engine Service Account to prioritize deployment velocity. In a production environment, I would implement **Least Privilege** by creating a dedicated Service Account with access scoped strictly to `roles/aiplatform.user`.

## 📂 Project Structure
```text
/app
  ├── main.py            # FastAPI backend & Vertex AI Logic
  └── templates/         # UI Frontend (Jinja2)
/samples                 # Example label images for testing
Dockerfile               # Container configuration
requirements.txt         # Python dependencies
```

## ✅ Future Improvements
* **Bounding Box Highlighting:** Use Cloud Vision API to draw rectangles around matched text on the image.
* **User Accounts:** Save submission history to Firestore.
* **Strict Warning Check:** Validate the exact wording of the Government Warning against the official TTB legal text.

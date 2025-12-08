# 🍷 TTB Label Verifier (AI-Powered)

**Live Demo:** [https://ttb-verifier-550651297425.us-central1.run.app](https://ttb-verifier-550651297425.us-central1.run.app)

## Overview
This is a full-stack automated compliance agent designed to simulate the TTB alcohol label approval process. It accepts a product label image and form data, then uses **Multimodal Generative AI** (Google Gemini 2.0 Flash) to semantically verify if the label matches the application details. It also employs a hybrid approach using **Google Cloud Vision API** for precise text localization (bounding boxes).

## ✨ Features
* **AI Verification:** Uses Gemini 2.0 Flash to "read" and reason about label text, replacing brittle OCR+Regex pipelines.
* **Hybrid Localization:** Combines Gemini's reasoning with Cloud Vision's OCR to draw accurate bounding boxes around verified text on the image.
* **Fuzzy Matching:** Handles minor formatting differences (e.g., "40%" vs "Alc. 40% by Vol") natively.
* **Compliance Checks:** Verifies Brand Name, Class/Type, ABV, Net Contents, and the presence of the mandatory **Government Warning**.
* **Professional UI:** A Single Page Application (SPA) with a "Federal Agency" inspired theme, drag-and-drop uploads, and async feedback.
* **Instant Feedback:** Provides a clear "Match/Mismatch" dashboard with visual evidence.

## 🛠 Tech Stack
* **Frontend:** HTML5, Bootstrap 5 (Agency Theme), JavaScript (Fetch API).
* **Backend:** Python **FastAPI**.
* **AI/ML:** **Google Vertex AI** (Gemini 2.0 Flash) & **Google Cloud Vision API**.
* **Infrastructure:** **Google Cloud Run** (Serverless container).

## 💰 Estimated Cost per Image

Running this automated verification is significantly cheaper than human labor. Here is a rough breakdown based on standard pricing (as of late 2024/2025):

*   **Gemini 2.0 Flash:**
    *   **Input Tokens (~$0.10 / 1M tokens):** A typical label image + prompt consumes ~3,000 tokens.
    *   **Output Tokens (~$0.40 / 1M tokens):** The JSON response is small (~200 tokens).
    *   *Estimated Gemini Cost:* ~$0.0004 per transaction.

*   **Google Cloud Vision API:**
    *   **OCR (Text Detection):** ~$1.50 per 1,000 units (after the first 1,000 free per month).
    *   *Estimated Vision Cost:* ~$0.0015 per transaction.

**Total Estimated Cost:** **~$0.0019 per label** (less than 1/5th of a penny).

## 🚀 How to Run Locally

### Prerequisites
* Python 3.10+
* Google Cloud Project with the following APIs enabled:
    * `Vertex AI API`
    * `Cloud Vision API`
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

### Why Hybrid (Gemini + Vision API)?
While **Gemini 2.0** is excellent at semantic understanding (knowing that "Kentucky Straight Bourbon" matches "Bourbon"), large language models can sometimes struggle with precise pixel-level coordinate generation for bounding boxes.
We solve this by using **Cloud Vision OCR** to get the exact coordinates of every word on the page, and then using Gemini's output to "search" that OCR map. This gives us the best of both worlds: high-level reasoning + pixel-perfect highlighting.

### Infrastructure (Cloud Run)
The application is containerized (Docker) and deployed to **Google Cloud Run**. This was chosen for:
* **Scale-to-Zero:** Cost-efficient when not in use.
* **Simplicity:** A single command deploys both the API and the UI.
* **Security:** Managed HTTPS out of the box.

## 📂 Project Structure
```text
/app
  ├── main.py            # FastAPI backend (Gemini + Vision Logic)
  └── templates/         # UI Frontend (Jinja2, Agency Theme)
/samples                 # Example label images for testing
/tests                   # Automated tests
  ├── test_api.py        # Unit tests
  └── test_e2e.py        # End-to-End tests
Dockerfile               # Container configuration
requirements.txt         # Python dependencies
```

## ✅ Automated Testing

I have included both Unit and End-to-End tests to ensure reliability.

### 1. Install Test Dependencies
```bash
pip install pytest httpx playwright pytest-playwright
playwright install
```

### 2. Run Tests
You need two terminal tabs.

**Terminal 1 (Run your App):**
You must have the app running for the E2E test to visit localhost:8000.
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 (Run the Tests):**
```bash
# Run ALL tests
pytest

# Run just the unit tests (Fast)
pytest tests/test_api.py

# Run just the E2E tests (Slower, launches browser)
pytest tests/test_e2e.py
```

**Test Details:**
*   **Unit Tests (`tests/test_api.py`)**: Uses `pytest` and `unittest.mock` to verify API logic without incurring costs on the Vertex AI API.
*   **E2E Tests (`tests/test_e2e.py`)**: Uses `Playwright` to spin up a headless Chromium browser and test the full user flow (Upload -> Verify -> UI Result).
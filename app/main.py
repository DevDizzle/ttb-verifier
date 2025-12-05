import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Initialize Vertex AI (Ensure you set your specific project ID in env vars or here)
# PRO TIP: In Cloud Run, authentication is automatic via the Service Account.
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "paperrec-ai")
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)

def analyze_label_with_gemini(image_bytes: bytes, form_data: dict) -> dict:
    """Sends image and form data to Gemini 2.0 Flash for verification."""
    
    logger.info(f"Sending request to Gemini with form data: {form_data}")
    
    model = GenerativeModel("gemini-2.0-flash-001")
    
    # 1. Create the Image Part
    image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
    
    # 2. Construct the Prompt (The "TTB Agent" Instructions)
    prompt = f"""
    You are an expert Alcohol and Tobacco Tax and Trade Bureau (TTB) agent. 
    Your task is to verify if the information on the alcohol label image matches the submitted form data.
    
    Form Data to Verify:
    - Brand Name: "{form_data.get('brand_name')}"
    - Product Class/Type: "{form_data.get('product_type')}"
    - Alcohol Content (ABV): "{form_data.get('abv')}"
    - Net Contents: "{form_data.get('net_contents')}"
    
    Instructions:
    1. Extract the text from the label image for each field.
    2. Compare the extracted text with the Form Data. Be tolerant of minor formatting differences (e.g., "40%" vs "40% Alc/Vol").
    3. Check if the "GOVERNMENT WARNING" statement is present on the label (mandatory).
    4. Return the result in strictly valid JSON format. Do not use Markdown code blocks.
    
    Required JSON Structure:
    {{
      "brand_name": {{ "match": boolean, "found_value": string, "reason": string }},
      "product_type": {{ "match": boolean, "found_value": string, "reason": string }},
      "abv": {{ "match": boolean, "found_value": string, "reason": string }},
      "net_contents": {{ "match": boolean, "found_value": string, "reason": string }},
      "government_warning": {{ "present": boolean, "found_text_snippet": string }},
      "overall_match": boolean
    }}
    """

    # 3. Generate Response
    response = model.generate_content(
        [image_part, prompt],
        generation_config={"response_mime_type": "application/json"}
    )
    
    raw_response_text = response.text
    logger.info(f"Raw response from Gemini: {raw_response_text}")

    # Clean the response text (remove markdown code blocks if present)
    cleaned_response_text = raw_response_text.replace("```json", "").replace("```", "").strip()
    
    return json.loads(cleaned_response_text)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/verify")
async def verify_label(
    brand_name: str = Form(...),
    product_type: str = Form(...),
    abv: str = Form(...),
    net_contents: str = Form(None),
    file: UploadFile = File(...)
):
    # Read image file
    image_bytes = await file.read()
    
    form_data = {
        "brand_name": brand_name,
        "product_type": product_type,
        "abv": abv,
        "net_contents": net_contents or "N/A"
    }

    # Process with Gemini
    try:
        verification_result = analyze_label_with_gemini(image_bytes, form_data)
        return verification_result
    except Exception as e:
        logger.error("Error processing verification request", exc_info=True)
        return {"error": str(e)}
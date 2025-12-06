import os
import json
import logging
import io
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import vision
from PIL import Image as PILImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Initialize Vertex AI & Vision API
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "paperrec-ai")
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Try to initialize Vision Client (might fail if API not enabled)
try:
    vision_client = vision.ImageAnnotatorClient()
except Exception as e:
    logger.warning(f"Could not init Vision Client: {e}")
    vision_client = None

def get_ocr_annotations(image_bytes: bytes):
    """Calls Cloud Vision to get text annotations."""
    if not vision_client:
        return []
    try:
        image = vision.Image(content=image_bytes)
        response = vision_client.text_detection(image=image)
        if response.error.message:
            logger.error(f"OCR Error: {response.error.message}")
            return []
        return response.text_annotations
    except Exception as e:
        logger.error(f"OCR Exception: {e}")
        return []

def find_box_for_text(target_text: str, annotations, width: int, height: int) -> Optional[List[int]]:
    """
    Finds the bounding box for target_text within annotations using multiple strategies.
    Returns [ymin, xmin, ymax, xmax] scaled to 0-1000.
    """
    if not target_text or not annotations or len(annotations) < 2:
        return None
    
    target_normalized = target_text.lower().strip()
    words = target_normalized.split()
    if not words:
        return None

    # Strategy 1: Exact Phrase Match (Consecutive Sequence)
    # We search for the sequence of words in the annotations.
    for i, ann in enumerate(annotations[1:], 1):
        ann_text = ann.description.lower()
        if words[0] in ann_text:
            # Possible start of sequence
            matched_indices = [i]
            match_valid = True
            current_ann_idx = i + 1
            
            for w in words[1:]:
                if current_ann_idx >= len(annotations):
                    match_valid = False
                    break
                
                next_ann_text = annotations[current_ann_idx].description.lower()
                # Simple check: is the word in the next annotation?
                if w in next_ann_text:
                    matched_indices.append(current_ann_idx)
                    current_ann_idx += 1
                else:
                    match_valid = False
                    break
            
            if match_valid:
                return calculate_box_from_indices(matched_indices, annotations, width, height)

    # Strategy 2: Keyword Fallback (for "GOVERNMENT WARNING")
    # If the exact phrase isn't found, look for the specific key header "GOVERNMENT WARNING"
    # or "GOVERNMENT" near "WARNING".
    if "government" in target_normalized and "warning" in target_normalized:
        gov_indices = []
        for i, ann in enumerate(annotations[1:], 1):
            txt = ann.description.lower()
            if "government" in txt or "warning" in txt:
                gov_indices.append(i)
        
        # If we found them close together, return their union
        if gov_indices:
             # Filter for clustered indices if needed, for now return union of all found
             return calculate_box_from_indices(gov_indices, annotations, width, height)

    return None

def calculate_box_from_indices(indices: List[int], annotations, width: int, height: int) -> List[int]:
    """Helper to compute bounding box from a list of annotation indices."""
    all_xs = []
    all_ys = []
    for idx in indices:
        poly = annotations[idx].bounding_poly
        all_xs.extend([v.x for v in poly.vertices])
        all_ys.extend([v.y for v in poly.vertices])
    
    if all_xs and all_ys:
        ymin = int((min(all_ys) / height) * 1000)
        xmin = int((min(all_xs) / width) * 1000)
        ymax = int((max(all_ys) / height) * 1000)
        xmax = int((max(all_xs) / width) * 1000)
        return [ymin, xmin, ymax, xmax]
    return None

def analyze_label_with_gemini(image_bytes: bytes, form_data: dict) -> dict:
    """Hybrid Approach: OCR for boxes + Gemini for reasoning."""
    
    # 1. Get Image Dimensions (for coordinate scaling)
    try:
        with PILImage.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
    except Exception:
        width, height = 1000, 1000 # Fallback
    
    # 2. Run OCR (Cloud Vision)
    ocr_annotations = get_ocr_annotations(image_bytes)
    
    # 3. Run Gemini (Reasoning)
    model = GenerativeModel("gemini-2.0-flash-001")
    image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
    
    # Modified Prompt: Ask for full government warning text
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
    2. Compare the extracted text with the Form Data. Be tolerant of minor formatting differences.
    3. Check if the "GOVERNMENT WARNING" statement is present on the label (mandatory). Extract the FULL text of the warning starting with "GOVERNMENT WARNING".
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

    response = model.generate_content(
        [image_part, prompt],
        generation_config={"response_mime_type": "application/json"}
    )
    
    # Parse Gemini Result
    cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
    result = json.loads(cleaned_response)
    
    # 4. Inject Precise OCR Boxes
    fields_to_map = ["brand_name", "product_type", "abv", "net_contents"]
    for field in fields_to_map:
        if field in result and "found_value" in result[field]:
            text_val = result[field]["found_value"]
            box = find_box_for_text(text_val, ocr_annotations, width, height)
            if box:
                result[field]["box_2d"] = box
    
    # Special handling for Gov Warning (Full Block)
    if "government_warning" in result:
        gw = result["government_warning"]
        if "found_text_snippet" in gw and gw["found_text_snippet"]:
             snippet = gw["found_text_snippet"]
             # Try finding the FULL snippet first
             box = find_box_for_text(snippet, ocr_annotations, width, height)
             if box:
                 gw["box_2d"] = box
             else:
                 # Fallback: If full snippet fails (due to line breaks/OCR glitches), 
                 # try finding the bounds between "GOVERNMENT WARNING" and the end of the snippet.
                 # We can try just "GOVERNMENT WARNING" to at least highlight the start.
                 start_box = find_box_for_text("GOVERNMENT WARNING", ocr_annotations, width, height)
                 if start_box:
                     gw["box_2d"] = start_box

    # Add Token Usage
    usage = response.usage_metadata
    result["usage"] = {
        "input_tokens": usage.prompt_token_count,
        "output_tokens": usage.candidates_token_count,
        "total_tokens": usage.total_token_count
    }
    
    return result

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
    image_bytes = await file.read()
    form_data = {
        "brand_name": brand_name,
        "product_type": product_type,
        "abv": abv,
        "net_contents": net_contents or "N/A"
    }

    try:
        verification_result = analyze_label_with_gemini(image_bytes, form_data)
        return verification_result
    except Exception as e:
        logger.error("Error processing verification request", exc_info=True)
        return {"error": str(e)}
import google.generativeai as genai
import json
from PIL import Image
import os
import re

# Load config
with open('config/config.json') as f:
    config = json.load(f)

# Configure Gemini
genai.configure(api_key=config['gemini_api_key'])
model = genai.GenerativeModel("gemini-1.5-flash")

def extract_value_from_support_doc(doc_path):
    """
    Extracts ONLY the non-VAT total value (pre-tax amount)
    from a supporting document using Gemini vision model.
    Returns a float or None if failed.
    """
    try:
        # Load image
        img = Image.open(doc_path)

        # Stronger prompt to force numeric-only output
        prompt = """
        You are a financial data extraction engine.

        From this document, extract ONLY the total non-VAT value
        (the pre-tax total). 
        Return:
        - ONLY the numeric value
        - No currency symbol
        - No explanation
        - No text
        - No commas
        - No quotes
        - No code blocks

        Example output: 1234.56
        """

        response = model.generate_content([prompt, img])

        raw_text = response.text.strip()

        # Remove backticks or "json" code fences if Gemini adds them
        raw_text = re.sub(r"```.*?```", "", raw_text, flags=re.DOTALL).strip()

        # Extract the first numeric value (integer or float)
        match = re.search(r"[-+]?\d*\.\d+|\d+", raw_text)
        if match:
            return float(match.group())

        print(f"[WARN] No numeric value found in: {raw_text}")
        return None

    except Exception as e:
        print(f"[ERROR] Failed to extract from {doc_path}: {e}")
        return None

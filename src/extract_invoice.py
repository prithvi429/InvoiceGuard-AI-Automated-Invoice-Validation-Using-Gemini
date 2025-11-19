import google.generativeai as genai
import pandas as pd
from PIL import Image
import os
import json
from pdf2image import convert_from_path

# ---- Load config & initialize Gemini ----
with open('config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

genai.configure(api_key=config['gemini_api_key'])
model = genai.GenerativeModel("gemini-1.5-flash")

# ---- Helper: safely parse JSON from Gemini response ----
def parse_json_from_response(text: str):
    """
    Takes the raw response.text from Gemini and tries to extract a valid JSON string.
    Handles cases where the model wraps output in ```json ... ``` fences.
    """
    text = text.strip()

    # If fenced in ```json ... ``` or ```...``` remove the fences
    if text.startswith("```"):
        # Remove the first fence line
        lines = text.splitlines()
        # Drop first line (``` or ```json) and last line if it's ```
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Now `text` should be pure JSON array or object
    return json.loads(text)

# ---- Core: extract line items from a single invoice ----
def extract_line_items(invoice_path: str) -> pd.DataFrame:
    try:
        # 1) Convert to image (if PDF, take first page)
        if invoice_path.lower().endswith('.pdf'):
            images = convert_from_path(invoice_path, dpi=200)
            if not images:
                raise ValueError("No pages found in PDF.")
            img = images[0]
        else:
            img = Image.open(invoice_path)

        # 2) Prompt for Gemini
        prompt = """
        You are an expert in reading tax invoices.

        Analyze this tax invoice and extract EACH line item as a JSON object
        with the following keys:

        - item_description (string)
        - quantity (number)
        - unit_price (number, excluding VAT)
        - total_non_vat_value (number)
        - vat_amount (number)
        - currency (string)

        Return ONLY a valid JSON array of objects.
        Example:
        [
          {
            "item_description": "...",
            "quantity": 1,
            "unit_price": 100.0,
            "total_non_vat_value": 100.0,
            "vat_amount": 15.0,
            "currency": "USD"
          }
        ]

        No explanations, no comments, no extra fields.
        """

        # 3) Call Gemini (vision + prompt)
        response = model.generate_content([prompt, img])

        if not hasattr(response, "text") or not response.text:
            print(f"[WARN] Empty response from Gemini for: {invoice_path}")
            return pd.DataFrame()

        # 4) Parse JSON safely
        try:
            line_items = parse_json_from_response(response.text)
        except json.JSONDecodeError as je:
            print(f"[ERROR] JSON parsing failed for: {invoice_path}")
            print(f"Raw response was:\n{response.text[:500]}...")
            raise je

        # 5) Convert list of dict → DataFrame
        if isinstance(line_items, list) and line_items:
            return pd.DataFrame(line_items)
        else:
            print(f"[WARN] Parsed JSON is not a non-empty list for: {invoice_path}")
            return pd.DataFrame()

    except Exception as e:
        print(f"[ERROR] Failed to process {invoice_path}: {e}")
        return pd.DataFrame()

# ---- Process all invoices in a folder & save combined output ----
def process_invoices(invoices_folder: str, data_folder: str) -> pd.DataFrame:
    all_data = []

    # Ensure data folder exists
    os.makedirs(data_folder, exist_ok=True)

    for file_name in os.listdir(invoices_folder):
        if file_name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            full_path = os.path.join(invoices_folder, file_name)
            print(f"[INFO] Processing: {full_path}")
            df = extract_line_items(full_path)

            if not df.empty:
                df['invoice_file'] = file_name
                all_data.append(df)
            else:
                print(f"[WARN] No data extracted for: {file_name}")

    if all_data:
        df_combined = pd.concat(all_data, ignore_index=True)
        output_path = os.path.join(data_folder, 'extracted_invoices.csv')
        df_combined.to_csv(output_path, index=False, encoding='utf-8')
        print(f"[INFO] Saved extracted data to: {output_path}")
        return df_combined
    else:
        print("[WARN] No invoices processed successfully. No CSV created.")
        return pd.DataFrame()

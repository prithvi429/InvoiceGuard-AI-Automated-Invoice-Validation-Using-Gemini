import os
import json
import pandas as pd
from typing import List, Dict, Any

from PIL import Image
from pdf2image import convert_from_path
import google.generativeai as genai

# -------------------------------------------------------------------
# Load config
# -------------------------------------------------------------------
with open("config/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

GEMINI_API_KEY = config.get("gemini_api_key")
POPPLER_PATH = config.get("poppler_path")  # e.g. "C:/Users/DELL/Downloads/.../bin"

if not GEMINI_API_KEY:
    raise ValueError("Missing 'gemini_api_key' in config/config.json")

# -------------------------------------------------------------------
# Configure Gemini
# -------------------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


# -------------------------------------------------------------------
# Helper: safely parse JSON from Gemini response
# -------------------------------------------------------------------
def parse_json_from_response(text: str) -> Any:
    """
    Takes the raw response.text from Gemini and tries to extract a valid JSON value.
    Handles cases where the model wraps output in ```json ... ``` fences.
    """
    text = text.strip()

    # If fenced in ```json ... ``` or ```...``` remove the fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (``` or ```json)
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Drop last line if it's ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Now `text` should be pure JSON (array or object)
    return json.loads(text)


# -------------------------------------------------------------------
# Core: extract line items from a single invoice file
# -------------------------------------------------------------------
def extract_line_items(invoice_path: str) -> pd.DataFrame:
    """
    Extracts line items from a single invoice (PDF or image) using Gemini.

    Returns:
        DataFrame with columns at least:
        - item_description
        - quantity
        - unit_price
        - total_non_vat_value
        - vat_amount
        - currency
    """
    try:
        # 1) Convert invoice into an image
        invoice_path_lower = invoice_path.lower()

        if invoice_path_lower.endswith(".pdf"):
            print(f"[INFO] Converting PDF to image: {invoice_path}")
            # Use poppler_path if provided in config
            if POPPLER_PATH:
                images = convert_from_path(invoice_path, dpi=200, poppler_path=POPPLER_PATH)
            else:
                images = convert_from_path(invoice_path, dpi=200)

            if not images:
                raise ValueError("No pages found in PDF.")
            img = images[0]  # first page only for now
        else:
            print(f"[INFO] Opening image file: {invoice_path}")
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
            "item_description": "Laptop Model X",
            "quantity": 1,
            "unit_price": 900.0,
            "total_non_vat_value": 900.0,
            "vat_amount": 100.0,
            "currency": "USD"
          }
        ]

        No explanations, no comments, no extra fields.
        """

        # 3) Call Gemini with vision + instructions
        response = model.generate_content([prompt, img])

        if not hasattr(response, "text") or not response.text:
            print(f"[WARN] Empty response from Gemini for: {invoice_path}")
            return pd.DataFrame()

        raw_text = response.text
        # 4) Parse JSON safely
        try:
            line_items = parse_json_from_response(raw_text)
        except json.JSONDecodeError as je:
            print(f"[ERROR] JSON parsing failed for: {invoice_path}")
            print(f"Raw response (first 500 chars):\n{raw_text[:500]}...")
            raise je

        # 5) Convert list of dicts → DataFrame
        if isinstance(line_items, list) and line_items:
            df = pd.DataFrame(line_items)

            # Ensure expected columns exist (even if null)
            expected_cols = [
                "item_description",
                "quantity",
                "unit_price",
                "total_non_vat_value",
                "vat_amount",
                "currency",
            ]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None

            return df[expected_cols]  # keep column order consistent

        else:
            print(f"[WARN] Parsed JSON is not a non-empty list for: {invoice_path}")
            return pd.DataFrame()

    except Exception as e:
        print(f"[ERROR] Failed to process {invoice_path}: {e}")
        return pd.DataFrame()


# -------------------------------------------------------------------
# Process all invoices in a folder & save combined output
# -------------------------------------------------------------------
def process_invoices(invoices_folder: str, data_folder: str) -> pd.DataFrame:
    """
    Process all PDF/image invoices in the given folder.

    - Extracts line items for each invoice
    - Adds 'invoice_file' column
    - Saves combined data to data_folder/extracted_invoices.csv

    Returns:
        Combined DataFrame of all invoice line items.
    """
    all_data: List[pd.DataFrame] = []

    if not os.path.isdir(invoices_folder):
        print(f"[ERROR] Invoices folder not found: {invoices_folder}")
        return pd.DataFrame()

    os.makedirs(data_folder, exist_ok=True)

    for file_name in os.listdir(invoices_folder):
        if file_name.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
            full_path = os.path.join(invoices_folder, file_name)
            print(f"[INFO] Processing invoice file: {full_path}")
            df = extract_line_items(full_path)

            if not df.empty:
                df["invoice_file"] = file_name
                all_data.append(df)
            else:
                print(f"[WARN] No line items extracted for: {file_name}")

    if all_data:
        df_combined = pd.concat(all_data, ignore_index=True)
        output_path = os.path.join(data_folder, "extracted_invoices.csv")
        df_combined.to_csv(output_path, index=False, encoding="utf-8")
        print(f"[INFO] Saved extracted invoice data to: {output_path}")
        return df_combined
    else:
        print("[WARN] No invoices processed successfully. No CSV created.")
        return pd.DataFrame()

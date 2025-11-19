import pandas as pd
import os
import json
from src.extract_support_doc import extract_value_from_support_doc

# Load config
with open('config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

tolerance = config.get('tolerance', 0.01)  # default fallback

def _normalize_for_match(text: str) -> str:
    """
    Normalize text for simple filename matching:
    - lowercase
    - replace spaces with underscores
    - strip leading/trailing spaces
    """
    if not isinstance(text, str):
        return ""
    return text.strip().lower().replace(" ", "_")

def match_and_verify(df_invoice: pd.DataFrame,
                     supporting_docs_folder: str,
                     data_folder: str) -> pd.DataFrame:
    """
    For each invoice line item:
    - Try to find a supporting document whose filename contains a normalized
      version of the item_description.
    - Extract the non-VAT value from the supporting document using Gemini.
    - Compare it with the invoice total_non_vat_value using the configured tolerance.
    - Save verification results as CSV in data_folder.

    Returns:
        df_verification (pd.DataFrame): one row per invoice line item with verification status.
    """

    # Ensure folders exist / are valid
    if not os.path.isdir(supporting_docs_folder):
        print(f"[WARN] Supporting docs folder does not exist: {supporting_docs_folder}")

    os.makedirs(data_folder, exist_ok=True)

    verified_rows = []

    for idx, row in df_invoice.iterrows():
        item_desc = row.get('item_description', '')
        non_vat_value = row.get('total_non_vat_value', None)

        # Normalize description for filename match
        target_key = _normalize_for_match(item_desc)

        supporting_found = False
        matching_value = False
        matched_doc = ""
        extracted_value = None
        diff = None

        # Guard against missing numeric value
        try:
            non_vat_value = float(non_vat_value)
        except (TypeError, ValueError):
            print(f"[WARN] Non-numeric non-VAT value in invoice row {idx}: {non_vat_value}")
            non_vat_value = None

        if os.path.isdir(supporting_docs_folder) and target_key:
            for doc in os.listdir(supporting_docs_folder):
                doc_lower = doc.lower()
                if target_key in doc_lower:
                    supporting_found = True
                    matched_doc = doc
                    doc_path = os.path.join(supporting_docs_folder, doc)

                    extracted_value = extract_value_from_support_doc(doc_path)

                    if extracted_value is not None and non_vat_value is not None:
                        diff = extracted_value - non_vat_value
                        if abs(diff) <= tolerance:
                            matching_value = True
                    break  # stop after first match
        else:
            if not target_key:
                print(f"[WARN] Empty or invalid item_description in row {idx}")

        verified_rows.append({
            "item_description": item_desc,
            "invoice_non_vat_value": non_vat_value,
            "supporting_attached": supporting_found,
            "supporting_file": matched_doc,
            "extracted_non_vat_value": extracted_value,
            "difference": diff,
            "non_vat_match": matching_value,
            "invoice_file": row.get("invoice_file", "")
        })

    df_verification = pd.DataFrame(verified_rows)

    output_path = os.path.join(data_folder, "verification_results.csv")
    df_verification.to_csv(output_path, index=False, encoding="utf-8")
    print(f"[INFO] Verification results saved to: {output_path}")

    return df_verification

import os
import pandas as pd

from src.extract_invoice import process_invoices
from src.matcher import match_and_verify
from src.fx_rate_service import apply_fx_rates


def run_validation(invoices_folder: str,
                   supporting_docs_folder: str,
                   data_folder: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    End-to-end validation pipeline:

    1) Extract line items from all invoices in invoices_folder
       -> saves extracted_invoices.csv in data_folder

    2) Match & verify against supporting documents in supporting_docs_folder
       -> saves verification_results.csv in data_folder

    3) Apply FX rates and add converted_non_vat_value column
       -> saves converted_invoices.csv in data_folder

    Returns:
        df_invoice (pd.DataFrame): invoice lines with FX conversion
        df_verification (pd.DataFrame): per-line verification results
    """

    # Ensure folders exist
    if not os.path.isdir(invoices_folder):
        print(f"[ERROR] Invoices folder does not exist: {invoices_folder}")
        return pd.DataFrame(), pd.DataFrame()

    if not os.path.isdir(supporting_docs_folder):
        print(f"[WARN] Supporting docs folder does not exist: {supporting_docs_folder}")

    os.makedirs(data_folder, exist_ok=True)

    # 1) Extract invoice line items
    print("[INFO] Step 1/3: Extracting invoice line items...")
    df_invoice = process_invoices(invoices_folder, data_folder)

    if df_invoice.empty:
        print("[WARN] No invoice data extracted. Stopping pipeline.")
        return pd.DataFrame(), pd.DataFrame()

    # 2) Match & verify with supporting docs
    print("[INFO] Step 2/3: Matching and verifying against supporting documents...")
    df_verification = match_and_verify(df_invoice, supporting_docs_folder, data_folder)

    # 3) Apply FX rates
    print("[INFO] Step 3/3: Applying FX rates...")
    df_invoice_fx = apply_fx_rates(df_invoice, data_folder)

    print("[INFO] Validation pipeline completed.")
    return df_invoice_fx, df_verification


# Optional: simple CLI runner
if __name__ == "__main__":
    invoices_folder = "invoices"
    supporting_docs_folder = "supporting_docs"
    data_folder = "data"

    df_inv, df_ver = run_validation(invoices_folder, supporting_docs_folder, data_folder)

    print("\n[SUMMARY] Invoices with FX conversion:")
    print(df_inv.head())

    print("\n[SUMMARY] Verification results:")
    print(df_ver.head())

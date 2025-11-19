from src.validator import run_validation
from src.report_generator import generate_report
import os

if __name__ == "__main__":
    invoices_folder = "invoices/"
    supporting_docs_folder = "supporting_docs/"
    data_folder = "data/"
    output_path = "data/validation_report.xlsx"

    print("\n=== Invoice Validation Pipeline Started ===")

    # Ensure necessary folders exist
    os.makedirs(data_folder, exist_ok=True)

    # Run the complete extraction → verification → FX → combination pipeline
    df_invoice, df_verification = run_validation(
        invoices_folder,
        supporting_docs_folder,
        data_folder
    )

    # If invoice dataframe is empty, stop the process
    if df_invoice.empty:
        print("[ERROR] No invoice data extracted. Report not generated.")
        print("=== Pipeline Ended ===")
    else:
        print("[INFO] Generating final Excel report...")
        generate_report(df_invoice, df_verification, output_path)
        print("\n=== Pipeline Completed Successfully ===")
        print(f"Report saved to: {output_path}")

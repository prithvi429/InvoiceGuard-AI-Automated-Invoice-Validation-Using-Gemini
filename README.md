# InvoiceGuard-AI — Automated Invoice Validation (using Gemini)

InvoiceGuard-AI is a starter project for automated invoice extraction, validation, and reconciliation. It provides a modular layout and stub modules you can extend to integrate OCR, vision, and LLM services (for example Google Gemini Vision/Text or other providers).

The repository focuses on separating concerns: extraction, matching, validation, exchange-rate lookups, and report generation. The included `src` modules are placeholders to help you get started.

**Status:** Starter skeleton (stub modules included). Replace stubs with your implementation.

**Recommended Python version:** 3.8+

**Table of Contents**
- Project structure
- Quick start
- How the modules fit together
- Development notes
- License

**Project structure**

Root layout (created by the scaffolding step):

```
data/
invoices/
supporting_docs/
src/
	├── extract_invoice.py
	├── extract_support_doc.py
	├── matcher.py
	├── validator.py
	├── fx_rate_service.py
	└── report_generator.py
config/
requirements.txt
README.md
```

- `data/`: any datasets, example inputs, or intermediate data.
- `invoices/`: drop invoice files (PDFs, images) here for processing.
- `supporting_docs/`: supporting documents related to invoices (purchase orders, receipts).
- `src/`: Python modules for extraction, matching, validation, FX rates, and report generation.
- `config/`: configuration files, secrets (use `.env` or a secrets manager), and API keys.

**Quick start (Windows PowerShell)**

1. Create a virtual environment and activate it (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Run a stub module to verify the layout (examples):

```powershell
python .\src\extract_invoice.py
python .\src\extract_support_doc.py
```

4. (Optional) Implement a runner script `src/main.py` to orchestrate extraction → matching → validation → reporting.

**How the modules fit together**

- `extract_invoice.py`: parse invoice files and return structured data (invoice number, date, vendor, line items, totals).
- `extract_support_doc.py`: parse supporting documents (POs, delivery notes) and return structured fields for reconciliation.
- `matcher.py`: match invoice records to supporting documents using keys like PO number, amounts, vendor.
- `validator.py`: apply business rules and data checks (tax rates, amounts, duplicates) and emit validation reports.
- `fx_rate_service.py`: resolve currency conversion rates when invoices and POs use different currencies.
- `report_generator.py`: create human-readable or machine-readable validation reports (CSV, JSON, PDF).

**Development notes & tips**

- Protect API keys: store them in `config/.env` or use a secret manager; do not commit keys.
- For OCR, consider `pdfminer.six` for text PDFs and `pytesseract`/Vision APIs for images.
- For LLM/vision integration, implement a dedicated adapter that converts your extraction problem into calls to Gemini (or other services), then normalise outputs to structured fields.
- Add tests for extraction and validation logic; create a `tests/` folder and use `pytest`.

**Next steps (suggested)**

- Implement `src/extract_invoice.py` to parse sample invoices from `invoices/`.
- Add `src/main.py` to run an end-to-end flow over files in `invoices/` and output reports to `data/reports/`.
- Add example sample files (redacted) to `data/` or `invoices/` for integration testing.

**License**

This project includes a `LICENSE` file at the repository root. Follow the terms specified there.

---

If you want, I can now:
- create a simple `src/main.py` runner that demonstrates an end-to-end flow using the stub modules, or
- implement one of the stub modules (for example `extract_invoice.py`) to parse a simple PDF/image sample.
Which would you like next?


import pandas as pd
import os
import requests
import json

# ---- Load config ----
with open('config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

base_currency = config.get('base_currency', 'USD')
rates_file = config.get('rates_file', 'data/fx_rates.csv')


# ---- Load local FX rates ----
def load_rates(path: str | None = None) -> dict:
    """
    Load FX rates from a CSV file.
    Expected columns: from_currency, to_currency, rate

    Returns:
        dict with keys (from_currency, to_currency) -> rate
        or {} if file not found / invalid.
    """
    path = path or rates_file

    if not os.path.exists(path):
        print(f"[WARN] FX rates file not found: {path}")
        return {}

    try:
        df_rates = pd.read_csv(path)
        required_cols = {"from_currency", "to_currency", "rate"}
        if not required_cols.issubset(df_rates.columns):
            print(f"[WARN] FX rates file missing required columns in: {path}")
            return {}

        rates_dict = {
            (str(row["from_currency"]).upper(), str(row["to_currency"]).upper()): float(row["rate"])
            for _, row in df_rates.iterrows()
        }
        print(f"[INFO] Loaded {len(rates_dict)} FX rates from: {path}")
        return rates_dict

    except Exception as e:
        print(f"[ERROR] Failed to load FX rates from {path}: {e}")
        return {}


# ---- Helper: get rate, with local & API fallback ----
def get_rate(from_currency: str,
             to_currency: str,
             rates_dict: dict | None = None,
             api_cache: dict | None = None) -> float:
    """
    Get FX rate from from_currency to to_currency.

    Priority:
    1) Local rates_dict
    2) External API (cached per from_currency)
    3) Fallback 1.0 on error

    Returns:
        float rate
    """
    if not from_currency or not to_currency:
        print(f"[WARN] Empty currency code: {from_currency} -> {to_currency}, using rate 1.0")
        return 1.0

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    rates_dict = rates_dict or {}
    api_cache = api_cache or {}

    # 1) Local file rate
    if (from_currency, to_currency) in rates_dict:
        return rates_dict[(from_currency, to_currency)]

    # 2) Try API (with simple caching by from_currency)
    try:
        if from_currency not in api_cache:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            resp = requests.get(url, timeout=5)
            if resp.ok:
                api_cache[from_currency] = resp.json().get("rates", {})
            else:
                print(f"[WARN] FX API request failed for base {from_currency}: HTTP {resp.status_code}")
                api_cache[from_currency] = {}

        rates_map = api_cache.get(from_currency, {})
        rate = rates_map.get(to_currency)
        if rate is not None:
            return float(rate)
        else:
            print(f"[WARN] No FX rate {from_currency} -> {to_currency} in API response, using 1.0")
            return 1.0

    except Exception as e:
        print(f"[ERROR] FX API error for {from_currency} -> {to_currency}: {e}")
        return 1.0


# ---- Helper: safe float ----
def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---- Apply FX to invoice DataFrame ----
def apply_fx_rates(df_invoice: pd.DataFrame, data_folder: str) -> pd.DataFrame:
    """
    Adds a 'converted_non_vat_value' column to df_invoice,
    converting total_non_vat_value to base_currency using FX rates.

    - Uses local CSV rates if available.
    - Falls back to online API if needed.
    - Falls back to 1.0 if everything fails.

    Saves result to converted_invoices.csv in data_folder.
    """
    os.makedirs(data_folder, exist_ok=True)

    rates_dict = load_rates()
    api_cache = {}

    def _convert_row(row):
        currency = row.get("currency")
        amount = _safe_float(row.get("total_non_vat_value"))

        if amount is None:
            print(f"[WARN] Cannot convert non-numeric amount: {row.get('total_non_vat_value')}")
            return None

        if not currency:
            print(f"[WARN] Missing currency for row, using base currency ({base_currency}) as-is.")
            return amount

        if currency.upper() == base_currency.upper():
            return amount

        rate = get_rate(currency, base_currency, rates_dict, api_cache)
        return amount * rate

    df_invoice = df_invoice.copy()
    df_invoice["converted_non_vat_value"] = df_invoice.apply(_convert_row, axis=1)

    output_path = os.path.join(data_folder, "converted_invoices.csv")
    df_invoice.to_csv(output_path, index=False, encoding="utf-8")
    print(f"[INFO] Saved FX-converted invoices to: {output_path}")

    return df_invoice

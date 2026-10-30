"""IFSC first-4-letters -> bank name, for the ifsc_bank_mismatch anomaly check (spec 5.7.9)."""

IFSC_PREFIX_TO_BANK: dict[str, str] = {
    "SBIN": "State Bank of India",
    "HDFC": "HDFC Bank",
    "ICIC": "ICICI Bank",
    "PUNB": "Punjab National Bank",
    "UBIN": "Union Bank of India",
    "CNRB": "Canara Bank",
    "BARB": "Bank of Baroda",
    "UTIB": "Axis Bank",
    "KKBK": "Kotak Mahindra Bank",
    "IDIB": "Indian Bank",
}

IFSC_PATTERN = r"^[A-Z]{4}0[A-Z0-9]{6}$"

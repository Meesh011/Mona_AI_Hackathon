import os
import pandas as pd

from invoice_processor import extract_text
from classifier import classify_invoice
from database import save_results

INVOICE_FOLDER = "invoices"

results = []

# ── FIX 6: Sort files for consistent output order ────────────────────────────
# os.listdir() returns files in arbitrary filesystem order.
for file in sorted(os.listdir(INVOICE_FOLDER)):

    # ── FIX 7: Skip the manifest CSV — it is not an invoice ──────────────────
    if file == "00_manifest.csv":
        continue

    path = os.path.join(INVOICE_FOLDER, file)

    text = extract_text(path)

    department = classify_invoice(text)

    results.append({
        "invoice": file,
        "department": department,
        "status": "Pending Approval"
    })

# ── FIX 8: Ensure output directory exists before saving ──────────────────────
os.makedirs("output", exist_ok=True)

save_results(results)

df = pd.DataFrame(results)
print(df)

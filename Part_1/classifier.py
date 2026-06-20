# ── FIX 4: Classifier keyword corrections ────────────────────────────────────
#
# Problems in original:
#  a) "adobe" was under IT — Adobe Creative Cloud is a Marketing/Design tool
#  b) "consulting" / "brightpath" were under Finance — it's an Operations cost
#  c) "bürobedarf" keyword used umlaut but OCR/docx text often gives "buerobedarf"
#     → added both spellings + "schmidt" (vendor name visible in extracted text)
#  d) "hotel" / "adlon" were under HR/Admin which is correct, but the department
#     name is now "HR / Travel" to be more descriptive
#  e) No tie-break: when all scores = 0 the old code returned "IT" (first key).
#     Fixed by returning "Unclassified" when nothing matches.

TEAM_RULES = {

    "IT": [
        "microsoft",
        "aws",
        "amazon web services",
        "cloud",
        "software",
        "license",
        "telekom",
        "internet",
        "dell",
        "latitude",              # Dell laptop model visible in invoice
        "hardware",
        "server",
        "network",
    ],

    "Facilities": [
        "stadtwerke",
        "gas",
        "e.on",
        "energie",
        "electricity",
        "strom",                 # German for electricity
        "wasser",                # water
        "wärme",                 # heating
    ],

    "HR / Travel": [
        "hotel",
        "adlon",
        "kempinski",
        "accommodation",
        "übernachtung",          # German for overnight stay
        "reise",                 # travel
        "frühstück",             # breakfast (appears on hotel invoices)
    ],

    "Operations": [
        "consulting",
        "brightpath",
        "strategy",
        "bürobedarf",            # German umlaut version
        "buerobedarf",           # ASCII fallback (OCR often strips umlauts)
        "office supplies",
        "stationery",
        "kopierpapier",          # copy paper
        "toner",
        "aktenordner",           # binder/folder
    ],

    "Marketing": [
        "adobe",
        "creative cloud",
        "creativecloud",
        "stock",                 # Adobe Stock
        "acrobat",
        "design",
    ],
}


def classify_invoice(text):
    text = text.lower()

    scores = {}

    for team, keywords in TEAM_RULES.items():
        scores[team] = 0
        for keyword in keywords:
            if keyword in text:
                scores[team] += 1

    best_score = max(scores.values())

    # ── FIX 5: Tie / zero-score fallback ─────────────────────────────────────
    # Original: max() on a dict of all-zeros silently returned the first key
    # (which happened to be "IT"), causing every unmatched invoice to be
    # labelled IT. Now returns "Unclassified" when nothing matches.
    if best_score == 0:
        return "Unclassified"

    return max(scores, key=scores.get)

from datetime import date, datetime, timedelta

INCLUDE_HOLY_SPIRIT = False  # Αγίου Πνεύματος: αλλάζει σε True αν αποφασίσεις ότι μετράει

def orthodox_easter(year):
    # Υπολογίζει την Κυριακή του Ορθόδοξου Πάσχα για οποιοδήποτε έτος
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    return date(year, month, day) + timedelta(days=13)

def greek_holidays(year):
    # Επιστρέφει το σύνολο των πανελλαδικών αργιών του έτους
    e = orthodox_easter(year)
    h = {date(year, 1, 1), date(year, 1, 6), date(year, 3, 25), date(year, 5, 1),
         date(year, 8, 15), date(year, 10, 28), date(year, 12, 25), date(year, 12, 26),
         e - timedelta(days=48), e - timedelta(days=2), e + timedelta(days=1)}
    if INCLUDE_HOLY_SPIRIT:
        h.add(e + timedelta(days=50))
    return h

def is_workday(d, holidays):
    return d.weekday() < 5 and d not in holidays

def deadline(product_delivery, today):
    # Product Delivery Date μείον 3 εργάσιμες, όχι πριν από σήμερα, πάντα 01:00
    at_one = lambda d: datetime.combine(d, datetime.min.time().replace(hour=1))
    if product_delivery is None:
        return at_one(today)
    holidays = greek_holidays(product_delivery.year) | greek_holidays(product_delivery.year - 1)
    d, counted = product_delivery, 0
    while counted < 3:
        d -= timedelta(days=1)
        if is_workday(d, holidays):
            counted += 1
    return at_one(max(d, today))

def build_title(wo, service, pod):
    # WO / POD μόνο όταν η υπηρεσία περιέχει ΥΔΕ και υπάρχει POD
    if "ΥΔΕ" in (service or "") and (pod or "").strip():
        return f"{wo} / {pod.strip()}"
    return wo

def build_notes(f):
    # Σημειώσεις εκκρεμότητας με τη συμφωνημένη σειρά, περικοπή στους 1000 χαρακτήρες
    order = ["OTP", "Product", "Product Delivery Date", "Appointment Date",
             "Work Order Summary", "Survey Response", "Change Status Comments"]
    text = "\n".join(f"{k}: {f.get(k, '') or ''}" for k in order)
    return text[:1000]

def split_name(name):
    # Χωρισμός Contact Name σε όνομα / επώνυμο
    w = (name or "").split()
    if not w:
        raise ValueError("Κενό Contact Name")
    if len(w) == 1:
        return w[0], w[0]
    k = len(w) // 2
    return " ".join(w[:k]), " ".join(w[k:])

def customer_phones(mobile, landline):
    # Τηλέφωνο αναζήτησης και τηλέφωνα αποθήκευσης· 6900000000 μόνο για νέο πελάτη
    mobile, landline = (mobile or "").strip(), (landline or "").strip()
    search = mobile or landline or None
    if not mobile and not landline:
        return None, ["6900000000"]
    return search, [p for p in (mobile, landline) if p]

import unicodedata

_LATIN_TO_GREEK = str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ")

def norm(text):
    # Κανονικοποίηση για σύγκριση: κεφαλαία, χωρίς τόνους, ενιαία κενά, ελληνικά ομοιόμορφα
    t = unicodedata.normalize("NFD", text or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = " ".join(t.upper().split())
    return t.translate(_LATIN_TO_GREEK)

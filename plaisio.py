import re, keyring

from playwright.sync_api import sync_playwright
from datetime import date

def parse_pdd(text):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", (text or "").strip())
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None

URL = "https://serviceapp.plaisio.gr"
PROFILE = r"C:\Users\kokka\kotsovolos-domx-profile"

def login_plaisio(page):
    page.goto(URL)
    email = page.get_by_role("textbox", name=re.compile("email", re.I))
    if email.count() and email.first.is_visible():
        email.first.fill(keyring.get_password("plaisio", "username"))
        page.get_by_role("button", name="Επόμενο").click()
        pwd = page.get_by_role("textbox", name=re.compile("Κωδικός"))
        pwd.first.wait_for(timeout=15000)
        pwd.first.fill(keyring.get_password("plaisio", "password"))
        page.locator('form[novalidate] button[type="submit"]').click()
    page.get_by_text("Ανοιχτά (", exact=False).first.wait_for(timeout=60000)

def phones(raw):
    digits = re.sub(r"\D", "", raw)
    nums = [digits[i:i+10] for i in range(0, len(digits), 10) if len(digits[i:i+10]) == 10]
    out = []
    for n in nums:
        if n not in out:
            out.append(n)
    return out

def read_open(page):
    page.get_by_text("Ανοιχτά (", exact=False).first.click()
    page.wait_for_timeout(1500)
    buttons = page.get_by_role("button", name="Λεπτομέρειες")
    n = buttons.count()
    print(f"Κάρτες στα Ανοιχτά: {n}")
    rows = []
    for i in range(n):
        btn = buttons.nth(i)
        btn.scroll_into_view_if_needed()
        btn.click()
        details = page.get_by_text("Στοιχεία Ραντεβού").locator("visible=true")
        try:
            details.first.wait_for(timeout=5000)
        except Exception:
            btn.click()
            details.first.wait_for(timeout=5000)
        card = details.first.locator("xpath=ancestor::*[contains(., 'Αρ. Παραγγελίας')][1]")
        txt = card.inner_text()
        head = {}
        for label in ["Αρ. Παραγγελίας", "Πλήρες Όνομα", "Διεύθυνση", "Ημ/νία Ανάθεσης", "Κινητό"]:
            m = re.search(re.escape(label) + r"\s*\n\s*(.+)", txt)
            head[label] = m.group(1).strip() if m else ""
        for block in re.split(r"Στοιχεία Ραντεβού", txt)[1:]:
            def g(lbl):
                m = re.search(re.escape(lbl) + r":\s*(.+)", block)
                v = m.group(1).strip() if m else ""
                return "" if v in ("-", "- -") else v
            rows.append({**head,
                "Κωδικός": g("Κωδικός"), "Ημ/νία Ραντεβού": g("Ημ/νία Ραντεβού"),
                "Κατάσταση": g("Κατάσταση"), "Σχόλια": g("Σχόλια"),
                "Προϊόν": g("Προϊόν"), "Ημ/νία Παράδοσης": g("Ημ/νία Παράδοσης"),
                "Υπηρεσία": g("Υπηρεσία"), "Λειτουργική": g("Λειτουργική"),
                "Τηλέφωνα": phones(head["Κινητό"])})
    return rows

NOTE_FIELDS = ["Ημ/νία Ραντεβού", "Ημ/νία Ανάθεσης", "Ημ/νία Παράδοσης", "Προϊόν",
               "Υπηρεσία", "Κατάσταση", "Σχόλια", "Λειτουργική", "Αρ. Παραγγελίας"]

def service_name(raw):
    return re.sub(r"^\s*\d+\s*-\s*", "", raw).strip()

def build_notes(r):
    text = "\n".join(f"{k}: {r.get(k, '')}" for k in NOTE_FIELDS)
    return text[:1000]

def split_address(addr):
    parts = [p.strip() for p in addr.split(",")]
    if len(parts) >= 3:
        return ", ".join(parts[:-2]), parts[-2], parts[-1]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return addr.strip(), "", ""

def to_wo(r):
    street, city, pc = split_address(r["Διεύθυνση"])
    ph = r["Τηλέφωνα"]
    return {
        "Work Order Number": r["Κωδικός"],
        "Service": service_name(r["Υπηρεσία"]),
        "Contact Name": r["Πλήρες Όνομα"],
        "Contact Mobile Phone": ph[0] if len(ph) > 0 else "",
        "Contact Phone Number": ph[1] if len(ph) > 1 else "",
        "POD": "",
        "Product Delivery Date": r["Ημ/νία Παράδοσης"],
        "Street 1": street, "Street 2": "", "Street 3": "",
        "City": city, "Postal Code": pc,
        "_pdd": parse_pdd(r["Ημ/νία Παράδοσης"]),
        "_source": "plaisio",
        "_notes": build_notes(r),
    }

def _row(code, order, name, phones_raw, addr, pdd, service, product):
    return {"Αρ. Παραγγελίας": order, "Πλήρες Όνομα": name, "Διεύθυνση": addr,
            "Ημ/νία Ανάθεσης": "05/11/2026", "Κινητό": phones_raw,
            "Κωδικός": code, "Ημ/νία Ραντεβού": "", "Κατάσταση": "Open", "Σχόλια": "ΤΕΣΤ ΑΥΤΟΜΑΤΙΣΜΟΥ",
            "Προϊόν": product, "Ημ/νία Παράδοσης": pdd, "Υπηρεσία": service,
            "Λειτουργική": "Όχι", "Τηλέφωνα": phones(phones_raw)}

TEST_ROWS = [
    _row("TESTPL0001-10-1", "TESTPL0001", "ΤΕΣΤ ΠΛΑΙΣΙΟ ΕΝΑ", "6900000021/6900000021",
         "28ης Οκτωβρίου 157, Νέα Πέραμος, 19006", "10/11/2026",
         "3741176 - Σύνδεση απορροφητήρα τζάκι", ""),
    _row("TESTPL0002-10-1", "TESTPL0002", "ΤΕΣΤΠΛΑΙΣΙΟ", "6900000022/2296000022",
         "ΤΕΣΤ ΟΔΟΣ 999, ΤΕΣΤΟΥΠΟΛΗ, 99999", "03/11/2026",
         "3854418 - Σύνδεση Πλυντηρίου Πιάτων", "9999991 - ΤΕΣΤ Πλυντήριο Πιάτων"),
    _row("TESTPL0003-10-1", "TESTPL0003", "ΤΕΣΤ ΠΛΑΙΣΙΟ", "6900000023/6900000024",
         "Ερμού 1, Αθήνα, 10563", "",
         "3741184 - Αποσύνδεση απορροφητήρα", "9999992 - ΤΕΣΤ Απορροφητήρας"),
    _row("TESTPL0001-10-2", "TESTPL0001", "ΤΕΣΤ ΠΛΑΙΣΙΟ ΕΝΑ", "6900000021/6900000021",
         "28ης Οκτωβρίου 157, Νέα Πέραμος, 19006", "10/11/2026",
         "3741184 - Αποσύνδεση απορροφητήρα", ""),
    _row("TESTPL0005-10-1", "TESTPL0005", "ΤΕΣΤ ΠΛΑΙΣΙΟ ΠΕΝΤΕ", "6900000025/6900000025",
         "28ης Οκτωβρίου 157, Νέα Πέραμος, 19006", "12/11/2026",
         "3741176 - Σύνδεση απορροφητήρα τζάκι", ""),
]

if __name__ == "__main__":
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=False, no_viewport=True)
        page = ctx.new_page()
        login_plaisio(page)
        page.get_by_text("Ανοιχτά (", exact=False).first.click()
        page.wait_for_timeout(1500)
        for r in read_open(page):
            w = to_wo(r)
            print("\n=== ", w["Work Order Number"], "|", w["Service"], "|", w["_pdd"])
            for k, v in w.items():
                if k != "_notes":
                    print(f"  {k}: {v!r}")
            print("  _notes:\n" + w["_notes"])
        input("Enter για κλείσιμο...")
        ctx.close()
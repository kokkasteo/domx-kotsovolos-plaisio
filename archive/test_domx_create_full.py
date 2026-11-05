import re
from datetime import date
from playwright.sync_api import sync_playwright
from rules import deadline, build_title, build_notes, norm, split_name, customer_phones

# --- Δεδομένα δοκιμής (όλα στο όνομα Θεόδωρου Κόκκα) ---
WO = "WOTEST0003"
POD = ""                                   # χωρίς POD -> τίτλος μόνο WO
SERVICE = "Κ-ΨΥΚΤΙΚΗ ΕΓΚ AC ΤΟΙΧ 9-15 BTU"
CONTACT_NAME = "ΔΟΚΙΜΗ ΑΥΤΟΜΑΤΙΣΜΟΥ ΚΟΚΚΑΣ"
PHONE = "6900000000"                        # κινητό: κενό στην πηγή
LANDLINE = ""                               # σταθερό: κενό στην πηγή
STREET, CITY, ZIP = "ΔΙΓΕΝΗ ΑΚΡΙΤΑ 4", "Νέα Πέραμος", "19006"
OWNER = "Έφη Τσιατσιάνη"
FIELDS = {"OTP": "TEST", "Product": "Δοκιμαστικό προϊόν", "Product Delivery Date": "",
          "Appointment Date": "", "Work Order Summary": "Αυτόματη δοκιμή νέου πελάτη/εγκατάστασης",
          "Survey Response": "", "Change Status Comments": ""}

TITLE = build_title(WO, SERVICE, POD)
NOTES = build_notes(FIELDS)
DUE = deadline(None, date.today())           # σήμερα 01:00


def next_button(page, step):
    # Το ΕΠΟΜΕΝΟ του συγκεκριμένου βήματος: 1 -> πρώτο, 2 -> δεύτερο
    return page.get_by_role("button", name="ΕΠΟΜΕΝΟ").nth(step - 1)


def clock_pick(page, value):
    # Κλικ σε αριθμό του ρολογιού (ώρα ή λεπτά)
    page.get_by_role("menu").get_by_text(value, exact=True).click()


def fill_task_step(page):
    page.get_by_role("textbox", name="Τίτλος").click()
    page.get_by_role("textbox", name="Τίτλος").fill(TITLE)

    svc = page.get_by_role("textbox", name="Σύνδεση με τύπο υπηρεσίας")
    svc.click()
    svc.fill(SERVICE)                              # φιλτράρει τη λίστα, όπως χειροκίνητα
    page.wait_for_timeout(1200)
    options = page.get_by_role("option")
    texts = options.all_inner_texts()
    matches = [i for i, t in enumerate(texts) if norm(t) == norm(SERVICE)]
    distinct = {texts[i].strip() for i in matches}
    print(f"Επιλογές μετά το φίλτρο: {len(texts)}, ταυτίσεις: {len(matches)}, διακριτές: {len(distinct)}")
    if len(distinct) != 1:
        print("Κοντινές:", [t for t in texts][:5])
        raise RuntimeError("Η υπηρεσία δεν βρέθηκε μονοσήμαντα — WO για έλεγχο")
    options.nth(matches[0]).click()
    page.keyboard.press("Escape")

    owner = page.get_by_role("textbox", name="Χρήστης / Συνεργάτης").last
    owner.click()
    page.get_by_role("option").filter(has_text=OWNER).first.click()
    page.keyboard.press("Escape")

    # Αποεπιλογή «Όλη την ημέρα» -> εμφανίζεται πεδίο Ώρα
    page.locator(".v-input--selection-controls__ripple").first.click()
    time_btn = page.get_by_role("button", name="Ώρα")
    time_btn.wait_for(state="visible")
    time_btn.click()
    clock_pick(page, str(DUE.hour))        # "1"
    clock_pick(page, DUE.strftime("%M"))                                 # "00"
    page.get_by_role("menu").get_by_role("button").last.click()   # το OK του ρολογιού
    page.get_by_role("menu").wait_for(state="hidden")

    notes = page.get_by_role("textbox", name="Σημειώσεις εκκρεμότητας")
    notes.click()
    notes.fill(NOTES)

    print("Τίτλος:", TITLE)
    print("Προθεσμία:", DUE.strftime("%d/%m/%Y %H:%M"))


def pick_customer(page):
    search_phone, phones = customer_phones("", LANDLINE)       # None, ["6900000000"]
    if search_phone:
        box = page.get_by_role("textbox", name="Πελάτης", exact=True)
        box.wait_for(state="visible")
        page.wait_for_function("el => !el.disabled", arg=box.element_handle(), timeout=15000)
        box.click(); box.fill(search_phone); page.wait_for_timeout(1500)
        n = page.get_by_role("option").count()
        print(f"Αναζήτηση {search_phone}: {n} αποτελέσματα")
        if n == 1:
            page.get_by_role("option").first.click(); return "existing"
        if n > 1:
            raise RuntimeError("Πολλαπλοί πελάτες — WO για έλεγχο")
    # Νέος πελάτης
    page.get_by_text("Νέος πελάτης;").click()
    first, last = split_name(CONTACT_NAME)
    page.get_by_role("textbox", name="Όνομα").fill(first)
    page.get_by_role("textbox", name="Επώνυμο").fill(last)
    page.get_by_role("textbox", name="Τηλέφωνο").first.fill(phones[0])
    if len(phones) > 1:
        page.locator(".v-btn.v-btn--icon.v-btn--round").filter(has_text="").last.click()
        page.get_by_role("textbox", name="Τηλέφωνο").nth(1).fill(phones[1])
    print(f"Νέος πελάτης: {first} / {last}, τηλέφωνα {phones}")
    return "new"


def pick_installation(page):
    # Περιμένουμε να εμφανιστεί η φόρμα εγκατάστασης (Περιγραφή)
    page.get_by_role("textbox", name="Περιγραφή").wait_for(state="visible")
    toggle = page.get_by_text("Νέα εγκατάσταση;")
    if toggle.count() and toggle.first.is_visible():
        toggle.first.click()                  # υπάρχων πελάτης: ανοίγουμε νέα εγκατάσταση
        page.wait_for_timeout(500)
    else:
        print("Νέος πελάτης: η φόρμα νέας εγκατάστασης εμφανίζεται απευθείας")
    addr = page.get_by_role("textbox", name="Διεύθυνση")
    addr.click()
    addr.type(f"{STREET} {CITY}", delay=80)                 # γράμμα-γράμμα για το Google
    page.wait_for_timeout(2500)
    suggestions = page.locator(".pac-item")                 # λίστα Google Places
    n = suggestions.count()
    texts = suggestions.all_inner_texts()
    print(f"Προτάσεις Google: {n}", texts[:5])
    good = [i for i, t in enumerate(texts) if norm(CITY) in norm(t)]
    if len(good) == 0:
        raise RuntimeError("Καμία πρόταση με σωστή περιοχή — εναλλακτική διεύθυνση (δεν υλοποιήθηκε ακόμη)")
    # Επιλογή με πληκτρολόγιο: η λίστα Google κλείνει αν μετακινηθεί το ποντίκι
    for _ in range(good[0] + 1):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    def value_of(label):
        page.get_by_role("textbox", name="Περιγραφή").fill(WO)
        # Διαβάζει την τιμή του input που ακολουθεί τη συγκεκριμένη ετικέτα, όποιος κι αν είναι ο τύπος του
        return page.locator(f"label:has-text('{label}')").last.evaluate(
            "l => { const i = document.getElementById(l.htmlFor); return i ? i.value : ''; }")
    lat, lon = value_of("Γεωγραφικό πλάτος"), value_of("Γεωγραφικό μήκος")
    area, zipc = value_of("Περιοχή"), value_of("Ταχυδρομικός κώδικας")
    print(f"Στίγμα: {lat}, {lon} | Περιοχή: {area} | ΤΚ: {zipc}")
    if lat.startswith("37,98381") or zipc.replace(" ", "") != ZIP:
        raise RuntimeError("Το στίγμα δεν επιβεβαιώθηκε — εναλλακτική διεύθυνση (δεν υλοποιήθηκε ακόμη)")


def verify_saved(page):
    # Επιβεβαίωση: αναζήτηση του τίτλου στις Εκκρεμότητες, εύρος 2024–2031
    page.goto("https://portal.business.domx.online/tasks"
              "?date_from=2024-01-01T00%3A00%3A00.000Z&date_to=2031-12-31T23%3A59%3A59.999Z"
              f"&search={WO}")
    page.wait_for_timeout(3000)
    found = page.get_by_text(TITLE, exact=False).count()
    print("ΕΠΙΒΕΒΑΙΩΣΗ ΑΠΟΘΗΚΕΥΣΗΣ:", "ΒΡΕΘΗΚΕ" if found else "ΔΕΝ ΒΡΕΘΗΚΕ", f"({found})")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://portal.business.domx.online/")
    print("Συνδέσου στο domx, μείνε στο dashboard και πάτησε Resume.")
    page.pause()

    # Έλεγχος διπλοτύπου ΠΡΙΝ από οποιαδήποτε καταχώριση
    page.goto("https://portal.business.domx.online/tasks"
              "?date_from=2024-01-01T00%3A00%3A00.000Z&date_to=2031-12-31T23%3A59%3A59.999Z"
              f"&search={WO}")
    page.wait_for_timeout(3000)
    if page.get_by_text(WO, exact=False).count() > 0:
        print(f"ΠΑΡΑΛΕΙΨΗ: το {WO} υπάρχει ήδη στο domx. Καμία καταχώριση.")
        page.pause()
        browser.close()
        raise SystemExit
    page.goto("https://portal.business.domx.online/dashboard")
    page.get_by_role("button", name="ΓΡΗΓΟΡΗ ΠΡΟΣΘΗΚΗ").wait_for(state="visible")
    
    page.get_by_role("button", name="ΓΡΗΓΟΡΗ ΠΡΟΣΘΗΚΗ").click()
    page.get_by_role("button", name="ΕΚΚΡΕΜΟΤΗΤΑ", exact=True).click()
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="visible")

    try:
        fill_task_step(page)
        next_button(page, 1).click()
        pick_customer(page)
        next_button(page, 2).click()
        pick_installation(page)
    except Exception as e:
        print("ΣΦΑΛΜΑ:", type(e).__name__, str(e)[:200])
        page.screenshot(path="debug_error.png", full_page=True)
        print("Ο browser μένει ανοιχτός. Κοίτα τη φόρμα, βγάλε screenshot, μετά Resume.")
        page.pause()
        raise

    print("\nΕΛΕΓΞΕ ΤΗ ΦΟΡΜΑ. Αν όλα σωστά, πάτησε Resume και θα πατηθεί ΤΕΛΟΣ.")
    print("Αν κάτι είναι λάθος, κλείσε τον wizard με Χ ΠΡΙΝ πατήσεις Resume.")
    page.pause()

    end = page.get_by_role("button", name="ΤΕΛΟΣ")
    if end.count() and end.is_visible():
        end.click()
        page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden")
        print("Πατήθηκε ΤΕΛΟΣ, ο wizard έκλεισε.")
        verify_saved(page)
    else:
        print("Ο wizard είχε κλείσει — δεν έγινε καταχώριση.")

    page.pause()
    browser.close()
import re
from datetime import date
from playwright.sync_api import sync_playwright
from rules import deadline, build_title, build_notes, norm

# --- Δεδομένα δοκιμής (όλα στο όνομα Θεόδωρου Κόκκα) ---
WO = "WOTEST0001"
POD = "11700000001"
SERVICE = "K-BUSINESS ΥΔΕ ΕΩΣ 200 ΤΜ"
OWNER = "Έφη Τσιατσιάνη"
PHONE = "6949205010"
FIELDS = {"OTP": "TEST", "Product": "Δοκιμαστικό προϊόν", "Product Delivery Date": "",
          "Appointment Date": "", "Work Order Summary": "Αυτόματη δοκιμή καταχώρισης",
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
    box = page.get_by_role("textbox", name="Πελάτης", exact=True)
    box.wait_for(state="visible")
    page.wait_for_function("el => !el.disabled", arg=box.element_handle(), timeout=15000)
    box.click()
    box.fill(PHONE)
    page.wait_for_timeout(1500)
    options = page.get_by_role("option")
    n = options.count()
    if n != 1:
        raise RuntimeError(f"Αναμενόταν 1 πελάτης, βρέθηκαν {n}")
    print("Πελάτης:", options.first.inner_text().strip())
    options.first.click()


def pick_installation(page):
    page.get_by_text("Νέα εγκατάσταση;").wait_for(state="visible")
    inst = page.get_by_role("textbox", name="Εγκατάσταση", exact=True)
    page.wait_for_function("el => !el.disabled", arg=inst.element_handle(), timeout=15000)
    print("Εγκατάσταση:", inst.input_value())


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

    fill_task_step(page)
    next_button(page, 1).click()
    pick_customer(page)
    next_button(page, 2).click()
    pick_installation(page)

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
import sys
from datetime import date
from playwright.sync_api import sync_playwright
from rules import deadline, build_title, build_notes, norm, split_name, customer_phones
from test_data import CASES

OWNER = "Έφη Τσιατσιάνη"
TASKS_URL = ("https://portal.business.domx.online/tasks"
             "?date_from=2024-01-01T00%3A00%3A00.000Z&date_to=2031-12-31T23%3A59%3A59.999Z&search=")
FALLBACK = {"street": "28ης Οκτωβρίου 157", "area": "Νέα Πέραμος", "zip": "19006",
            "lat": "38.011784", "lon": "23.434141",
            "note": "ΕΛΕΓΧΟΣ ΔΙΕΥΘΥΝΣΗΣ — χρησιμοποιήθηκε η διεύθυνση του καταστήματος."}


class Review(Exception):
    """Επιχειρησιακός λόγος: το WO μένει για έλεγχο, δεν είναι τεχνικό σφάλμα."""


def next_button(page, step):
    return page.get_by_role("button", name="ΕΠΟΜΕΝΟ").nth(step - 1)


def clock_pick(page, value):
    page.get_by_role("menu").get_by_text(value, exact=True).click()


def field_value(page, label):
    # Διαβάζει την τιμή του input που αντιστοιχεί στην ετικέτα (δουλεύει και για μη-textbox πεδία)
    return page.locator(f"label:has-text('{label}')").last.evaluate(
        "l => { const i = document.getElementById(l.htmlFor); return i ? i.value : ''; }")


def close_wizard(page):
    # Κλείσιμο με Χ χωρίς ΤΕΛΟΣ: στοχεύουμε το κουμπί που περιέχει το εικονίδιο mdi-window-close
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    x_btns = page.get_by_role("button").filter(has=page.locator("i.mdi-window-close"))
    visible = [x_btns.nth(i) for i in range(x_btns.count()) if x_btns.nth(i).is_visible()]
    print(f"Κουμπιά Χ με mdi-window-close: {x_btns.count()}, ορατά: {len(visible)}")
    if not visible:
        raise RuntimeError("Δεν βρέθηκε ορατό Χ του wizard")
    try:
        visible[0].click(timeout=5000)
    except Exception:
        print("Το Χ είναι εκτός ορατής περιοχής, κλικ μέσω JavaScript")
        visible[0].evaluate("b => b.click()")
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden", timeout=5000)
    print("Ο wizard έκλεισε με Χ.")


def fill_task_step(page, wo):
    title = build_title(wo["Work Order Number"], wo["Service"], wo["POD"])
    service = "Κ-" + wo["Service"]
    due = deadline(None, date.today())

    page.get_by_role("textbox", name="Τίτλος").click()
    page.get_by_role("textbox", name="Τίτλος").fill(title)

    svc = page.get_by_role("textbox", name="Σύνδεση με τύπο υπηρεσίας")
    svc.click(); svc.fill(service); page.wait_for_timeout(1200)
    options = page.get_by_role("option")
    texts = options.all_inner_texts()
    matches = [i for i, t in enumerate(texts) if norm(t) == norm(service)]
    distinct = {texts[i].strip() for i in matches}
    print(f"Υπηρεσία «{service}»: επιλογές {len(texts)}, διακριτές ταυτίσεις {len(distinct)}")
    if len(distinct) != 1:
        raise Review(f"Υπηρεσία δεν βρέθηκε μονοσήμαντα ({len(distinct)})")
    options.nth(matches[0]).click()
    page.keyboard.press("Escape")

    owner = page.get_by_role("textbox", name="Χρήστης / Συνεργάτης").last
    owner.click()
    page.get_by_role("option").filter(has_text=OWNER).first.click()
    page.keyboard.press("Escape")

    page.locator(".v-input--selection-controls__ripple").first.click()
    time_btn = page.get_by_role("button", name="Ώρα")
    time_btn.wait_for(state="visible"); time_btn.click()
    clock_pick(page, str(due.hour)); clock_pick(page, due.strftime("%M"))
    page.get_by_role("menu").get_by_role("button").last.click()
    page.get_by_role("menu").wait_for(state="hidden")

    notes = page.get_by_role("textbox", name="Σημειώσεις εκκρεμότητας")
    notes.click(); notes.fill(build_notes(wo))
    print("Τίτλος:", title, "| Προθεσμία:", due.strftime("%d/%m/%Y %H:%M"))
    return title


def pick_customer(page, wo):
    search_phone, phones = customer_phones(wo["Contact Mobile Phone"], wo["Contact Phone Number"])
    if search_phone:
        box = page.get_by_role("textbox", name="Πελάτης", exact=True)
        box.wait_for(state="visible")
        page.wait_for_function("el => !el.disabled", arg=box.element_handle(), timeout=15000)
        box.click(); box.fill(search_phone); page.wait_for_timeout(1500)
        opts = page.get_by_role("option").all_inner_texts()
        distinct = {t.strip() for t in opts}
        print(f"Αναζήτηση {search_phone}: {len(distinct)} πελάτες", list(distinct)[:3])
        if len(distinct) == 1:
            page.get_by_role("option").first.click(); return "existing"
        if len(distinct) > 1:
            raise Review(f"{len(distinct)} πελάτες με τηλέφωνο {search_phone}")
        page.keyboard.press("Escape")
    page.get_by_text("Νέος πελάτης;").click()
    first, last = split_name(wo["Contact Name"])
    page.get_by_role("textbox", name="Όνομα").fill(first)
    page.get_by_role("textbox", name="Επώνυμο").fill(last)
    page.get_by_role("textbox", name="Τηλέφωνο").first.fill(phones[0])
    if len(phones) > 1:
        # Δεύτερη γραμμή επαφής: το «+» είναι το εικονίδιο mdi-plus, χωρίς κείμενο
        page.get_by_role("button").filter(has=page.locator("i.mdi-plus")).last.click()
        page.get_by_role("textbox", name="Τηλέφωνο").nth(1).wait_for(state="visible")
        page.get_by_role("textbox", name="Τηλέφωνο").nth(1).fill(phones[1])
        # Τύπος 2ης γραμμής -> Σταθερό (dropdown "Τύπος επικοινωνίας", η δεύτερη εμφάνιση)
        page.get_by_role("textbox", name="Τύπος επικοινωνίας").nth(1).click()
        page.get_by_role("option").filter(has_text="Σταθερό").first.click()
        page.keyboard.press("Escape")
        types = [page.get_by_role("textbox", name="Τύπος επικοινωνίας").nth(i).input_value() for i in range(2)]
        print("Τύποι επαφών:", types)
        if types != ["Κινητό", "Σταθερό"]:
            raise RuntimeError(f"Λάθος τύποι επαφών {types}")
    print(f"Νέος πελάτης: {first} / {last}, τηλέφωνα {phones}")
    return "new"


def matches_address(option_text, wo):
    # Κριτήριο ταύτισης (προς επαλήθευση με δείγματα): οδός+αριθμός ΚΑΙ πόλη μέσα στο κείμενο της επιλογής
    t = norm(option_text)
    return norm(wo["Street 1"]) in t and norm(wo["City"]) in t


def google_address(page, wo):
    addr = page.get_by_role("textbox", name="Διεύθυνση")
    addr.click(); addr.fill("")
    addr.type(f"{wo['Street 1']} {wo['City']}", delay=80)
    page.wait_for_timeout(2500)
    texts = page.locator(".pac-item").all_inner_texts()
    print(f"Προτάσεις Google: {len(texts)}", texts[:3])
    good = [i for i, t in enumerate(texts) if norm(wo["City"]) in norm(t)]
    if not good:
        return False
    for _ in range(good[0] + 1):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    lat, zipc = field_value(page, "Γεωγραφικό πλάτος"), field_value(page, "Ταχυδρομικός κώδικας")
    print(f"Στίγμα: {lat}, {field_value(page, 'Γεωγραφικό μήκος')} | ΤΚ: {zipc}")
    return not lat.startswith("37,98381") and zipc.replace(" ", "") == wo["Postal Code"]


def fallback_address(page):
    # Εναλλακτική διεύθυνση καταστήματος + σημείωση ΜΟΝΟ στις σημειώσεις εγκατάστασης
    print("Εναλλακτική διεύθυνση καταστήματος")
    page.get_by_role("textbox", name="Διεύθυνση").fill(FALLBACK["street"])
    page.get_by_role("textbox", name="Περιοχή").fill(FALLBACK["area"])
    page.get_by_role("textbox", name="Ταχυδρομικός κώδικας").fill(FALLBACK["zip"])
    for label, val in (("Γεωγραφικό πλάτος", FALLBACK["lat"]), ("Γεωγραφικό μήκος", FALLBACK["lon"])):
        page.locator(f"label:has-text('{label}')").last.evaluate(
            "(l, v) => { const i = document.getElementById(l.htmlFor); i.value = v;"
            " i.dispatchEvent(new Event('input', {bubbles: true})); }", val)
    page.get_by_role("textbox", name="Σημειώσεις εγκατάστασης").fill(FALLBACK["note"])
    print("ΠΑΥΣΗ: έλεγξε ότι lat/lon έγιναν δεκτά από τη φόρμα, μετά Resume.")
    page.pause()


def pick_installation(page, wo, customer_kind):
    wo_no = wo["Work Order Number"]
    if customer_kind == "existing":
        dd = page.get_by_role("textbox", name="Εγκατάσταση", exact=True)
        dd.wait_for(state="visible"); dd.click(); page.wait_for_timeout(1000)
        texts = page.get_by_role("option").all_inner_texts()
        distinct = list({t.strip() for t in texts})
        print(f"Εγκαταστάσεις πελάτη: {len(distinct)}", distinct)
        hits = [t for t in distinct if matches_address(t, wo)]
        print(f"Ταιριάζουν στη διεύθυνση: {len(hits)}", hits)
        if len(hits) > 1:
            raise Review(f"{len(hits)} εγκαταστάσεις ταιριάζουν")
        if len(hits) == 1:
            page.get_by_role("option").filter(has_text=hits[0]).first.click()
            print("Επιλέχθηκε υπάρχουσα εγκατάσταση")
            return "existing_installation"
        page.keyboard.press("Escape")
        page.get_by_text("Νέα εγκατάσταση;").click()
        page.wait_for_timeout(500)
    page.get_by_role("textbox", name="Περιγραφή").last.wait_for(state="visible")
    ok = google_address(page, wo)
    if not ok:
        fallback_address(page)
    page.get_by_role("textbox", name="Περιγραφή").last.fill(wo_no)
    return "new_installation" if ok else "fallback_address"


def exists_in_domx(page, wo_no):
    page.goto(TASKS_URL + wo_no); page.wait_for_timeout(3000)
    return page.get_by_text(wo_no, exact=False).count() > 0


case = sys.argv[1] if len(sys.argv) > 1 else "T3"
wo = CASES[case]
print(f"=== Σενάριο {case}: {wo['Work Order Number']} | αναμένεται: {wo['expect']} ===")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)
    page.goto("https://portal.business.domx.online/")
    print("Συνδέσου στο domx, μείνε στο dashboard και πάτησε Resume.")
    page.pause()

    if exists_in_domx(page, wo["Work Order Number"]):
        print(f"ΠΑΡΑΛΕΙΨΗ: το {wo['Work Order Number']} υπάρχει ήδη.")
        browser.close(); raise SystemExit

    page.goto("https://portal.business.domx.online/dashboard")
    page.get_by_role("button", name="ΓΡΗΓΟΡΗ ΠΡΟΣΘΗΚΗ").click()
    page.get_by_role("button", name="ΕΚΚΡΕΜΟΤΗΤΑ", exact=True).click()
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="visible")

    result = None
    try:
        title = fill_task_step(page, wo)
        next_button(page, 1).click()
        kind = pick_customer(page, wo)
        next_button(page, 2).click()
        result = pick_installation(page, wo, kind)
    except Review as e:
        print("ΓΙΑ ΕΛΕΓΧΟ:", e)
        close_wizard(page)
        print("Έλεγξε ότι ΔΕΝ δημιουργήθηκε τίποτα, μετά Resume.")
        page.pause(); browser.close(); raise SystemExit
    except Exception as e:
        print("ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ:", type(e).__name__, str(e)[:200])
        print("Ο wizard ΔΕΝ θα ολοκληρωθεί. Κλείνει με Χ.")
        try:
            close_wizard(page)
        except Exception:
            print("Το Χ απέτυχε — κλείσε τον wizard χειροκίνητα με Χ (ΟΧΙ ΤΕΛΟΣ), μετά Resume.")
            page.pause()
        browser.close(); raise SystemExit

    print(f"\nΑποτέλεσμα: {result} | αναμενόταν: {wo['expect']}")
    print("ΕΛΕΓΞΕ ΤΗ ΦΟΡΜΑ. Resume = ΤΕΛΟΣ. Αν κάτι είναι λάθος, κλείσε με Χ πριν το Resume.")
    page.pause()

    end = page.get_by_role("button", name="ΤΕΛΟΣ")
    if end.count() and end.is_visible():
        end.click()
        page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden")
        found = exists_in_domx(page, wo["Work Order Number"])
        print("ΕΠΙΒΕΒΑΙΩΣΗ ΑΠΟΘΗΚΕΥΣΗΣ:", "ΒΡΕΘΗΚΕ" if found else "ΔΕΝ ΒΡΕΘΗΚΕ")
    else:
        print("Ο wizard είχε κλείσει — δεν έγινε καταχώριση.")
    page.pause(); browser.close()
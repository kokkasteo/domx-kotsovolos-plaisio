# domx.py — αναδόμηση 05/11/2026
# ΜΟΝΟ αυτούσια αντιγραφή από τα δοκιμασμένα αρχεία:
#   • pre-check (εύρος 2024–2031 + αναζήτηση): test_domx_search_cycle_no_pause_verified.py (03/11)
#   • wizard βήματα 1–3, Χ, «+», Google, εναλλακτική: test_domx_case_old.py (04/11, T1–T6/E5 πέρασαν)
# Καμία αλλαγή λογικής. Μόνο «τύλιγμα» σε συναρτήσεις + επιστροφή αποτελέσματος.

import re
from datetime import date
from urllib.parse import urlsplit
from playwright.sync_api import expect
from rules import deadline, build_title, build_notes, norm, split_name, customer_phones

OWNER = "Έφη Τσιατσιάνη"
SERVICE_PREFIX = {"kotsovolos": "Κ-", "plaisio": "Π-"}
BASE_URL = "https://portal.business.domx.online"
START_DATE = "01/01/2024"
END_DATE = "31/12/2031"
MIN_TOTAL = 9500   # η πλήρης λίστα μόνο αυξάνεται (9686 στις 05/11/2026)· λιγότερες = λάθος φόρτωση ή φίλτρο
FALLBACK = {"street": "28ης Οκτωβρίου 157", "area": "Νέα Πέραμος", "zip": "19006",
            "lat": "38.011784", "lon": "23.434141",
            "note": "ΕΛΕΓΧΟΣ ΔΙΕΥΘΥΝΣΗΣ — χρησιμοποιήθηκε η διεύθυνση του καταστήματος."}


class Review(Exception):
    """Επιχειρησιακός λόγος: το WO μένει για έλεγχο, δεν είναι τεχνικό σφάλμα."""


def log(msg):
    print("   ", msg)


# =====================================================================
# PRE-CHECK ΔΙΠΛΟΤΥΠΟΥ — αυτούσιο από test_domx_search_cycle_no_pause_verified.py
# =====================================================================

_TASKS = {}   # στοιχεία της σελίδας Εκκρεμότητες (table, heading, baseline, search)


def _open_custom_range(page):
    page.get_by_text("Εύρος ημερομηνιών", exact=True).click()

    card = page.locator(".datepicker-card:visible")
    expect(card).to_have_count(1)

    button = card.get_by_role(
        "button", name="Προσαρμοσμένο εύρος", exact=True
    )
    if button.get_attribute("aria-expanded") != "true":
        button.click()

    dates = card.locator('input[placeholder="ΗΗ/ΜΜ/ΕΕΕΕ"]:visible')
    expect(dates).to_have_count(2)
    return card, dates


def _wait_no_loading(table):
    expect(
        table.get_by_role("progressbar").locator("visible=true")
    ).to_have_count(0, timeout=30000)


def prepare_tasks_page(page):
    """Άνοιγμα Εκκρεμοτήτων, εύρος 2024–2031 με επαλήθευση, καταγραφή αρχικής λίστας,
    εντοπισμός πεδίου αναζήτησης μέσω id. Ίδια σειρά βημάτων με το δοκιμασμένο αρχείο."""
    _TASKS.clear()
    stage = "Άνοιγμα σελίδας"
    try:
        page.goto(BASE_URL + "/tasks", wait_until="domcontentloaded", timeout=60000)
        page.get_by_text("Εύρος ημερομηνιών", exact=True).wait_for(state="visible", timeout=30000)
        if urlsplit(page.url).path.rstrip("/") != "/tasks":
            raise RuntimeError("Δεν βρίσκεσαι στις Εκκρεμότητες.")

        stage = "Εφαρμογή ημερομηνιών"
        card, dates = _open_custom_range(page)
        for index, value in enumerate((START_DATE, END_DATE)):
            dates.nth(index).fill(value)
            dates.nth(index).press("Tab")
            expect(dates.nth(index)).to_have_value(value)
        card.get_by_role("button", name=re.compile(r"^ΕΦΑΡΜΟΓΗ$", re.IGNORECASE)).click()
        expect(card).to_be_hidden()

        card, dates = _open_custom_range(page)
        expect(dates.nth(0)).to_have_value(START_DATE)
        expect(dates.nth(1)).to_have_value(END_DATE)
        card.get_by_role("button", name=re.compile(r"^ΑΚΥΡΩΣΗ$", re.IGNORECASE)).click()
        expect(card).to_be_hidden()
        log(f"Εύρος ημερομηνιών επιβεβαιώθηκε: {START_DATE} – {END_DATE}")

        stage = "Καταγραφή αρχικής λίστας"
        table = page.get_by_role("table")
        expect(table).to_have_count(1)
        _wait_no_loading(table)

        heading = page.get_by_role("heading", level=1)
        baseline_heading = " ".join(heading.inner_text().split())
        match = re.fullmatch(r"Εκκρεμότητες\s+(\d+)\s+Σύνολο", baseline_heading)
        if not match or int(match.group(1)) < MIN_TOTAL:
            raise RuntimeError(f"Η λίστα δεν είναι η πλήρης 2024–2031 ({baseline_heading!r}).")

        first_row = table.get_by_role("row").filter(has=page.get_by_role("cell")).first
        expect(first_row).to_be_visible()
        baseline_row = first_row.inner_text()
        log(f"Αρχική λίστα: {baseline_heading}")

        stage = "Εντοπισμός πεδίου αναζήτησης"
        search = page.get_by_label("Αναζήτηση εκκρεμοτήτων", exact=True)
        expect(search).to_have_count(1)
        expect(search).to_have_value("")
        search_id = search.get_attribute("id")
        if not search_id:
            raise RuntimeError("Το πεδίο αναζήτησης δεν έχει ID.")
        search = page.locator(f'input[id="{search_id}"]')

        _TASKS.update(table=table, heading=heading, baseline_heading=baseline_heading,
                      first_row=first_row, baseline_row=baseline_row, search=search)
    except Exception as e:
        raise RuntimeError(f"[{stage}] {type(e).__name__}: {str(e)[:160]}") from e


def _clear_and_wait(page):
    t = _TASKS
    search = t["search"]
    expect(search).to_be_visible()
    search.press("Control+A")
    search.press("Backspace")
    expect(search).to_have_value("")
    try:
        expect(t["heading"]).to_have_text(t["baseline_heading"], timeout=30000)
        expect(t["first_row"]).to_have_text(t["baseline_row"], timeout=30000)
        _wait_no_loading(t["table"])
    except Exception:
        # Η λίστα άλλαξε στο μεταξύ (π.χ. νέα εκκρεμότητα από agent): στην επόμενη
        # αναζήτηση ξαναφορτώνουμε τη σελίδα από την αρχή.
        log("Η αρχική λίστα δεν επανήλθε ίδια — θα ξαναφορτωθεί στην επόμενη αναζήτηση")
        _TASKS.clear()


def exists_in_domx(page, wo_no):
    """True = ΒΡΕΘΗΚΕ, False = κενή λίστα («Δεν βρέθηκαν εκκρεμότητες» + 0 Σύνολο).
    Οτιδήποτε άλλο → εξαίρεση (Μ-4: αβέβαιο ≠ ανύπαρκτο)."""
    if not _TASKS or urlsplit(page.url).path.rstrip("/") != "/tasks":
        for attempt in range(1, 4):           # έως 3 προσπάθειες φόρτωσης της πλήρους λίστας
            try:
                prepare_tasks_page(page); break
            except RuntimeError as e:
                log(f"Φόρτωση Εκκρεμοτήτων, προσπάθεια {attempt}/3 απέτυχε: {e}")
                if attempt == 3:
                    raise
    t = _TASKS
    table, heading, search = t["table"], t["heading"], t["search"]

    empty_message = table.get_by_text("Δεν βρέθηκαν εκκρεμότητες", exact=True)
    title_pattern = re.compile(rf"^\s*{re.escape(wo_no)}(?:\s*/\s*\d+)?\s*$")
    result = table.get_by_role("cell").filter(has_text=title_pattern)

    expect(search).to_be_visible()
    expect(search).to_be_editable()
    expect(search).to_have_value("")
    search.fill(wo_no)
    expect(search).to_have_value(wo_no)

    found = None
    for _ in range(60):                       # έως 30 δευτερόλεπτα
        if result.count() > 0 and result.first.is_visible():
            found = True
            break
        if empty_message.count() > 0 and empty_message.is_visible():
            found = False
            break
        page.wait_for_timeout(500)
    if found is None:
        _clear_and_wait(page)
        raise RuntimeError("Έλεγχος διπλοτύπου αβέβαιος: ούτε WO ούτε κενή λίστα σε 30s")

    _wait_no_loading(table)
    if found:
        expect(result.first).to_be_visible()
        title = result.first.inner_text().strip()
        log(f"ΒΡΕΘΗΚΕ στο domx: {title}")
    else:
        expect(empty_message).to_be_visible()
        expect(heading).to_have_text(re.compile(r"^\s*Εκκρεμότητες\s+0\s+Σύνολο\s*$"), timeout=30000)
        expect(result).to_have_count(0)
        log(f"Δεν υπάρχει στο domx: {wo_no}")

    _clear_and_wait(page)
    return found


# =====================================================================
# WIZARD — αυτούσιο από test_domx_case_old.py
# =====================================================================

def next_button(page, step):
    return page.get_by_role("button", name="ΕΠΟΜΕΝΟ").nth(step - 1)


def clock_pick(page, value):
    page.get_by_role("menu").get_by_text(value, exact=True).click()


def field_value(page, label):
    # Διαβάζει την τιμή του input που αντιστοιχεί στην ετικέτα (δουλεύει και για μη-textbox πεδία)
    return page.locator(f"label:has-text('{label}')").last.evaluate(
        "l => { const i = document.getElementById(l.htmlFor); return i ? i.value : ''; }")


def wizard_is_open(page):
    t = page.get_by_role("textbox", name="Τίτλος")
    return t.count() > 0 and t.first.is_visible()


def close_wizard(page):
    # Κλείσιμο με Χ χωρίς ΤΕΛΟΣ: στοχεύουμε το κουμπί που περιέχει το εικονίδιο mdi-window-close
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    x_btns = page.get_by_role("button").filter(has=page.locator("i.mdi-window-close"))
    visible = [x_btns.nth(i) for i in range(x_btns.count()) if x_btns.nth(i).is_visible()]
    log(f"Κουμπιά Χ με mdi-window-close: {x_btns.count()}, ορατά: {len(visible)}")
    if not visible:
        raise RuntimeError("Δεν βρέθηκε ορατό Χ του wizard")
    try:
        visible[0].click(timeout=5000)
    except Exception:
        log("Το Χ είναι εκτός ορατής περιοχής, κλικ μέσω JavaScript")
        visible[0].evaluate("b => b.click()")
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden", timeout=5000)
    log("Ο wizard έκλεισε με Χ.")


def open_wizard(page):
    page.goto(BASE_URL + "/dashboard")
    page.get_by_role("button", name="ΓΡΗΓΟΡΗ ΠΡΟΣΘΗΚΗ").click()
    page.get_by_role("button", name="ΕΚΚΡΕΜΟΤΗΤΑ", exact=True).click()
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="visible")

GREEK_MONTHS = ["Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος",
                "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"]

def date_pick(page, due):
    """Επιλέγει την ημερομηνία προθεσμίας στο πεδίο «Ολοκλήρωση έως» (Vuetify date picker)."""
    field = page.get_by_label("Ολοκλήρωση έως", exact=True)
    field.click()
    header = page.locator(".v-date-picker-header__value").last
    header.wait_for(state="visible", timeout=10000)
    target = f"{GREEK_MONTHS[due.month - 1]} {due.year}"
    for _ in range(36):
        shown = header.inner_text().strip()
        if norm(shown) == norm(target):
            break
        parts = shown.split()
        shown_idx = (int(parts[1]) * 12 + GREEK_MONTHS.index(parts[0])) if len(parts) == 2 and parts[0] in GREEK_MONTHS else None
        target_idx = due.year * 12 + (due.month - 1)
        arrows = page.locator(".v-date-picker-header button")
        (arrows.last if shown_idx is None or shown_idx < target_idx else arrows.first).click()
        page.wait_for_timeout(300)
    else:
        raise RuntimeError(f"Ημερολόγιο: δεν βρέθηκε ο μήνας «{target}»")
    day = page.locator(".v-date-picker-table button").filter(
        has_text=re.compile(rf"^\s*{due.day}\s*$")).first
    day.click()
    expect(field).to_have_value(due.strftime("%Y-%m-%d"), timeout=5000)
    if header.is_visible():
        page.keyboard.press("Escape")
    log(f"Ημερομηνία προθεσμίας: {due.strftime('%d/%m/%Y')}")

def fill_task_step(page, wo, today=None):
    today = today or date.today()
    title = build_title(wo["Work Order Number"], wo["Service"], wo.get("POD", ""))
    service = SERVICE_PREFIX[wo.get("_source", "kotsovolos")] + wo["Service"]
    due = deadline(wo.get("_pdd"), today)   # _pdd: Product Delivery Date ως date ή None

    page.get_by_role("textbox", name="Τίτλος").click()
    page.get_by_role("textbox", name="Τίτλος").fill(title)

    svc = page.get_by_role("textbox", name="Σύνδεση με τύπο υπηρεσίας")
    svc.click(); svc.fill(service); page.wait_for_timeout(1200)
    options = page.get_by_role("option")
    texts = options.all_inner_texts()
    matches = [i for i, t in enumerate(texts) if norm(t) == norm(service)]
    distinct = {texts[i].strip() for i in matches}
    log(f"Υπηρεσία «{service}»: επιλογές {len(texts)}, διακριτές ταυτίσεις {len(distinct)}")
    if len(distinct) != 1:
        raise Review(f"Υπηρεσία «{service}» δεν βρέθηκε μονοσήμαντα ({len(distinct)})")
    options.nth(matches[0]).click()
    page.keyboard.press("Escape")

    owner = page.get_by_role("textbox", name="Χρήστης / Συνεργάτης").last
    owner.click()
    page.get_by_role("option").filter(has_text=OWNER).first.click()
    page.keyboard.press("Escape")

    date_pick(page, due)
    page.locator(".v-input--selection-controls__ripple").first.click()
    time_btn = page.get_by_role("button", name="Ώρα")
    time_btn.wait_for(state="visible"); time_btn.click()
    clock_pick(page, str(due.hour)); clock_pick(page, due.strftime("%M"))
    page.get_by_role("menu").get_by_role("button").last.click()
    page.get_by_role("menu").wait_for(state="hidden")

    notes = page.get_by_role("textbox", name="Σημειώσεις εκκρεμότητας")
    notes.click(); notes.fill(wo.get("_notes") or build_notes(wo))
    log(f"Τίτλος: {title} | Προθεσμία: {due.strftime('%d/%m/%Y %H:%M')}")
    return title


def pick_customer(page, wo):
    search_phone, phones = customer_phones(wo.get("Contact Mobile Phone", ""),
                                           wo.get("Contact Phone Number", ""))
    if search_phone:
        box = page.get_by_role("textbox", name="Πελάτης", exact=True)
        box.wait_for(state="visible")
        page.wait_for_function("el => !el.disabled", arg=box.element_handle(), timeout=15000)
        box.click(); box.fill(search_phone); page.wait_for_timeout(1500)
        opts = page.get_by_role("option").all_inner_texts()
        distinct = {t.strip() for t in opts}
        log(f"Αναζήτηση {search_phone}: {len(distinct)} πελάτες {list(distinct)[:3]}")
        if len(distinct) == 1:
            page.get_by_role("option").first.click(); return "existing"
        if len(distinct) > 1:
            raise Review(f"{len(distinct)} πελάτες με τηλέφωνο {search_phone}")
        page.keyboard.press("Escape")
    page.get_by_text("Νέος πελάτης;").click()
    first, last = split_name(wo.get("Contact Name", ""))     # ValueError αν κενό
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
        log(f"Τύποι επαφών: {types}")
        if types != ["Κινητό", "Σταθερό"]:
            raise RuntimeError(f"Λάθος τύποι επαφών {types}")
    log(f"Νέος πελάτης: {first} / {last}, τηλέφωνα {phones}")
    return "new"


def matches_address(option_text, wo):
    # Ε-8: norm(επιλογή) περιέχει norm(Street 1) ΚΑΙ norm(City)
    t = norm(option_text)
    return norm(wo["Street 1"]) in t and norm(wo["City"]) in t


def google_address(page, wo):
    addr = page.get_by_role("textbox", name="Διεύθυνση")
    addr.click(); addr.fill("")
    addr.type(f"{wo['Street 1']} {wo['City']}", delay=80)
    page.wait_for_timeout(2500)
    texts = page.locator(".pac-item").all_inner_texts()
    log(f"Προτάσεις Google: {len(texts)} {texts[:3]}")
    good = [i for i, t in enumerate(texts) if norm(wo["City"]) in norm(t)]
    if not good:
        return False
    for _ in range(good[0] + 1):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    lat, zipc = field_value(page, "Γεωγραφικό πλάτος"), field_value(page, "Ταχυδρομικός κώδικας")
    log(f"Στίγμα: {lat}, {field_value(page, 'Γεωγραφικό μήκος')} | ΤΚ: {zipc}")
    return not lat.startswith("37,98381") and zipc.replace(" ", "") == wo.get("Postal Code", "")


def fallback_address(page):
    # Εναλλακτική διεύθυνση καταστήματος + σημείωση ΜΟΝΟ στις σημειώσεις εγκατάστασης
    log("Εναλλακτική διεύθυνση καταστήματος")
    page.get_by_role("textbox", name="Διεύθυνση").fill(FALLBACK["street"])
    page.get_by_role("textbox", name="Περιοχή").fill(FALLBACK["area"])
    page.get_by_role("textbox", name="Ταχυδρομικός κώδικας").fill(FALLBACK["zip"])
    for label, val in (("Γεωγραφικό πλάτος", FALLBACK["lat"]), ("Γεωγραφικό μήκος", FALLBACK["lon"])):
        page.locator(f"label:has-text('{label}')").last.evaluate(
            "(l, v) => { const i = document.getElementById(l.htmlFor); i.value = v;"
            " i.dispatchEvent(new Event('input', {bubbles: true})); }", val)
    page.get_by_role("textbox", name="Σημειώσεις εγκατάστασης").fill(FALLBACK["note"])


def pick_installation(page, wo, customer_kind):
    wo_no = wo["Work Order Number"]
    if customer_kind == "existing":
        dd = page.get_by_role("textbox", name="Εγκατάσταση", exact=True)
        dd.wait_for(state="visible"); dd.click(); page.wait_for_timeout(1000)
        texts = page.get_by_role("option").all_inner_texts()
        distinct = list({t.strip() for t in texts})
        log(f"Εγκαταστάσεις πελάτη: {len(distinct)} {distinct}")
        hits = [t for t in distinct if matches_address(t, wo)]
        log(f"Ταιριάζουν στη διεύθυνση: {len(hits)} {hits}")
        if len(hits) > 1:
            raise Review(f"{len(hits)} εγκαταστάσεις ταιριάζουν")
        if len(hits) == 1:
            page.get_by_role("option").filter(has_text=hits[0]).first.click()
            log("Επιλέχθηκε υπάρχουσα εγκατάσταση")
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


# =====================================================================
# ΠΛΗΡΗΣ ΚΥΚΛΟΣ ΕΝΟΣ WO
# =====================================================================

def _safe_close(page):
    try:
        if wizard_is_open(page):
            close_wizard(page)
    except Exception as e:
        log(f"ΠΡΟΣΟΧΗ: ο wizard δεν έκλεισε ({type(e).__name__}) — κλείσε τον χειροκίνητα με Χ (ΟΧΙ ΤΕΛΟΣ)")
        page.pause()


def process_wo(page, wo, confirm=None, today=None):
    """Επιστρέφει dict: result, stage, reason, domx_ref.
    result ∈ ΠΑΡΑΛΕΙΨΗ / ΚΑΤΑΧΩΡΙΣΤΗΚΕ / ΓΙΑ ΕΛΕΓΧΟ / ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ. Ποτέ δεν αφήνει wizard ανοιχτό."""
    wo_no = wo["Work Order Number"]
    stage = "precheck"
    try:
        if exists_in_domx(page, wo_no):
            return dict(result="ΠΑΡΑΛΕΙΨΗ", stage=stage, reason="Υπάρχει ήδη στο domx", domx_ref=wo_no)
        _TASKS.clear()                        # Σ-7: δεύτερος έλεγχος μετά από πλήρη επαναφόρτωση
        log("Δεν βρέθηκε — επαναφόρτωση σελίδας και δεύτερη αναζήτηση")
        if exists_in_domx(page, wo_no):
            return dict(result="ΠΑΡΑΛΕΙΨΗ", stage=stage, reason="Υπάρχει ήδη στο domx (2ος έλεγχος)", domx_ref=wo_no)
    except Exception as e:
        return dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage=stage,
                    reason=f"{type(e).__name__}: {str(e)[:200]}", domx_ref="")

    try:
        stage = "task"; open_wizard(page)
        title = fill_task_step(page, wo, today)
        next_button(page, 1).click()
        stage = "customer"; kind = pick_customer(page, wo)
        next_button(page, 2).click()
        stage = "installation"; inst = pick_installation(page, wo, kind)
        stage = "finish"
        if confirm and not confirm(page):
            _safe_close(page)
            return dict(result="ΓΙΑ ΕΛΕΓΧΟ", stage=stage, reason="Ακυρώθηκε από χρήστη", domx_ref="")
        end = page.get_by_role("button", name="ΤΕΛΟΣ")
        end.click()
        page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden", timeout=15000)
        stage = "verify"
        try:
            found = exists_in_domx(page, wo_no)
        except RuntimeError as e:
            log(f"Verify αβέβαιο ({e}) — επαναφόρτωση και δεύτερη αναζήτηση (Σ-7)")
            _TASKS.clear()
            found = exists_in_domx(page, wo_no)
        if found:
            return dict(result="ΚΑΤΑΧΩΡΙΣΤΗΚΕ", stage=stage,
                        reason=f"πελάτης {kind}, εγκατάσταση {inst}", domx_ref=title)
        return dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage=stage,
                    reason="Δεν βρέθηκε μετά το ΤΕΛΟΣ (Σ-3: έλεγξε χειροκίνητα πριν επανάληψη)", domx_ref="")
    except Review as e:
        log(f"ΓΙΑ ΕΛΕΓΧΟ: {e}")
        _safe_close(page)
        return dict(result="ΓΙΑ ΕΛΕΓΧΟ", stage=stage, reason=str(e), domx_ref="")
    except ValueError as e:                        # π.χ. κενό Contact Name
        log(f"ΓΙΑ ΕΛΕΓΧΟ: {e}")
        _safe_close(page)
        return dict(result="ΓΙΑ ΕΛΕΓΧΟ", stage=stage, reason=str(e), domx_ref="")
    except Exception as e:
        log(f"ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ: {type(e).__name__} {str(e)[:200]}")
        _safe_close(page)
        return dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage=stage,
                    reason=f"{type(e).__name__}: {str(e)[:150]}", domx_ref="")

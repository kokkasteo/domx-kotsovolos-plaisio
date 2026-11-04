from datetime import date
import re
from playwright.sync_api import expect
from rules import deadline, build_title, build_notes, norm, split_name, customer_phones


OWNER = "Έφη Τσιατσιάνη"
BASE_URL = "https://portal.business.domx.online"
START_DATE, END_DATE = "01/01/2024", "31/12/2031"
FALLBACK = {"street": "28ης Οκτωβρίου 157", "area": "Νέα Πέραμος", "zip": "19006",
            "lat": "38.011784", "lon": "23.434141",
            "note": "ΕΛΕΓΧΟΣ ΔΙΕΥΘΥΝΣΗΣ — χρησιμοποιήθηκε η διεύθυνση του καταστήματος."}
OMONOIA_LAT = "37,98381"


class Review(Exception):
    """Επιχειρησιακός λόγος: το WO μένει για έλεγχο."""


# ---------- βοηθητικά ----------

def log(msg):
    print("   ", msg)


def next_button(page, step):
    return page.get_by_role("button", name="ΕΠΟΜΕΝΟ").nth(step - 1)


def clock_pick(page, value):
    page.get_by_role("menu").get_by_text(value, exact=True).click()


def field_value(page, label):
    return page.locator(f"label:has-text('{label}')").last.evaluate(
        "l => { const i = document.getElementById(l.htmlFor); return i ? i.value : ''; }")


def set_field_js(page, label, value):
    page.locator(f"label:has-text('{label}')").last.evaluate(
        "(l, v) => { const i = document.getElementById(l.htmlFor); i.value = v;"
        " i.dispatchEvent(new Event('input', {bubbles: true})); }", value)


def close_wizard(page):
    # Χ του wizard: ακυρώνει τα πάντα (επιβεβαιωμένο χειροκίνητα 04/11)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    x_btns = page.get_by_role("button").filter(has=page.locator("i.mdi-window-close"))
    visible = [x_btns.nth(i) for i in range(x_btns.count()) if x_btns.nth(i).is_visible()]
    if not visible:
        raise RuntimeError("Δεν βρέθηκε ορατό Χ του wizard")
    try:
        visible[0].click(timeout=5000)
    except Exception:
        visible[0].evaluate("b => b.click()")
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden", timeout=5000)
    log("Ο wizard έκλεισε με Χ")


def wizard_is_open(page):
    return page.get_by_role("textbox", name="Τίτλος").count() > 0 and \
        page.get_by_role("textbox", name="Τίτλος").first.is_visible()


# ---------- έλεγχος διπλοτύπου (Μ-2, Μ-4) ----------
# Αυτούσιο από test_domx_search_cycle_no_pause_verified.py (δοκιμασμένο 03/11)

def _open_custom_range(page):
    page.get_by_text("Εύρος ημερομηνιών", exact=True).click()
    card = page.locator(".datepicker-card:visible")
    expect(card).to_have_count(1)
    button = card.get_by_role("button", name="Προσαρμοσμένο εύρος", exact=True)
    if button.get_attribute("aria-expanded") != "true":
        button.click()
    dates = card.locator('input[placeholder="ΗΗ/ΜΜ/ΕΕΕΕ"]:visible')
    expect(dates).to_have_count(2)
    return card, dates


def _wait_no_loading(table):
    expect(table.get_by_role("progressbar").locator("visible=true")).to_have_count(0, timeout=30000)


def prepare_tasks_page(page):
    """Ανοίγει τις Εκκρεμότητες και εφαρμόζει το εύρος 2024–2031 με διπλή επαλήθευση."""
    page.goto(BASE_URL + "/tasks", wait_until="domcontentloaded", timeout=60000)
    page.get_by_text("Εύρος ημερομηνιών", exact=True).wait_for(state="visible", timeout=30000)
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
    table = page.get_by_role("table")
    expect(table).to_have_count(1)
    _wait_no_loading(table)
    log(f"Εύρος ημερομηνιών επιβεβαιώθηκε: {START_DATE} – {END_DATE}")


def exists_in_domx(page, wo_no):
    """True = υπάρχει, False = σίγουρα δεν υπάρχει (κενή λίστα), εξαίρεση = αβέβαιο (Μ-4)."""
    if "/tasks" not in page.url:
        prepare_tasks_page(page)
    table = page.get_by_role("table")
    search = page.get_by_label("Αναζήτηση εκκρεμοτήτων", exact=True)
    expect(search).to_have_count(1)
    search_id = search.get_attribute("id")
    if not search_id:
        raise RuntimeError("Το πεδίο αναζήτησης δεν έχει ID.")
    search = page.locator(f'input[id="{search_id}"]')
    search.press("Control+A"); search.press("Backspace")
    expect(search).to_have_value("")
    search.fill(wo_no)
    expect(search).to_have_value(wo_no)
    empty_message = table.get_by_text("Δεν βρέθηκαν εκκρεμότητες", exact=True)
    title_pattern = re.compile(rf"^\s*{re.escape(wo_no)}(?:\s*/\s*\d+)?\s*$")
    result = table.get_by_role("cell").filter(has_text=title_pattern)
    for _ in range(60):
        if result.count() > 0:
            _wait_no_loading(table)
            return result.count() > 0
        if empty_message.count() > 0:
            _wait_no_loading(table)
            return result.count() > 0
        page.wait_for_timeout(500)
    raise RuntimeError("Έλεγχος διπλοτύπου αβέβαιος: ούτε WO ούτε κενή λίστα σε 30s")


# ---------- βήμα 1: εκκρεμότητα ----------

def fill_task_step(page, wo, today=None):
    today = today or date.today()
    title = build_title(wo["Work Order Number"], wo["Service"], wo.get("POD", ""))
    service = "Κ-" + wo["Service"]
    due = deadline(wo.get("_pdd"), today)   # _pdd: ημερομηνία παράδοσης ως date ή None

    page.get_by_role("textbox", name="Τίτλος").click()
    page.get_by_role("textbox", name="Τίτλος").fill(title)

    svc = page.get_by_role("textbox", name="Σύνδεση με τύπο υπηρεσίας")
    svc.click(); svc.fill(service); page.wait_for_timeout(1200)
    options = page.get_by_role("option")
    texts = options.all_inner_texts()
    matches = [i for i, t in enumerate(texts) if norm(t) == norm(service)]
    distinct = {texts[i].strip() for i in matches}
    if len(distinct) != 1:
        raise Review(f"Υπηρεσία «{service}» δεν βρέθηκε μονοσήμαντα ({len(distinct)})")
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
    log(f"Τίτλος {title} | Προθεσμία {due.strftime('%d/%m/%Y %H:%M')}")
    return title


# ---------- βήμα 2: πελάτης ----------

def pick_customer(page, wo):
    search_phone, phones = customer_phones(wo.get("Contact Mobile Phone", ""),
                                           wo.get("Contact Phone Number", ""))
    if search_phone:
        box = page.get_by_role("textbox", name="Πελάτης", exact=True)
        box.wait_for(state="visible")
        page.wait_for_function("el => !el.disabled", arg=box.element_handle(), timeout=15000)
        box.click(); box.fill(search_phone); page.wait_for_timeout(1500)
        distinct = {t.strip() for t in page.get_by_role("option").all_inner_texts()}
        log(f"Αναζήτηση {search_phone}: {len(distinct)} πελάτες")
        if len(distinct) == 1:
            page.get_by_role("option").first.click()
            return "existing"
        if len(distinct) > 1:
            raise Review(f"{len(distinct)} πελάτες με τηλέφωνο {search_phone}")
        page.keyboard.press("Escape")

    page.get_by_text("Νέος πελάτης;").click()
    first, last = split_name(wo.get("Contact Name", ""))   # ValueError αν κενό
    page.get_by_role("textbox", name="Όνομα").fill(first)
    page.get_by_role("textbox", name="Επώνυμο").fill(last)
    page.get_by_role("textbox", name="Τηλέφωνο").first.fill(phones[0])
    if len(phones) > 1:
        page.get_by_role("button").filter(has=page.locator("i.mdi-plus")).last.click()
        page.get_by_role("textbox", name="Τηλέφωνο").nth(1).wait_for(state="visible")
        page.get_by_role("textbox", name="Τηλέφωνο").nth(1).fill(phones[1])
        page.get_by_role("textbox", name="Τύπος επικοινωνίας").nth(1).click()
        page.get_by_role("option").filter(has_text="Σταθερό").first.click()
        page.keyboard.press("Escape")
        types = [page.get_by_role("textbox", name="Τύπος επικοινωνίας").nth(i).input_value() for i in range(2)]
        if types != ["Κινητό", "Σταθερό"]:
            raise RuntimeError(f"Λάθος τύποι επαφών {types}")
    log(f"Νέος πελάτης {first} / {last}, τηλέφωνα {phones}")
    return "new"


# ---------- βήμα 3: εγκατάσταση ----------

def matches_address(option_text, wo):
    # Ε-8 (συμφωνημένο 04/11): norm(επιλογή) περιέχει norm(Street 1) ΚΑΙ norm(City)
    t = norm(option_text)
    return norm(wo["Street 1"]) in t and norm(wo["City"]) in t


def google_address(page, wo):
    addr = page.get_by_role("textbox", name="Διεύθυνση")
    addr.click(); addr.fill("")
    addr.type(f"{wo['Street 1']} {wo['City']}", delay=80)
    page.wait_for_timeout(2500)
    texts = page.locator(".pac-item").all_inner_texts()
    good = [i for i, t in enumerate(texts) if norm(wo["City"]) in norm(t)]
    log(f"Προτάσεις Google: {len(texts)}, με σωστή πόλη: {len(good)}")
    if not good:
        return False
    for _ in range(good[0] + 1):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    lat, zipc = field_value(page, "Γεωγραφικό πλάτος"), field_value(page, "Ταχυδρομικός κώδικας")
    log(f"Στίγμα {lat}, {field_value(page, 'Γεωγραφικό μήκος')} | ΤΚ {zipc}")
    return not lat.startswith(OMONOIA_LAT) and zipc.replace(" ", "") == wo.get("Postal Code", "")


def fallback_address(page):
    log("Εναλλακτική διεύθυνση καταστήματος (Ε-6)")
    page.get_by_role("textbox", name="Διεύθυνση").fill(FALLBACK["street"])
    page.get_by_role("textbox", name="Περιοχή").fill(FALLBACK["area"])
    page.get_by_role("textbox", name="Ταχυδρομικός κώδικας").fill(FALLBACK["zip"])
    set_field_js(page, "Γεωγραφικό πλάτος", FALLBACK["lat"])
    set_field_js(page, "Γεωγραφικό μήκος", FALLBACK["lon"])
    page.get_by_role("textbox", name="Σημειώσεις εγκατάστασης").fill(FALLBACK["note"])


def pick_installation(page, wo, customer_kind):
    wo_no = wo["Work Order Number"]
    if customer_kind == "existing":
        dd = page.get_by_role("textbox", name="Εγκατάσταση", exact=True)
        page.wait_for_timeout(1500)
        if dd.count() == 0 or dd.first.is_disabled():
            log("Πελάτης χωρίς εγκαταστάσεις — φόρμα νέας απευθείας")
        else:
            dd.click(); page.wait_for_timeout(1000)
            distinct = list({t.strip() for t in page.get_by_role("option").all_inner_texts()})
            hits = [t for t in distinct if matches_address(t, wo)]
            log(f"Εγκαταστάσεις {len(distinct)}, ταιριάζουν {len(hits)}")
            if len(hits) > 1:
                raise Review(f"{len(hits)} εγκαταστάσεις ταιριάζουν στη διεύθυνση")
            if len(hits) == 1:
                page.get_by_role("option").filter(has_text=hits[0]).first.click()
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


# ---------- πλήρης κύκλος ενός WO ----------

def open_wizard(page):
    page.goto(BASE_URL + "/dashboard")
    page.get_by_role("button", name="ΓΡΗΓΟΡΗ ΠΡΟΣΘΗΚΗ").click()
    page.get_by_role("button", name="ΕΚΚΡΕΜΟΤΗΤΑ", exact=True).click()
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="visible")


def process_wo(page, wo, confirm=None, today=None):
    """Επιστρέφει dict: result, stage, reason, domx_ref. Ποτέ δεν αφήνει wizard ανοιχτό."""
    wo_no = wo["Work Order Number"]
    stage = "precheck"
    try:
        if exists_in_domx(page, wo_no):
            return dict(result="ΠΑΡΑΛΕΙΨΗ", stage=stage, reason="Υπάρχει ήδη στο domx", domx_ref=wo_no)
    except Exception as e:
        return dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage=stage, reason=str(e)[:200], domx_ref="")

    try:
        stage = "task"; open_wizard(page)
        title = fill_task_step(page, wo, today)
        next_button(page, 1).click()
        stage = "customer"; kind = pick_customer(page, wo)
        next_button(page, 2).click()
        stage = "installation"; inst = pick_installation(page, wo, kind)
        stage = "finish"
        if confirm and not confirm(page):
            close_wizard(page)
            return dict(result="ΓΙΑ ΕΛΕΓΧΟ", stage=stage, reason="Ακυρώθηκε από χρήστη", domx_ref="")
        page.get_by_role("button", name="ΤΕΛΟΣ").click()
        page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden", timeout=15000)
        stage = "verify"
        found = exists_in_domx(page, wo_no)
        if found:
            return dict(result="ΚΑΤΑΧΩΡΙΣΤΗΚΕ", stage=stage,
                        reason=f"πελάτης {kind}, εγκατάσταση {inst}", domx_ref=title)
        return dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage=stage, reason="Δεν βρέθηκε μετά το ΤΕΛΟΣ (Σ-3)", domx_ref="")
    except Review as e:
        _safe_close(page)
        return dict(result="ΓΙΑ ΕΛΕΓΧΟ", stage=stage, reason=str(e), domx_ref="")
    except ValueError as e:                       # π.χ. κενό Contact Name
        _safe_close(page)
        return dict(result="ΓΙΑ ΕΛΕΓΧΟ", stage=stage, reason=str(e), domx_ref="")
    except Exception as e:
        _safe_close(page)
        return dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage=stage, reason=f"{type(e).__name__}: {str(e)[:150]}", domx_ref="")


def _safe_close(page):
    try:
        if wizard_is_open(page):
            close_wizard(page)
    except Exception as e:
        log(f"ΠΡΟΣΟΧΗ: ο wizard δεν έκλεισε ({type(e).__name__}) — ανανέωση σελίδας")
        page.goto(BASE_URL + "/dashboard")
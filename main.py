import csv, re, sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from playwright.sync_api import sync_playwright
import domx
from rules import deadline, build_title, split_name, customer_phones
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
REPORTS = Path("reports")

SOURCE_URL = "https://kotsovolosportal.powerappsportals.com/workorder-list/"
HISTORY = Path("history.csv")
COLUMNS = ["run_id", "time", "wo", "stage", "result", "reason", "domx_ref", "recheck"]
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else None

FIELDS = [
    ("Work Order Number", r"^Work Order Number$"),
    ("Service", r"^Service is a required field\.$"),
    ("Contact Name", r"^Contact Name$"),
    ("Contact Mobile Phone", r"^Contact Mobile Phone$"),
    ("Contact Phone Number", r"^Contact Phone Number$"),
    ("POD", r"^POD$"),
    ("OTP", r"^OTP$"),
    ("Product", r"^Product$"),
    ("Product Delivery Date", r"^Product Delivery Date\s*\*?$"),
    ("Appointment Date", r"^Appointment Date$"),
    ("Work Order Summary", r"^Work Order Summary$"),
    ("Survey Response", r"^Survey Response$"),
    ("Street 1", r"^Street 1$"),
    ("City", r"^City$"),
    ("Postal Code", r"^Postal Code$"),
    ("Change Status Comments", r"^Change Status Comments$"),
    ("Street 2", r"^Street 2$"),
    ("Street 3", r"^Street 3$"),
]


# ---------- ΑΝΑΓΝΩΣΗ ΚΩΤΣΟΒΟΛΟΥ (αυτούσια λογική read_current_page.py) ----------

def read_field(page, pattern):
    field = page.get_by_role("textbox", name=re.compile(pattern))
    field.first.wait_for(state="attached", timeout=15000)
    if field.count() != 1:
        raise RuntimeError("Το πεδίο δεν εντοπίστηκε μοναδικά.")
    return field.evaluate(
        'el => (("value" in el ? el.value : el.textContent) ?? "").trim()')


def collect_targets(page):
    links = page.get_by_role("link", name=re.compile(r"^WO\d+$"))
    links.first.wait_for(state="visible", timeout=15000)
    targets = {}
    for i in range(links.count()):
        number = links.nth(i).inner_text().strip()
        href = links.nth(i).get_attribute("href")
        if not href:
            raise RuntimeError(f"Δεν βρέθηκε διεύθυνση για το {number}.")
        url = urljoin(page.url, href)
        if urlsplit(url).netloc != urlsplit(SOURCE_URL).netloc:
            raise RuntimeError(f"Μη αναμενόμενος σύνδεσμος για το {number}.")
        targets.setdefault(number, url)
    return targets


def parse_pdd(text):
    # «07/11/2026» ή «07/11/2026 00:00» → date· οτιδήποτε άλλο → None (= σήμερα 01:00 κατά Π-1)
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", (text or "").strip())
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def read_wo(page, expected_wo, url):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    actual = read_field(page, r"^Work Order Number$")
    if actual != expected_wo:
        raise RuntimeError(f"Αναμενόταν {expected_wo}, διαβάστηκε {actual}.")
    wo = {label: read_field(page, pattern) for label, pattern in FIELDS}
    wo["_pdd"] = parse_pdd(wo["Product Delivery Date"])
    return wo


# ---------- ΙΣΤΟΡΙΚΟ CSV ----------

def previous_wos():
    if not HISTORY.exists():
        return set()
    with HISTORY.open(encoding="utf-8-sig", newline="") as f:
        return {row["wo"] for row in csv.DictReader(f)}


def append_history(run_id, wo_no, r, recheck):
    new_file = not HISTORY.exists()
    with HISTORY.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow(dict(run_id=run_id, time=datetime.now().strftime("%H:%M:%S"), wo=wo_no,
                        stage=r["stage"], result=r["result"], reason=r["reason"],
                        domx_ref=r["domx_ref"], recheck="ναι" if recheck else ""))


def confirm(page):
    print("ΕΛΕΓΞΕ ΤΗ ΦΟΡΜΑ. Resume = ΤΕΛΟΣ. Αν κάτι είναι λάθος, κλείσε με Χ πριν το Resume.")
    page.pause()
    return domx.wizard_is_open(page)

# ---------- REPORT ΑΝΑ ΕΚΤΕΛΕΣΗ ----------

COLORS = {"ΚΑΤΑΧΩΡΙΣΤΗΚΕ": "C6EFCE", "ΠΑΡΑΛΕΙΨΗ": "E7E6E6", "ΓΙΑ ΕΛΕΓΧΟ": "FFEB9C", "ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ": "FFC7CE"}
HEAD = ["WO", "Υπηρεσία", "Τίτλος domx", "Προθεσμία", "Παράδοση (πηγή)", "Πελάτης", "Τηλέφωνα",
        "Διεύθυνση πηγής", "Επιλογή πελάτη/εγκατάστασης", "Αποτέλεσμα", "Στάδιο", "Αιτία", "Ώρα"]


def report_row(wo, r, t):
    # Μία γραμμή report από τα δεδομένα του WO και το αποτέλεσμα· όλα τα πεδία προαιρετικά
    if wo is None:
        return [r["wo"], "", "", "", "", "", "", "", "", r["result"], r["stage"], r["reason"], t]
    title = build_title(wo["Work Order Number"], wo["Service"], wo.get("POD", ""))
    due = deadline(wo.get("_pdd"), date.today()).strftime("%d/%m/%Y %H:%M")
    try:
        name = " ".join(split_name(wo.get("Contact Name", "")))
    except ValueError:
        name = "(κενό Contact Name)"
    _, phones = customer_phones(wo.get("Contact Mobile Phone", ""), wo.get("Contact Phone Number", ""))
    addr = ", ".join(x for x in (wo.get("Street 1"), wo.get("City"), wo.get("Postal Code")) if x)
    choice = r["reason"] if r["result"] == "ΚΑΤΑΧΩΡΙΣΤΗΚΕ" else ""
    choice = (choice.replace("πελάτης new", "νέος πελάτης").replace("πελάτης existing", "υπάρχων πελάτης")
              .replace("new_installation", "νέα εγκατάσταση (Google)").replace("existing_installation", "υπάρχουσα εγκατάσταση")
              .replace("fallback_address", "ΕΝΑΛΛΑΚΤΙΚΗ ΔΙΕΥΘΥΝΣΗ ΚΑΤΑΣΤΗΜΑΤΟΣ"))
    return [wo["Work Order Number"], wo["Service"], title, due, wo.get("Product Delivery Date", ""),
            name, " / ".join(phones), addr, choice, r["result"], r["stage"], r["reason"], t]


def write_report(run_id, rows, totals, found):
    REPORTS.mkdir(exist_ok=True)
    wb = Workbook(); ws = wb.active; ws.title = "Αποτελέσματα"
    ws.append(HEAD)
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDEBF7")
    for row in rows:
        ws.append(row)
        fill = PatternFill("solid", fgColor=COLORS.get(row[9], "FFFFFF"))
        for c in ws[ws.max_row]:
            c.fill = fill; c.alignment = Alignment(vertical="top", wrap_text=True)
    for col, w in zip("ABCDEFGHIJKLM", (12, 34, 24, 16, 16, 26, 24, 34, 36, 16, 11, 40, 9)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "B2"; ws.auto_filter.ref = ws.dimensions
    s = wb.create_sheet("Σύνολα")
    for k, v in [("Εκτέλεση", run_id), ("Εντοπίστηκαν", found), ("Παραλείφθηκαν ως υπάρχοντα", totals["ΠΑΡΑΛΕΙΨΗ"]),
                 ("Καταχωρίστηκαν", totals["ΚΑΤΑΧΩΡΙΣΤΗΚΕ"]), ("Χρειάζονται έλεγχο", totals["ΓΙΑ ΕΛΕΓΧΟ"]),
                 ("Τεχνικά σφάλματα", totals["ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ"])]:
        s.append([k, v])
    s.column_dimensions["A"].width = 30
    path = REPORTS / f"report_{run_id}.xlsx"
    wb.save(path)
    return path


# ---------- ΚΥΡΙΑ ΡΟΗ ----------

run_id = datetime.now().strftime("%Y%m%d-%H%M")
seen_before = previous_wos()
totals = {"ΠΑΡΑΛΕΙΨΗ": 0, "ΚΑΤΑΧΩΡΙΣΤΗΚΕ": 0, "ΓΙΑ ΕΛΕΓΧΟ": 0, "ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ": 0}
rows = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(no_viewport=True)

    src = ctx.new_page()
    src.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=60000)
    print("ΚΩΤΣΟΒΟΛΟΣ: συνδέσου, επίλεξε την προβολή «Portal 1 – Προγραμματισμένα ανά ημέρα»,")
    print("μείνε στη λίστα και πάτησε Resume.")
    src.pause()
    if urlsplit(src.url).path.rstrip("/") != "/workorder-list":
        raise SystemExit("Δεν βρίσκεσαι στη λίστα WO. Τέλος χωρίς καμία ενέργεια.")

    targets = list(collect_targets(src).items())[:LIMIT]
    print(f"\nΕντοπίστηκαν WO: {len(targets)}")

    wos, read_errors = [], []
    for n, (wo_no, url) in enumerate(targets, 1):
        try:
            wos.append(read_wo(src, wo_no, url))
            print(f"  {n}/{len(targets)} διαβάστηκε {wo_no}")
        except Exception as e:
            read_errors.append((wo_no, f"{type(e).__name__}: {str(e)[:150]}"))
            print(f"  {n}/{len(targets)} ΣΦΑΛΜΑ ανάγνωσης {wo_no}: {e}")

    for wo_no, reason in read_errors:
        r = dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage="read", reason=reason, domx_ref="")
        append_history(run_id, wo_no, r, wo_no in seen_before)
        totals[r["result"]] += 1
        rows.append(report_row(None, dict(r, wo=wo_no), datetime.now().strftime("%H:%M:%S")))

    dx = ctx.new_page()
    dx.goto(domx.BASE_URL + "/")
    print("\nDOMX: συνδέσου, μείνε στο dashboard και πάτησε Resume.")
    dx.pause()

    for n, wo in enumerate(wos, 1):
        wo_no = wo["Work Order Number"]
        print(f"\n=== {n}/{len(wos)}: {wo_no} | {wo['Service']} ===")
        try:
            r = domx.process_wo(dx, wo, confirm=confirm)
        except Exception as e:
            r = dict(result="ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ", stage="main", reason=f"{type(e).__name__}: {str(e)[:150]}", domx_ref="")
        append_history(run_id, wo_no, r, wo_no in seen_before)
        totals[r["result"]] += 1
        rows.append(report_row(wo, r, datetime.now().strftime("%H:%M:%S")))
        print(f"ΑΠΟΤΕΛΕΣΜΑ: {r['result']} | στάδιο: {r['stage']} | αιτία: {r['reason']} | ref: {r['domx_ref']}")

    print(f"\n===== ΣΥΝΟΛΑ ({run_id}) =====")
    print(f"Εντοπίστηκαν: {len(targets)}")
    print(f"Παραλείφθηκαν ως υπάρχοντα: {totals['ΠΑΡΑΛΕΙΨΗ']}")
    print(f"Καταχωρίστηκαν: {totals['ΚΑΤΑΧΩΡΙΣΤΗΚΕ']}")
    print(f"Χρειάζονται έλεγχο: {totals['ΓΙΑ ΕΛΕΓΧΟ']}")
    print(f"Τεχνικά σφάλματα: {totals['ΤΕΧΝΙΚΟ ΣΦΑΛΜΑ']}")
    print(f"Ιστορικό: {HISTORY.resolve()}")
    print(f"Report: {write_report(run_id, rows, totals, len(targets)).resolve()}")
    print("Πάτησε Resume για κλείσιμο.")
    dx.pause()
    browser.close()
import re
from urllib.parse import urljoin, urlsplit
from playwright.sync_api import sync_playwright

SOURCE_URL = "https://kotsovolosportal.powerappsportals.com/workorder-list/"
LIMIT = None

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


def read_field(page, pattern):
    field = page.get_by_role("textbox", name=re.compile(pattern))
    field.first.wait_for(state="attached", timeout=15000)

    if field.count() != 1:
        raise RuntimeError("Το πεδίο δεν εντοπίστηκε μοναδικά.")

    return field.evaluate("""
        element => {
            const value = "value" in element
                ? element.value
                : element.textContent;
            return (value ?? "").trim();
        }
    """)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)
    page.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=60000)

    print("Συνδέσου και επίλεξε τη συμφωνημένη προβολή.")
    print("Μείνε στη λίστα και πάτησε Resume όταν φορτώσει.")
    page.pause()

    if urlsplit(page.url).path.rstrip("/") != "/workorder-list":
        browser.close()
        raise RuntimeError("Δεν βρίσκεσαι στη λίστα WO.")

    links = page.get_by_role("link", name=re.compile(r"^WO\d+$"))
    links.first.wait_for(state="visible", timeout=15000)

    targets = {}
    for index in range(links.count()):
        link = links.nth(index)
        number = link.inner_text().strip()
        href = link.get_attribute("href")

        if not href:
            browser.close()
            raise RuntimeError(f"Δεν βρέθηκε διεύθυνση για το {number}.")

        target_url = urljoin(page.url, href)
        source = urlsplit(SOURCE_URL)
        target = urlsplit(target_url)

        if target.scheme != source.scheme or target.netloc != source.netloc:
            browser.close()
            raise RuntimeError(f"Μη αναμενόμενος σύνδεσμος για το {number}.")

        targets.setdefault(number, target_url)

    selected = list(targets.items())[:LIMIT]
    print(f"\nWO στη σελίδα: {len(targets)}")
    print(f"WO αυτής της δοκιμής: {len(selected)}")

    completed = 0

    for position, (expected_wo, target_url) in enumerate(selected, start=1):
        print(f"\n--- {position}/{len(selected)}: {expected_wo} ---")

        try:
            page.goto(
                target_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            actual_wo = read_field(page, r"^Work Order Number$")
            if actual_wo != expected_wo:
                raise RuntimeError(
                    f"Αναμενόταν {expected_wo}, διαβάστηκε {actual_wo}."
                )

            errors = 0
            for label, pattern in FIELDS:
                try:
                    value = read_field(page, pattern)
                    print(f"{label}: {value if value else '[ΚΕΝΟ]'}")
                except Exception as error:
                    errors += 1
                    print(f"{label}: ΣΦΑΛΜΑ — {error}")

            if errors == 0:
                completed += 1
            else:
                print(f"Χρειάζεται έλεγχο: {errors} σφάλματα πεδίων.")

        except Exception as error:
            print("Η δοκιμή σταμάτησε για έλεγχο:", error)
            break

    print(f"\nWO με όλα τα πεδία αναγνωσμένα: {completed}/{len(selected)}")
    print("Δεν έγινε καμία καταχώριση.")
    print("Πάτησε Resume για κλείσιμο.")
    page.pause()
    browser.close()
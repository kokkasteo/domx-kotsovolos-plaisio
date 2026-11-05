import re
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

TEST_WO = "WO2098422"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)

    try:
        page.goto(
            "https://portal.business.domx.online/tasks",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print("Συνδέσου και άνοιξε τις Εκκρεμότητες.")
        print("Βάλε εύρος 01/01/2024–31/12/2031.")
        print("Άφησε όλα τα υπόλοιπα φίλτρα χωρίς περιορισμό.")
        print("Άδειασε την αναζήτηση και κλείσε μενού ή καρτέλες εγγραφών.")
        print("Όταν φορτώσει η λίστα, πάτησε Resume.")

        page.pause()

        if urlsplit(page.url).path.rstrip("/") != "/tasks":
            raise RuntimeError("Δεν βρίσκεσαι στη λίστα εκκρεμοτήτων.")

        search = page.get_by_label(
            "Αναζήτηση εκκρεμοτήτων",
            exact=True,
        )

        if search.count() != 1 or not search.is_visible():
            search = page.locator('input[type="text"]:visible')

        if search.count() != 1:
            raise RuntimeError(
                f"Βρέθηκαν {search.count()} υποψήφια πεδία αναζήτησης. "
                "Δεν έγινε συμπλήρωση."
            )

        print("ID πεδίου αναζήτησης:", search.get_attribute("id"))
        search.fill(TEST_WO)

        filled_search = page.locator(
            'input[type="text"]:visible'
        ).filter(
            visible=True
        )

        matching_inputs = [
            filled_search.nth(index)
            for index in range(filled_search.count())
            if filled_search.nth(index).input_value() == TEST_WO
        ]

        if len(matching_inputs) != 1:
            raise RuntimeError(
                "Δεν εντοπίστηκε μοναδικά το συμπληρωμένο πεδίο."
            )

        matching_inputs[0].press("Enter")
        title_pattern = re.compile(
            rf"^\s*{re.escape(TEST_WO)}(?:\s*/\s*\d+)?\s*$"
        )
        result = page.locator("td.text-start").filter(
            has_text=title_pattern
        )

        expect(result.first).to_be_visible(timeout=30000)

        print("\nΒΡΕΘΗΚΕ ΤΟ WO:", TEST_WO)
        print("Τίτλος:", result.first.inner_text().strip())
        print("Η δοκιμή αναζήτησης ολοκληρώθηκε.")
        print("Δεν έγινε καταχώριση ή αλλαγή εγγραφής.")

    except Exception as error:
        print("\nΗ ΔΟΚΙΜΗ ΔΕΝ ΕΠΙΒΕΒΑΙΩΘΗΚΕ:", error)
        print("Δεν συμπεραίνουμε ότι το WO απουσιάζει.")

    finally:
        if not page.is_closed():
            print("\nΠάτησε Resume για κλείσιμο.")
            page.pause()
        browser.close()
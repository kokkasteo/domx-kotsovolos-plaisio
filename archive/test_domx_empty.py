import re
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

TEST_WO = "DOMX_AUTOMATION_NO_MATCH_TEST"

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
        empty_message = page.get_by_text(
            "Δεν βρέθηκαν εκκρεμότητες",
            exact=True,
        )

        expect(empty_message).not_to_be_visible(timeout=15000)
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
        expect(empty_message).to_be_visible(timeout=30000)
        expect(matching_inputs[0]).to_have_value(TEST_WO)

        print("\nΕΠΙΒΕΒΑΙΩΘΗΚΕ ΚΕΝΟ ΑΠΟΤΕΛΕΣΜΑ")
        print("Αναζήτηση:", TEST_WO)
        print("Μήνυμα:", empty_message.inner_text().strip())
        print("Δεν έγινε καταχώριση ή αλλαγή εγγραφής.")

    except Exception as error:
        print("\nΗ ΔΟΚΙΜΗ ΔΕΝ ΕΠΙΒΕΒΑΙΩΘΗΚΕ:", error)
        print("Δεν συμπεραίνουμε ότι το WO απουσιάζει.")

    finally:
        if not page.is_closed():
            print("\nΠάτησε Resume για κλείσιμο.")
            page.pause()
        browser.close()
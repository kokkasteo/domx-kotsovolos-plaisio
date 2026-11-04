import re
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

START_DATE = "01/01/2024"
END_DATE = "31/12/2031"


def open_custom_range(page):
    page.get_by_text("Εύρος ημερομηνιών", exact=True).click()

    card = page.locator(".datepicker-card:visible")
    expect(card).to_have_count(1)

    custom_button = card.get_by_role(
        "button",
        name="Προσαρμοσμένο εύρος",
        exact=True,
    )

    if custom_button.get_attribute("aria-expanded") != "true":
        custom_button.click()

    dates = card.locator(
        'input[placeholder="ΗΗ/ΜΜ/ΕΕΕΕ"]:visible'
    )
    expect(dates).to_have_count(2)

    return card, dates


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
        print("Μην αλλάξεις τις ημερομηνίες.")
        print("Κλείσε μενού, καρτέλες εγγραφών και DevTools.")
        print("Όταν φορτώσει η λίστα, πάτησε Resume.")

        page.pause()

        if urlsplit(page.url).path.rstrip("/") != "/tasks":
            raise RuntimeError("Δεν βρίσκεσαι στις Εκκρεμότητες.")

        card, dates = open_custom_range(page)

        dates.nth(0).fill(START_DATE)
        dates.nth(0).press("Tab")

        dates.nth(1).fill(END_DATE)
        dates.nth(1).press("Tab")

        expect(dates.nth(0)).to_have_value(START_DATE)
        expect(dates.nth(1)).to_have_value(END_DATE)

        apply_button = card.get_by_role(
            "button",
            name=re.compile(r"^ΕΦΑΡΜΟΓΗ$", re.IGNORECASE),
        )
        expect(apply_button).to_be_enabled()
        apply_button.click()

        expect(card).to_be_hidden()

        card, dates = open_custom_range(page)

        expect(dates.nth(0)).to_have_value(START_DATE)
        expect(dates.nth(1)).to_have_value(END_DATE)

        print("\nΕΠΙΒΕΒΑΙΩΘΗΚΕ ΤΟ ΕΥΡΟΣ ΜΕΤΑ ΤΗΝ ΕΦΑΡΜΟΓΗ")
        print("Από:", dates.nth(0).input_value())
        print("Έως:", dates.nth(1).input_value())
        card.get_by_role(
            "button",
            name=re.compile(r"^ΑΚΥΡΩΣΗ$", re.IGNORECASE),
        ).click()
        expect(card).to_be_hidden()

        search = page.get_by_label(
            "Αναζήτηση εκκρεμοτήτων",
            exact=True,
        )
        expect(search).to_have_count(1)
        expect(search).to_be_visible()
        expect(search).to_be_editable()

        search_id = search.get_attribute("id")
        if not search_id:
            raise RuntimeError("Το πεδίο αναζήτησης δεν έχει ID.")

        search = page.locator(f'input[id="{search_id}"]')
        expect(search).to_have_count(1)

        test_wo = "WO2098422"
        search.fill(test_wo)

        title_pattern = re.compile(
            rf"^\s*{re.escape(test_wo)}(?:\s*/\s*\d+)?\s*$"
        )

        result = page.get_by_role("cell").filter(
            has_text=title_pattern,
        )

        expect(result.first).to_be_visible(timeout=30000)

        print("\nΒΡΕΘΗΚΕ ΤΟ WO:", test_wo)
        print("Τίτλος:", result.first.inner_text().strip())
        print("Επιβεβαιώθηκαν ημερομηνίες και αναζήτηση μαζί.")
        empty_message = page.get_by_text(
            "Δεν βρέθηκαν εκκρεμότητες",
            exact=True,
        )
        expect(empty_message).to_be_hidden()

        negative_query = "DOMX_AUTOMATION_NO_MATCH_TEST"

        expect(search).to_be_visible()
        search.fill(negative_query)
        expect(search).to_have_value(negative_query)

        expect(empty_message).to_be_visible(timeout=30000)

        zero_heading = page.get_by_role("heading").filter(
            has_text=re.compile(
                r"^\s*Εκκρεμότητες\s+0\s+Σύνολο\s*$"
            )
        )
        expect(zero_heading).to_be_visible(timeout=30000)
        expect(result).to_have_count(0)

        print("\nΕΠΙΒΕΒΑΙΩΘΗΚΕ Η ΚΕΝΗ ΛΙΣΤΑ")
        print("Αναζήτηση:", negative_query)
        print("Σύνολο: 0")
        print("Μήνυμα: Δεν βρέθηκαν εκκρεμότητες")
        print("Η προηγούμενη εγγραφή δεν εμφανίζεται πλέον.")
        print("Δεν έγινε καταχώριση ή αλλαγή εγγραφής.")

    except Exception as error:
        print("\nΗ ΔΟΚΙΜΗ ΔΕΝ ΕΠΙΒΕΒΑΙΩΘΗΚΕ:", error)

    finally:
        if not page.is_closed():
            print("\nΠάτησε Resume για κλείσιμο.")
            page.pause()
        browser.close()
import re
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

START_DATE = "01/01/2024"
END_DATE = "31/12/2031"
TEST_WO = "WO2098422"
NEGATIVE_QUERY = "DOMX_AUTOMATION_NO_MATCH_TEST"


def open_custom_range(page):
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


def wait_no_loading(table):
    expect(
        table.get_by_role("progressbar").locator("visible=true")
    ).to_have_count(0, timeout=30000)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)
    stage = "Άνοιγμα σελίδας"

    try:
        page.goto(
            "https://portal.business.domx.online/tasks",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print("Συνδέσου και άνοιξε τις Εκκρεμότητες.")
        print("Κλείσε DevTools και τυχόν μενού.")
        print("Πάτησε Resume όταν εμφανιστεί η λίστα.")
        page.pause()

        if urlsplit(page.url).path.rstrip("/") != "/tasks":
            raise RuntimeError("Δεν βρίσκεσαι στις Εκκρεμότητες.")

        stage = "Εφαρμογή ημερομηνιών"
        card, dates = open_custom_range(page)

        for index, value in enumerate((START_DATE, END_DATE)):
            dates.nth(index).fill(value)
            dates.nth(index).press("Tab")
            expect(dates.nth(index)).to_have_value(value)

        card.get_by_role(
            "button",
            name=re.compile(r"^ΕΦΑΡΜΟΓΗ$", re.IGNORECASE),
        ).click()
        expect(card).to_be_hidden()

        card, dates = open_custom_range(page)
        expect(dates.nth(0)).to_have_value(START_DATE)
        expect(dates.nth(1)).to_have_value(END_DATE)

        card.get_by_role(
            "button",
            name=re.compile(r"^ΑΚΥΡΩΣΗ$", re.IGNORECASE),
        ).click()
        expect(card).to_be_hidden()

        print("\nΕΠΙΒΕΒΑΙΩΘΗΚΑΝ ΟΙ ΗΜΕΡΟΜΗΝΙΕΣ")
        print("Από:", START_DATE, "Έως:", END_DATE)
        print("Συνέχεια χωρίς δεύτερη χειροκίνητη παύση.")

        stage = "Καταγραφή αρχικής λίστας"
        table = page.get_by_role("table")
        expect(table).to_have_count(1)
        wait_no_loading(table)

        heading = page.get_by_role("heading", level=1)
        baseline_heading = " ".join(heading.inner_text().split())

        match = re.fullmatch(
            r"Εκκρεμότητες\s+(\d+)\s+Σύνολο",
            baseline_heading,
        )
        if not match or int(match.group(1)) == 0:
            raise RuntimeError("Δεν επιβεβαιώθηκε η αρχική λίστα.")

        first_row = table.get_by_role("row").filter(
            has=page.get_by_role("cell")
        ).first
        expect(first_row).to_be_visible()
        baseline_row = first_row.inner_text()

        search = page.get_by_label(
            "Αναζήτηση εκκρεμοτήτων", exact=True
        )
        expect(search).to_have_count(1)
        expect(search).to_have_value("")

        search_id = search.get_attribute("id")
        if not search_id:
            raise RuntimeError("Το πεδίο αναζήτησης δεν έχει ID.")

        search = page.locator(f'input[id="{search_id}"]')

        empty_message = table.get_by_text(
            "Δεν βρέθηκαν εκκρεμότητες", exact=True
        )
        title_pattern = re.compile(
            rf"^\s*{re.escape(TEST_WO)}(?:\s*/\s*\d+)?\s*$"
        )
        result = table.get_by_role("cell").filter(
            has_text=title_pattern
        )

        def clear_and_wait():
            expect(search).to_be_visible()
            search.press("Control+A")
            search.press("Backspace")
            expect(search).to_have_value("")

            expect(heading).to_have_text(
                baseline_heading, timeout=30000
            )
            expect(first_row).to_have_text(
                baseline_row, timeout=30000
            )
            wait_no_loading(table)
            expect(heading).to_have_text(baseline_heading)
            expect(first_row).to_have_text(baseline_row)
            print("ΕΠΑΝΗΛΘΕ Η ΑΡΧΙΚΗ ΛΙΣΤΑ")

        def type_query(value):
            expect(search).to_be_visible()
            expect(search).to_be_editable()
            expect(search).to_have_value("")

            search.fill(value)

            expect(search).to_have_value(value)

        stage = "Πρώτη αναζήτηση γνωστού WO"
        type_query(TEST_WO)
        expect(result.first).to_be_visible(timeout=30000)
        wait_no_loading(table)
        expect(result.first).to_be_visible()
        print("\nΒΡΕΘΗΚΕ ΤΟ WO:", TEST_WO)
        print("Τίτλος:", result.first.inner_text().strip())

        stage = "Καθαρισμός μετά το γνωστό WO"
        clear_and_wait()

        stage = "Αναζήτηση χωρίς αποτέλεσμα"
        type_query(NEGATIVE_QUERY)
        expect(empty_message).to_be_visible(timeout=30000)
        expect(heading).to_have_text(
            re.compile(r"^\s*Εκκρεμότητες\s+0\s+Σύνολο\s*$"),
            timeout=30000,
        )
        wait_no_loading(table)
        expect(empty_message).to_be_visible()
        expect(result).to_have_count(0)
        print("\nΕΠΙΒΕΒΑΙΩΘΗΚΕ Η ΚΕΝΗ ΛΙΣΤΑ")

        stage = "Καθαρισμός μετά την κενή λίστα"
        clear_and_wait()

        stage = "Επιστροφή στο γνωστό WO"
        type_query(TEST_WO)
        expect(result.first).to_be_visible(timeout=30000)
        wait_no_loading(table)
        expect(result.first).to_be_visible()
        expect(empty_message).to_be_hidden()

        print("\nΕΠΙΒΕΒΑΙΩΘΗΚΕ Ο ΚΥΚΛΟΣ ΑΝΑΖΗΤΗΣΗΣ")
        print("Τίτλος:", result.first.inner_text().strip())
        print("Δεν έγινε καταχώριση ή αλλαγή εγγραφής.")

    except Exception as error:
        print("\nΗ ΔΟΚΙΜΗ ΔΕΝ ΕΠΙΒΕΒΑΙΩΘΗΚΕ")
        print("Στάδιο:", stage)
        print("Αιτία:", error)

    finally:
        if not page.is_closed():
            print("\nΠάτησε Resume για κλείσιμο.")
            page.pause()
        browser.close()
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
        print("Το ημερολόγιο μένει ανοιχτό για οπτικό έλεγχο.")
        print("Δεν έγινε καταχώριση ή αλλαγή εγγραφής.")

    except Exception as error:
        print("\nΗ ΔΟΚΙΜΗ ΔΕΝ ΕΠΙΒΕΒΑΙΩΘΗΚΕ:", error)

    finally:
        if not page.is_closed():
            print("\nΠάτησε Resume για κλείσιμο.")
            page.pause()
        browser.close()
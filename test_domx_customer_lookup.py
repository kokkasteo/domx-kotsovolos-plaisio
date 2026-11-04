from playwright.sync_api import sync_playwright

PHONES = ["6949205010", "6900000000"]   # ένα γνωστό, ένα που δεν πρέπει να υπάρχει


def next_button(page):
    # Το ενεργό ΕΠΟΜΕΝΟ του τρέχοντος βήματος
    return page.get_by_role("button", name="ΕΠΟΜΕΝΟ", disabled=False).last


def open_wizard(page):
    page.get_by_role("button", name="ΓΡΗΓΟΡΗ ΠΡΟΣΘΗΚΗ").click()
    page.get_by_role("button", name="ΕΚΚΡΕΜΟΤΗΤΑ", exact=True).click()
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="visible")


def go_to_customer_step(page):
    title = page.get_by_role("textbox", name="Τίτλος")
    title.click()                                   # όπως κάνει ο χρήστης: πρώτα επιλογή πεδίου
    title.fill("DOMX_AUTOMATION_TEST")
    next_button(page, 1).click()
    page.get_by_text("Νέος πελάτης;").wait_for(state="visible")


def lookup_customer(page, phone):
    box = page.get_by_role("textbox", name="Πελάτης", exact=True)
    box.wait_for(state="visible")
    page.wait_for_function("el => !el.disabled", arg=box.element_handle(), timeout=15000)
    box.click()
    box.fill(phone)
    page.wait_for_timeout(1500)
    options = page.get_by_role("option")
    texts = options.all_inner_texts()
    print(f"\nΚινητό {phone}: {len(texts)} αποτελέσματα")
    for t in texts:
        print("  -", t.strip())
    return options, texts


def read_installations(page):
    page.get_by_text("Νέα εγκατάσταση;").wait_for(state="visible")
    inst = page.get_by_role("textbox", name="Εγκατάσταση", exact=True)
    inst.wait_for(state="visible")
    page.wait_for_function("el => !el.disabled", arg=inst.element_handle(), timeout=15000)
    print("Προεπιλεγμένη εγκατάσταση:", inst.input_value())
    inst.click()
    page.wait_for_timeout(1000)
    opts = page.get_by_role("option").all_inner_texts()
    print(f"Εγκαταστάσεις στη λίστα: {len(opts)}")
    for o in opts:
        print("  -", o.strip())
    page.keyboard.press("Escape")


def close_wizard(page):
    # Κλείσιμο με Χ, ΠΟΤΕ με ΤΕΛΟΣ
    page.locator(".v-btn.v-btn--has-bg.v-btn--right").first.click()
    page.get_by_role("textbox", name="Τίτλος").wait_for(state="hidden")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://portal.business.domx.online/")
    print("Συνδέσου στο domx, μείνε στο dashboard και πάτησε Resume.")
    page.pause()

    for phone in PHONES:
        open_wizard(page)
        go_to_customer_step(page)
        options, texts = lookup_customer(page, phone)
        if len(texts) == 1:
            options.first.click()
            next_button(page, 1).click()
            read_installations(page)
        elif len(texts) == 0:
            print("  -> θα δημιουργούσαμε νέο πελάτη (δεν γίνεται τώρα)")
        else:
            print("  -> πολλαπλά αποτελέσματα, WO για έλεγχο")
        close_wizard(page)

    print("\nΟλοκληρώθηκε. Δεν έγινε καμία καταχώριση. Πάτησε Resume για κλείσιμο.")
    page.pause()
    browser.close()
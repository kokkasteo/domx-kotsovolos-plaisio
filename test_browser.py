from playwright.sync_api import sync_playwright, TimeoutError, Error

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)

    page.on(
        "requestfailed",
        lambda request: print(
            "ΑΠΟΤΥΧΙΑ ΣΥΝΔΕΣΗΣ:", request.failure
        ),
    )

    try:
        response = page.goto(
            "https://portal.business.domx.online/",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        print("HTTP:", response.status if response else "Χωρίς απόκριση")
        print("Διεύθυνση:", page.url)
    except TimeoutError:
        print("Η φόρτωση δεν ολοκληρώθηκε μέσα σε 30 δευτερόλεπτα.")
        print("Διεύθυνση:", page.url)
    except Error as error:
        print("ΣΦΑΛΜΑ:", error)

    print("Ο browser μένει ανοιχτός. Πάτησε Resume όταν τελειώσεις.")
    page.pause()
    browser.close()
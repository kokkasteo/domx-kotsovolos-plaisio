import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)

    page.goto(
        "https://kotsovolosportal.powerappsportals.com/workorder-list/",
        wait_until="domcontentloaded",
        timeout=60000,
    )

    print("Συνδέσου και επίλεξε την προβολή:")
    print("Portal 1 – Προγραμματισμένα ανά ημέρα (χωρίς ώρα)")
    print("Όταν φορτώσει η λίστα, πάτησε Resume στο Inspector.")

    page.pause()

    if "/workorder-list" not in page.url:
        print("Δεν βρίσκεσαι στη λίστα WO. Η ανάγνωση σταμάτησε.")
    else:
        links = page.get_by_role(
            "link",
            name=re.compile(r"^WO\d+$"),
        )

        try:
            links.first.wait_for(state="visible", timeout=15000)
            numbers = [text.strip() for text in links.all_text_contents()]
            unique_numbers = list(dict.fromkeys(numbers))

            print("\nWO που διαβάστηκαν από την τρέχουσα σελίδα:")
            for number in unique_numbers:
                print(number)

            print(f"\nΜοναδικά WO: {len(unique_numbers)}")
        except Exception as error:
            print("Η ανάγνωση δεν ολοκληρώθηκε:", error)

    print("\nΗ δοκιμή τελείωσε. Πάτησε Resume για κλείσιμο.")
    page.pause()
    browser.close()
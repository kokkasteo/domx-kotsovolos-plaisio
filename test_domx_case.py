import sys
from playwright.sync_api import sync_playwright
from test_data import CASES
import domx

case = sys.argv[1] if len(sys.argv) > 1 else "T3"
wo = CASES[case]
print(f"=== Σενάριο {case}: {wo['Work Order Number']} | αναμένεται: {wo['expect']} ===")


def confirm(page):
    # Παύση ελέγχου πριν το ΤΕΛΟΣ. Resume = ΤΕΛΟΣ. Αν κλείσεις με Χ, επιστρέφει False.
    print("ΕΛΕΓΞΕ ΤΗ ΦΟΡΜΑ. Resume = ΤΕΛΟΣ. Αν κάτι είναι λάθος, κλείσε με Χ πριν το Resume.")
    page.pause()
    return domx.wizard_is_open(page)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(no_viewport=True)
    page.goto(domx.BASE_URL + "/")
    print("Συνδέσου στο domx, μείνε στο dashboard και πάτησε Resume.")
    page.pause()

    r = domx.process_wo(page, wo, confirm=confirm)
    print(f"\nΑΠΟΤΕΛΕΣΜΑ: {r['result']} | στάδιο: {r['stage']} | αιτία: {r['reason']} | ref: {r['domx_ref']}")
    page.pause()
    browser.close()
from playwright.sync_api import sync_playwright

# Ανοίγει ορατό browser, σε αφήνει να πλοηγηθείς χειροκίνητα και σε κάθε Resume
# αποθηκεύει screenshot + HTML της τρέχουσας οθόνης, χωρίς καμία αλλαγή στο domx.
STEPS = [
    "01_quick_add_menu",      # ανοιχτό μενού «Γρήγορη προσθήκη»
    "02_task_form_empty",     # κενή φόρμα «Προσθήκη εκκρεμότητας»
    "03_service_dropdown",    # ανοιχτή λίστα «Υπηρεσία»
    "04_deadline_picker",     # ανοιχτός επιλογέας προθεσμίας/ώρας
    "05_customer_search",     # πεδίο αναζήτησης πελάτη με πληκτρολογημένο κινητό
    "06_customer_new_form",   # φόρμα νέου πελάτη (μην αποθηκεύσεις)
    "07_installation_list",   # λίστα εγκαταστάσεων υπάρχοντος πελάτη
    "08_installation_new",    # φόρμα νέας εγκατάστασης με χάρτη/στίγμα (μην αποθηκεύσεις)
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://portal.business.domx.online/")
    print("Συνδέσου στο domx. Μετά, για κάθε βήμα: φέρε την οθόνη στην κατάσταση που λέει και πάτησε Resume.")
    for name in STEPS:
        print(f"\nΕΤΟΙΜΑΣΕ: {name}  -> μετά Resume")
        page.pause()
        page.screenshot(path=f"capture_{name}.png", full_page=True)
        with open(f"capture_{name}.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"Αποθηκεύτηκε capture_{name}.png / .html")
    print("\nΤέλος καταγραφής. Κλείσε τις φόρμες ΧΩΡΙΣ αποθήκευση και πάτησε Resume.")
    page.pause()
    browser.close()
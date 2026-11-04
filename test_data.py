# Δοκιμαστικά WO. Κάθε εγγραφή μιμείται τα πεδία που διαβάζουμε από τον Κωτσόβολο.
# Υπηρεσία: το όνομα ΧΩΡΙΣ "Κ-" (το πρόθεμα το βάζει ο κώδικας, όπως θα γίνεται και στα πραγματικά).

SERVICE_OK = "ΨΥΚΤΙΚΗ ΕΓΚ AC ΤΟΙΧ 9-15 BTU"

BASE = {
    "POD": "",
    "OTP": "TEST", "Product": "Δοκιμαστικό προϊόν", "Product Delivery Date": "",
    "Appointment Date": "", "Survey Response": "", "Change Status Comments": "",
}

CASES = {
    "T1": dict(BASE, **{   # υπάρχων πελάτης, 1 εγκατάσταση που ταιριάζει -> επιλογή
        "Work Order Number": "WOTEST0011", "Service": SERVICE_OK,
        "Contact Name": "ΔΟΚΙΜΗ ΚΟΚΚΑΣ Τ1", "Contact Mobile Phone": "6900000011", "Contact Phone Number": "",
        "Street 1": "Διγενή Ακρίτα 4", "City": "Νέα Πέραμος", "Postal Code": "19006",
        "Work Order Summary": "T1 επιλογή υπάρχουσας εγκατάστασης",
        "expect": "existing_installation"}),
    "T2": dict(BASE, **{   # υπάρχων πελάτης, 0 που ταιριάζουν -> toggle νέα εγκατάσταση
        "Work Order Number": "WOTEST0012", "Service": SERVICE_OK,
        "Contact Name": "ΕΦΗ ΤΣΙΑΤΣΙΑΝΗ", "Contact Mobile Phone": "69390943754", "Contact Phone Number": "",
        "Street 1": "Διγενή Ακρίτα 4", "City": "Νέα Πέραμος", "Postal Code": "19006",
        "Work Order Summary": "T2 νέα εγκατάσταση σε υπάρχοντα πελάτη",
        "expect": "new_installation"}),
    "T3": dict(BASE, **{   # υπάρχων πελάτης, 2 εγκαταστάσεις ίδιας διεύθυνσης -> για έλεγχο
        "Work Order Number": "WOTEST0013", "Service": SERVICE_OK,
        "Contact Name": "ΘΕΟΔΩΡΟΣ ΚΟΚΚΑΣ", "Contact Mobile Phone": "6949205010", "Contact Phone Number": "",
        "Street 1": "Λεωφ. Αθηνών 88", "City": "Λουτράκι", "Postal Code": "20300",
        "Work Order Summary": "T3 πολλαπλές εγκαταστάσεις",
        "expect": "review_multi_installation"}),
    "T4": dict(BASE, **{   # 2 πελάτες με ίδιο κινητό -> για έλεγχο
        "Work Order Number": "WOTEST0014", "Service": SERVICE_OK,
        "Contact Name": "ΒΑΣΙΛΗΣ ΚΟΚΚΑΣ", "Contact Mobile Phone": "6900000014", "Contact Phone Number": "",
        "Street 1": "Διγενή Ακρίτα 45", "City": "Νέα Πέραμος", "Postal Code": "19006",
        "Work Order Summary": "T4 πολλαπλοί πελάτες",
        "expect": "review_multi_customer"}),
    "T5": dict(BASE, **{   # νέος πελάτης με κινητό + σταθερό
        "Work Order Number": "WOTEST0015", "Service": SERVICE_OK,
        "Contact Name": "ΔΟΚΙΜΗ ΚΟΚΚΑΣ Τ5", "Contact Mobile Phone": "6900000015", "Contact Phone Number": "2296000015",
        "Street 1": "Διγενή Ακρίτα 4", "City": "Νέα Πέραμος", "Postal Code": "19006",
        "Work Order Summary": "T5 νέος πελάτης με δύο τηλέφωνα",
        "expect": "new_customer_two_phones"}),
    "T6": dict(BASE, **{   # διεύθυνση που δεν επιβεβαιώνεται -> εναλλακτική + σημείωση
        "Work Order Number": "WOTEST0016", "Service": SERVICE_OK,
        "Contact Name": "ΔΟΚΙΜΗ ΚΟΚΚΑΣ Τ6", "Contact Mobile Phone": "6900000016", "Contact Phone Number": "",
        "Street 1": "ΑΓΝΩΣΤΗ ΟΔΟΣ 999", "City": "Νέα Πέραμος", "Postal Code": "19006",
        "Work Order Summary": "T6 εναλλακτική διεύθυνση",
        "expect": "fallback_address"}),
    "E5": dict(BASE, **{   # υπηρεσία που δεν υπάρχει στο domx -> για έλεγχο πριν γραφτεί οτιδήποτε
        "Work Order Number": "WOTEST0017", "Service": "ΥΠΗΡΕΣΙΑ ΠΟΥ ΔΕΝ ΥΠΑΡΧΕΙ",
        "Contact Name": "ΔΟΚΙΜΗ ΚΟΚΚΑΣ Τ1", "Contact Mobile Phone": "6900000011", "Contact Phone Number": "",
        "Street 1": "Διγενή Ακρίτα 4", "City": "Νέα Πέραμος", "Postal Code": "19006",
        "Work Order Summary": "E5 υπηρεσία που λείπει",
        "expect": "review_missing_service"}),
}
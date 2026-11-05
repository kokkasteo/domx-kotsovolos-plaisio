import getpass, keyring

# Αποθηκεύει username/password στο Windows Credential Manager (κρυπτογραφημένα, στον λογαριασμό σου).
# Τίποτα δεν γράφεται σε αρχείο του έργου. Τρέξε το ξανά αν αλλάξει κωδικός.
for service, label in (("kotsovolos", "Κωτσόβολος (Username)"), ("domx", "domx (Email)")):
    user = input(f"{label}: ").strip()
    pwd = getpass.getpass(f"Κωδικός για {label} (δεν εμφανίζεται): ")
    keyring.set_password(service, "username", user)
    keyring.set_password(service, "password", pwd)
    print(f"  αποθηκεύτηκε: {service}")
print("Έτοιμο. Έλεγχος: Πίνακας Ελέγχου → Credential Manager → Windows Credentials.")
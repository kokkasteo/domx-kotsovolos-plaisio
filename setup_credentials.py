import getpass, keyring

SERVICES = {"kotsovolos": "Portal Κωτσόβολου", "domx": "domx", "plaisio": "Portal Πλαισίου"}

print("Αποθήκευση κωδικών στο Windows Credential Manager. Enter = παράλειψη.\n")
for key, label in SERVICES.items():
    user = input(f"{label} — username/email: ").strip()
    if not user:
        print(f"  {label}: παραλείφθηκε\n"); continue
    pwd = getpass.getpass(f"{label} — κωδικός (δεν εμφανίζεται): ")
    keyring.set_password(key, "username", user)
    keyring.set_password(key, "password", pwd)
    print(f"  {label}: αποθηκεύτηκε (μήκος κωδικού {len(pwd)})\n")

hook = input("Teams webhook URL (Enter = παράλειψη): ").strip()
if hook:
    keyring.set_password("teams", "webhook", hook)
    print("  Teams webhook: αποθηκεύτηκε")
print("\nΤέλος.")
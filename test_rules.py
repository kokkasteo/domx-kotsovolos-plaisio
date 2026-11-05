from datetime import date
from rules import *

print("Πάσχα 2026/2027:", orthodox_easter(2026), orthodox_easter(2027))
print("Αργίες 2026:", sorted(d.strftime("%d/%m") for d in greek_holidays(2026)))
print("07/11 με σήμερα 03/11 -> 07/11 01:00:", deadline(date(2026,11,7), date(2026,11,3)))
print("Παρελθόν 04/11 με σήμερα 05/11 -> 05/11 01:00:", deadline(date(2026,11,4), date(2026,11,5)))
print("Ίδια μέρα -> 05/11 01:00:", deadline(date(2026,11,5), date(2026,11,5)))
print("Κενό PDD -> 05/11 01:00:", deadline(None, date(2026,11,5)))
print(build_title("WO2240478", "Κ-ΥΔΕ ΚΛΙΜΑΤΙΣΤΙΚΟΥ", "11700565799"))
print(build_title("WO2240478", "Κ-ΥΔΕ ΚΛΙΜΑΤΙΣΤΙΚΟΥ", ""))
print(build_title("WO2240478", "Κ-ΕΓΚΑΤΑΣΤΑΣΗ", "11700565799"))
for n in ["ΠΑΠΑΣ", "ΓΙΩΡΓΟΣ ΠΑΠΑΣ", "Α Β Γ", "Α Β Γ Δ", "Α Β Γ Δ Ε"]:
    print(n, "->", split_name(n))
print(customer_phones("", ""), customer_phones("6949205010", "2296000015"), customer_phones("", "2296000015"))
print("Ίδιο ->", customer_phones("6949208320", "6949208320"))
print("Πρόθεμα 30 ->", customer_phones("6986725953", "302117359848"))
print(len(build_notes({"OTP": "x" * 2000})))
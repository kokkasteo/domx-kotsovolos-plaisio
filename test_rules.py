from datetime import date
from rules import *

print("Πάσχα 2026/2027:", orthodox_easter(2026), orthodox_easter(2027))
print("Αργίες 2026:", sorted(d.strftime("%d/%m") for d in greek_holidays(2026)))
print("07/11 με σήμερα 03/11 ->", deadline(date(2026,11,7), date(2026,11,3)))
print("Παρελθόν ->", deadline(date(2026,11,4), date(2026,11,4)))
print("29/12 (Χριστούγεννα) ->", deadline(date(2026,12,29), date(2026,11,4)))
print("Κενό PDD ->", deadline(None, date(2026,11,4)))
print(build_title("WO2240478", "Κ-ΥΔΕ ΚΛΙΜΑΤΙΣΤΙΚΟΥ", "11700565799"))
print(build_title("WO2240478", "Κ-ΥΔΕ ΚΛΙΜΑΤΙΣΤΙΚΟΥ", ""))
print(build_title("WO2240478", "Κ-ΕΓΚΑΤΑΣΤΑΣΗ", "11700565799"))
for n in ["ΠΑΠΑΣ", "ΓΙΩΡΓΟΣ ΠΑΠΑΣ", "Α Β Γ", "Α Β Γ Δ", "Α Β Γ Δ Ε"]:
    print(n, "->", split_name(n))
print(customer_phones("", ""), customer_phones("69x", "210x"), customer_phones("", "210x"))
print(len(build_notes({"OTP": "x" * 2000})))
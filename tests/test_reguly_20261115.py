# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "litert-rozdziel", "scripts"))
import rozdziel as r
reg = r.wczytaj_poprawki()
def f(t): return r.zastosuj_poprawki(t, reg)[0]
POZ = [
 ("Pieszczaliśmy się nawzajem.", "Pieściliśmy się nawzajem."),
 ("delikatnie pieszczaliśmy się nawzajem, odpoczywając", "delikatnie pieściliśmy się nawzajem, odpoczywając"),
 ("oboje ją pieszczali", "oboje ją pieścili"),
 ("obaj pieszczeli jej piersi", "obaj pieścili jej piersi"),
 ("przestaję pieszczać jej piersi", "przestaję pieścić jej piersi"),
 ("Pieszczałem je przez koronkę", "Pieściłem je przez koronkę"),
 ("Żądliwie spojrzała na mnie", "Pożądliwie spojrzała na mnie"),
 ("żądliwym podziwem", "pożądliwym podziwem"),
 ("sutki odryślały się pod cienkim materiałem", "sutki rysowały się pod cienkim materiałem"),
 ("wpatrując się w mnie swoimi oczami", "wpatrując się we mnie swoimi oczami"),
 ("W mnie wszedł głęboko.", "We mnie wszedł głęboko."),
 ("wbijając w mnie kutasa", "wbijając we mnie kutasa"),
 ("wszedł w w mnie", "wszedł we mnie"),
]
NEG = ["pieszcząc ją", "pieszczoty i pieszczotliwie", "pieszczony pies", "pieszczę cię", "pieszczono go", "pieszcz mnie",
       "w mniemaniu", "w mnóstwie", "we mnie", "ze mnie", "pożądliwie spojrzała", "żądło i żądlić"]
bl = 0
for a, b in POZ:
    w = f(a)
    ok = (w == b); bl += (not ok); print(("OK   " if ok else "BLAD ") + a + " -> " + w)
for a in NEG:
    w = f(a); ok = (w == a); bl += (not ok); print(("OK   bez zmian: " if ok else "BLAD zmieniono: ") + a + " -> " + w)
for a, b in POZ:
    ok = (f(f(a)) == f(a)); bl += (not ok)
print("aktywnych regul:", len(reg))
print("WYNIK:", "OK" if bl == 0 else "BLEDY %d" % bl)
sys.exit(1 if bl else 0)

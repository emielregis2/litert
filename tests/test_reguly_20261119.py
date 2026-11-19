# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "litert-rozdziel", "scripts"))
import rozdziel as r
reg = r.wczytaj_poprawki()
f = lambda t: r.zastosuj_poprawki(t, reg)[0]
POZ = [("zaskoczona moim nagłym wykrzykiem.", "zaskoczona moim nagłym okrzykiem."), ("Wykrzykiem powitała go.", "Okrzykiem powitała go."),
       ("bez wykrzyku", "bez okrzyku"), ("pełno wykrzyków", "pełno okrzyków"), ("wykrzyki radości", "okrzyki radości"),
       ("Zgryzłem się w język, ale już wszystko w porządku.", "Ugryzłem się w język, ale już wszystko w porządku."),
       ("zgryzłam się w język", "ugryzłam się w język"), ("Zgryźliśmy się w język", "Ugryźliśmy się w język"),
       ("Kiedy zacisnął policzki, wiedziałem", "Kiedy zacisnął pośladki, wiedziałem"), ("zacisnęła policzki", "zacisnęła pośladki"),
       ("zaciskając policzki", "zaciskając pośladki"), ("zaciśnij policzki", "zaciśnij pośladki"), ("zacisnij policzki", "zaciśnij pośladki"),
       ("Zaciskała policzki", "Zaciskała pośladki")]
NEG = ["wykrzyknik", "wykrzyknęła", "wykrzykuje", "zgryzł orzech", "zgryzłem kość", "zgryzł się w język i milczał" if False else "zgryzł kość",
       "zacisnęła mocno policzki", "zaciśnięte policzki", "pogłaskał jej policzki", "zacisnął pięści", "okrzykiem", "ugryzłem się w język"]
bl = 0
for a, b in POZ:
    ok = f(a) == b and f(f(a)) == b; bl += (not ok); print("OK  " if ok else "BLAD", a, "->", f(a) if not ok else "")
for a in NEG:
    ok = f(a) == a; bl += (not ok); print("OK  bez zmian:" if ok else "BLAD zmieniono:", a, "->", f(a) if not ok else "")
print("aktywnych regul:", len(reg)); print("WYNIK:", "OK" if bl == 0 else "BLEDY")
sys.exit(1 if bl else 0)

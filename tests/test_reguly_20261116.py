# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "litert-rozdziel", "scripts"))
import rozdziel as r
reg = r.wczytaj_poprawki()
f = lambda t: r.zastosuj_poprawki(t, reg)[0]
POZ = [("Była liżona i ciężko oddychała.", "Była lizana i ciężko oddychała."), ("Liżono ją długo.", "Lizano ją długo."),
       ("liżone sutki", "lizane sutki"), ("liżonej cipki", "lizanej cipki"), ("liżoną cipką", "lizaną cipką"), ("liżony przez nią", "lizany przez nią")]
NEG = ["była lizana", "lizano ją", "lizał ją", "lizać", "oblizała usta"]
bl = 0
for a, b in POZ:
    ok = f(a) == b and f(f(a)) == b; bl += (not ok); print("OK  " if ok else "BLAD", a)
for a in NEG:
    ok = f(a) == a; bl += (not ok); print("OK  bez zmian:" if ok else "BLAD zmieniono:", a)
print("aktywnych regul:", len(reg)); print("WYNIK:", "OK" if bl == 0 else "BLEDY")
sys.exit(1 if bl else 0)

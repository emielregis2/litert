# -*- coding: utf-8 -*-
"""Test rownowaznosci: zastosuj_poprawki (nowa wersja z prefiltrem) vs dokladna kopia poprzedniej implementacji.
Uzycie: python tests/test_slownik_rownowaznosc.py [liczba_plikow_z_korpusu]   (dziala na Windows i macOS; bez korpusu Wymina robi tylko test syntetyczny)"""
import os, re, sys, time, random, importlib.util, collections
sys.stdout.reconfigure(errors="replace")
RT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "litert-rozdziel"); RZ = os.path.join(RT, "scripts", "rozdziel.py")
sp = importlib.util.spec_from_file_location("rz_nowy", RZ); nowy = importlib.util.module_from_spec(sp); sp.loader.exec_module(nowy)
def stara(tekst, reguly):
    liczby = collections.Counter()
    for z, d in reguly:
        rx = re.compile(r"(?<![^\W\d_])" + re.escape(z) + r"(?![^\W\d_])", re.I)
        def zam(m, z=z, d=d):
            s = m.group(0); liczby[z] += 1
            if len(s) > 1 and s.isupper(): return d.upper()
            if s[0].isupper(): return d[0].upper() + d[1:]
            return d
        tekst = rx.sub(zam, tekst)
    return tekst, liczby
reguly = nowy.wczytaj_poprawki(); print("regul: %d" % len(reguly))
teksty = []
for z, d in reguly:
    for forma in (z, z.capitalize(), z.upper()):
        teksty += ["Przed. %s po. i jeszcze raz %s koniec." % (forma, forma), forma, "a%sb x %s, y" % (forma, forma)]
teksty += [" ".join(z for z, d in reguly), " ".join(d for z, d in reguly), "İ ı ſ K ścisnij Ścisnij ŚCISNIJ"]
bl = sum(1 for t in teksty if stara(t, reguly) != nowy.zastosuj_poprawki(t, reguly))
print("(1) teksty syntetyczne: %d | rozbieznosci: %d" % (len(teksty), bl))
def korzen():
    for k in (os.environ.get("LITERT_KORZEN", ""), os.path.join(os.path.expanduser("~"), "Dropbox", "Wymina"), os.path.join(os.path.expanduser("~"), "Library", "CloudStorage", "Dropbox", "Wymina")):
        if k and os.path.isdir(k): return k
W = korzen(); bl2 = 0
if W:
    pliki = [os.path.join(W, k, f) for k in sorted(os.listdir(W)) if os.path.isdir(os.path.join(W, k)) for f in os.listdir(os.path.join(W, k)) if f.endswith(" pl.txt") and "_all" not in f]
    random.seed(20261111); proba = random.sample(pliki, min(int(sys.argv[1]) if len(sys.argv) > 1 else 60, len(pliki))); ts = tn = 0.0; mb = 0
    for p in proba:
        try: t = open(p, "rb").read().decode("utf-8")
        except UnicodeDecodeError: continue
        mb += len(t); t0 = time.perf_counter(); a = stara(t, reguly); t1 = time.perf_counter(); b = nowy.zastosuj_poprawki(t, reguly); t2 = time.perf_counter(); ts += t1 - t0; tn += t2 - t1
        if a != b: bl2 += 1; print("ROZNICA w pliku: %s" % p)
    print("(2) prawdziwe pliki: %d (%.1f MB) | rozbieznosci: %d | czas stara %.1f s, nowa %.2f s (%.0fx)" % (len(proba), mb / 1048576, bl2, ts, tn, ts / max(tn, 1e-9)))
else: print("(2) brak korpusu Wymina na tym komputerze - pominieto")
print("WYNIK: %s" % ("IDENTYCZNIE" if bl == 0 and bl2 == 0 else "ROZBIEZNOSCI"))
sys.exit(0 if bl == 0 and bl2 == 0 else 1)

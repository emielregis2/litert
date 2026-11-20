# -*- coding: utf-8 -*-
"""Testy napraw_auto.py i wykrywania petli znaku w dlugie_linie.py (litert-rozdziel). Uruchom: python tests/test_napraw_auto.py"""
import os, sys, re, time, shutil, tempfile, threading, importlib.util

SK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "litert-rozdziel", "scripts")


def zaladuj(nazwa):
    spec = importlib.util.spec_from_file_location(nazwa + "_t", os.path.join(SK, nazwa + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dl = zaladuj("dlugie_linie")
na = zaladuj("napraw_auto")
BLEDY = []


def sprawdz(warunek, opis):
    print(("OK   " if warunek else "BLAD ") + opis)
    if not warunek:
        BLEDY.append(opis)


def zdania(n, zacznij=0):
    return " ".join("This is sentence number %d of the test story and it goes on a little." % (zacznij + i) for i in range(n))


def zapisz(p, linie):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(linie) + "\n")


def czytaj(p):
    return open(p, "rb").read().decode("utf-8").replace("\r\n", "\n").split("\n")


def przygotuj_katalog(rodzaj_petli):
    """Katalog z oryginalem A.txt i wynikiem 'A pl.txt', w ktorym linia 2 ma petle."""
    tmp = tempfile.mkdtemp(prefix="napraw_auto_")
    d = os.path.join(tmp, "KAT_TEST")
    os.makedirs(d)
    dl_linia = zdania(14)                                   # ok. 1000 znakow: przy limicie 800 ciete na 2 kawalki
    zapisz(os.path.join(d, "A.txt"), ["Short first line.", dl_linia, "Short last line."])
    petla = {"z": "Zdanie " + "ę" * 150 + " koniec.", "s": "Zdanie " + "do " * 40 + "koniec."}[rodzaj_petli]
    zapisz(os.path.join(d, "A pl.txt"), ["Krotka pierwsza linia.", petla, "Krotka ostatnia linia."])
    return tmp, d


# ---- 1. wykrywanie ----
print("== wykrywanie petli znaku ==")
sprawdz(dl.znajdz_petle_znaku("ab " + "ę" * 100 + " cd") == (100, "ę"), "petla polskiej litery 100 x 'ę' wykryta")
sprawdz(dl.znajdz_petle_znaku("ab " + "Ą" * 61) == (61, "Ą"), "petla 61 x 'Ą' wykryta (prog 60)")
sprawdz(dl.znajdz_petle_znaku("ab " + "e" * 59) is None, "59 x 'e' nie jest petla (ponizej progu)")
sprawdz(dl.znajdz_petle_znaku("ab " + "A" * 100, "x " + "A" * 80) is None, "100 x 'A' przy 80 w zrodle: nie petla (nie ponad 2 x)")
sprawdz(dl.znajdz_petle_znaku("ab " + "A" * 200, "x " + "A" * 80) == (200, "A"), "200 x 'A' przy 80 w zrodle: petla")
sprawdz(dl.znajdz_petle_znaku("a b c d") is None, "zwykly tekst: brak petli")

tmp, d = przygotuj_katalog("z")
pliki, pomin = dl.zbierz_plan(d, 4000, set(), True, 0, 0, 800, True, None)
sprawdz(len(pliki) == 1 and not pomin, "zbierz_plan --petle znajduje plik z petla znaku")
sprawdz(pliki and list(pliki[0]["petle"].keys()) == [1] and pliki[0]["rodzaj"].get(1) == "z", "wskazuje linie 2 (indeks 1), rodzaj 'z'")
shutil.rmtree(tmp, ignore_errors=True)


# ---- symulator DeepL (watek): tlumaczy plik pomocniczy tak, jak zrobilby to uzytkownik ----
def symuluj(d, kat, gdzie, tryb, stop):
    pom = os.path.join(d, "DO_PRZETLUMACZENIA_%s_petle.txt" % kat)
    widziany = 0
    while not stop.is_set():
        if os.path.isfile(pom) and os.path.getmtime(pom) > widziany:
            widziany = os.path.getmtime(pom)
            time.sleep(1.0)
            tekst = open(pom, "rb").read().decode("utf-8")
            if tryb == "petla":                       # DeepL znow wpada w petle: dopisuje 120 x 'ę' do kazdego kawalka
                tekst = "\n\n".join(k + " " + "ę" * 120 for k in tekst.strip().split("\n\n")) + "\n"
            else:                                     # poprawne tlumaczenie (tu: ten sam tekst)
                tekst = tekst.replace("sentence number", "zdanie numer")
            with open(os.path.join(gdzie, "DO_PRZETLUMACZENIA_%s_petle pl.txt" % kat), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(tekst)
        time.sleep(0.3)


def uruchom_auto(d, pobrane, proj, tryb):
    kat = os.path.basename(d)
    stop = threading.Event()
    gdzie = pobrane if tryb == "ok" else d
    t = threading.Thread(target=symuluj, args=(d, kat, gdzie, tryb, stop), daemon=True)
    t.start()
    stare = sys.argv
    sys.argv = ["napraw_auto.py", d, "--bez-sprzatania", "--czekaj-min", "1", "--pobrane", pobrane, "--projekt-dir", proj]
    try:
        rc = na.main()
    finally:
        sys.argv = stare
        stop.set()
    return rc


# ---- 2. powodzenie, tlumaczenie z Pobranych ----
print("\n== automat: naprawa udana w 1. rundzie (plik z Pobranych) ==")
tmp, d = przygotuj_katalog("z")
pobrane, proj = os.path.join(tmp, "Pobrane"), os.path.join(tmp, "Projekt")
os.makedirs(pobrane), os.makedirs(proj)
przed = czytaj(os.path.join(d, "A pl.txt"))
rc = uruchom_auto(d, pobrane, proj, "ok")
po = czytaj(os.path.join(d, "A pl.txt"))
sprawdz(rc == 0, "kod wyjscia 0 (naprawiono)")
sprawdz(not re.search(r"([^\s])\1{19,}", "\n".join(po)), "w wyniku nie ma juz petli")
sprawdz(po[0] == przed[0] and po[2] == przed[2], "pozostale linie bez zmian")
sprawdz("zdanie numer" in po[1], "linia 2 zawiera nowe tlumaczenie")
sprawdz(len(po) == len(przed), "liczba linii bez zmian")
sprawdz(not os.path.isfile(os.path.join(pobrane, "DO_PRZETLUMACZENIA_KAT_TEST_petle pl.txt")), "plik z Pobranych zostal przeniesiony")
shutil.rmtree(tmp, ignore_errors=True)

# ---- 3. petla wraca we wszystkich rundach -> wariant B ----
print("\n== automat: petla wraca we wszystkich rundach -> wariant B ==")
tmp, d = przygotuj_katalog("z")
pobrane, proj = os.path.join(tmp, "Pobrane"), os.path.join(tmp, "Projekt")
os.makedirs(pobrane), os.makedirs(proj)
przed = czytaj(os.path.join(d, "A pl.txt"))
rc = uruchom_auto(d, pobrane, proj, "petla")
po = czytaj(os.path.join(d, "A pl.txt"))
sprawdz(rc == 3, "kod wyjscia 3 (wariant B)")
sprawdz(po == przed, "wynik nietkniety (zaden zepsuty wynik nie zostal zapisany)")
rap = [f for f in os.listdir(os.path.join(proj, "raporty")) if f.startswith("KAT_TEST_pozycje_napraw_")] if os.path.isdir(os.path.join(proj, "raporty")) else []
sprawdz(len(rap) == 1, "powstal raport pozycji napraw")
if rap:
    t = open(os.path.join(proj, "raporty", rap[0]), encoding="utf-8").read()
    sprawdz("linia 2" in t and "150" in t and "U+0119" in t, "raport zawiera numer linii, dlugosc i znak petli (bez tekstu)")
    sprawdz("Zdanie" not in t and "koniec" not in t, "raport nie zawiera tekstu z linii")
kop = os.listdir(os.path.join(proj, "kopie_zapasowe")) if os.path.isdir(os.path.join(proj, "kopie_zapasowe")) else []
sprawdz(len(kop) >= 3, "odrzucone wyniki 3 rund odlozone do kopii zapasowych (%d)" % len(kop))
shutil.rmtree(tmp, ignore_errors=True)

# ---- 4. rozjazd ukladu -> kod 5 ----
print("\n== automat: rozjazd ukladu linii -> kod 5 ==")
tmp, d = przygotuj_katalog("z")
zapisz(os.path.join(d, "A pl.txt"), ["Krotka pierwsza linia.", "Zdanie " + "ę" * 150])        # brak jednej linii
stare = sys.argv
sys.argv = ["napraw_auto.py", d, "--bez-sprzatania", "--czekaj-min", "0.1", "--pobrane", os.path.join(tmp, "P"), "--projekt-dir", os.path.join(tmp, "Pr")]
try:
    rc = na.main()
finally:
    sys.argv = stare
sprawdz(rc == 5, "kod wyjscia 5 (nie naprawiamy rozjazdu automatycznie)")
shutil.rmtree(tmp, ignore_errors=True)

print("\nWYNIK: " + ("OK" if not BLEDY else "BLEDY: %d" % len(BLEDY)))
sys.exit(0 if not BLEDY else 1)

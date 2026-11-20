# -*- coding: utf-8 -*-
"""Automatyczna naprawa petli DeepL w rozdzielonych tlumaczeniach (skill litert-rozdziel).

Gdy `rozdziel` wstrzymal sprzatanie z powodu petli (slowa albo znaku, takze polskich liter), ten skrypt prowadzi cala naprawe sam; Ty tylko
tlumaczysz w DeepL jeden maly plik pomocniczy:

  1. skanuje wyniki `* pl.txt` w katalogu i zbiera linie z petlami (ta sama regula co kontrola w rozdziel.py),
  2. zapisuje plik pomocniczy DO_PRZETLUMACZENIA_<Katalog>_petle.txt (kawalki do --limit znakow),
  3. CZEKA na przetlumaczony plik DO_PRZETLUMACZENIA_<Katalog>_petle pl.txt: w katalogu albo w Pobranych (wtedy sam go przenosi),
  4. stosuje go (dlugie_linie.py --zastosuj: kontrole, slownik poprawek, podmiana linii),
  5. gdy petla wraca, robi kolejna runde z krotszymi kawalkami (domyslnie limity 800, 400, 200 znakow),
  6. gdy po wszystkich rundach petla nadal jest, przyjmuje wariant B (stala regula Darka z 2026-11-04): zapisuje liste miejsc (same numery linii i
     znaki petli, bez tekstu) i konczy `rozdziel --tylko-sprzatanie` z progami podniesionymi tuz nad najdluzsze petle,
  7. gdy petli juz nie ma, konczy `rozdziel --tylko-sprzatanie` (kontrola, przeniesienie oryginalow do org, kasowanie plikow technicznych).

Uzycie:
  python napraw_auto.py KATALOG [--limity 800,400,200] [--czekaj-min 120] [--pobrane DIR] [--projekt-dir DIR] [--bez-sprzatania]
Kody wyjscia: 0 = naprawiono i posprzatano; 3 = przyjeto wariant B (cos zostalo nienaprawione); 4 = nie doczekano sie tlumaczenia;
5 = sa pliki z rozjazdem ukladu linii (nie naprawiamy automatycznie, patrz SKILL.md); 1 = blad."""
import os, sys, re, time, shutil, argparse, subprocess, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def zaladuj(nazwa):
    spec = importlib.util.spec_from_file_location(nazwa + "_mod", os.path.join(HERE, nazwa + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def uruchom_dl(dl, argv):
    stare = sys.argv
    sys.argv = ["dlugie_linie.py"] + argv
    try:
        return dl.main()
    finally:
        sys.argv = stare


def odstaw_pl(d, base_pom, kopie, etykieta):
    """Przenosi stare tlumaczenia pliku pomocniczego (po nieudanej rundzie) do katalogu kopii, zeby nie pomylic ich z nowymi."""
    os.makedirs(kopie, exist_ok=True)
    for n in (base_pom + " pl.txt", base_pom + " pl (1).txt"):
        p = os.path.join(d, n)
        if os.path.isfile(p):
            cel = os.path.join(kopie, "%s_%s_%s" % (base_pom.replace("DO_PRZETLUMACZENIA_", "DO_"), etykieta, n.replace(base_pom + " ", "")))
            shutil.move(p, cel)
            print("  odstawiono stary wynik do: " + cel, flush=True)


def czekaj_na_tlumaczenie(d, base_pom, start_ts, limit_s, pobrane):
    nazwy = [base_pom + " pl.txt", base_pom + " pl (1).txt"]
    docelowy = os.path.join(d, nazwy[0])
    koniec = time.time() + limit_s
    ostatni_komunikat = 0
    while time.time() < koniec:
        for fo in (d, pobrane):
            if not fo or not os.path.isdir(fo):
                continue
            for n in nazwy:
                p = os.path.join(fo, n)
                if os.path.isfile(p) and os.path.getmtime(p) >= start_ts - 2:
                    r1 = os.path.getsize(p)
                    time.sleep(2)
                    if os.path.isfile(p) and r1 > 0 and os.path.getsize(p) == r1:
                        if os.path.normcase(os.path.dirname(p)) != os.path.normcase(d):
                            shutil.move(p, docelowy)
                            print("  przeniesiono z Pobranych: " + p, flush=True)
                            return docelowy
                        return p
        if time.time() - ostatni_komunikat > 60:
            print("  czekam na plik: %s (w katalogu lub w Pobranych)..." % nazwy[0], flush=True)
            ostatni_komunikat = time.time()
        time.sleep(4)
    return None


def rozjazdy(dl, d):
    """Pliki biezacej partii (oryginal jeszcze w katalogu glownym), w ktorych wynik ma inna liczbe linii z trescia niz oryginal: DeepL scalil lub
    pominal linie albo dlugie linie nie zostaly zlozone. Zwraca liste (nazwa, linii oryginalu, linii wyniku). Oryginaly w org (partie
    posprzatane) pomijamy: po sprzataniu wyniki maja dodatkowe ciecia na zmianach mowcy, wiec liczby linii sie roznia zgodnie z planem."""
    wyn = []
    for zr, f in dl.pary_zrodel(d):
        if os.path.normcase(zr) != os.path.normcase(d):
            continue
        if not f.lower().endswith(".txt") or f.lower().endswith(" pl.txt") or re.search(r"_all|_spis|_raport|^DO_PRZETLUMACZENIA", f, re.I):
            continue
        wp = os.path.join(d, f[:-4] + " pl.txt")
        if not os.path.isfile(wp):
            continue
        no = sum(1 for x in dl.czytaj_linie(os.path.join(zr, f)) if x.strip())
        nr = sum(1 for x in open(wp, "rb").read().decode("utf-8").split("\n") if x.strip())
        if no != nr:
            wyn.append((f[:-4], no, nr))
    return wyn


def skan(dl, d, limit):
    return dl.zbierz_plan(d, 4000, set(), True, 0, 0, limit, True, None)


def main():
    ap = argparse.ArgumentParser(description="Automatyczna naprawa petli DeepL")
    ap.add_argument("katalog")
    ap.add_argument("--limity", default="800,400,200", help="limity dlugosci kawalka w kolejnych rundach (znaki)")
    ap.add_argument("--czekaj-min", type=float, default=120.0, help="ile minut czekac na przetlumaczony plik w jednej rundzie")
    ap.add_argument("--pobrane", default=os.path.join(os.path.expanduser("~"), "Downloads"), help="katalog, w ktorym szukac pobranego tlumaczenia")
    ap.add_argument("--projekt-dir", default="", help="katalog projektu (podkatalogi kopie_zapasowe, raporty); domyslnie AI_Claude\\Projekt TripleX w Dropbox, a gdy go nie ma, sam katalog")
    ap.add_argument("--bez-sprzatania", action="store_true", help="nie uruchamiaj rozdziel --tylko-sprzatanie na koncu (testy)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace", line_buffering=True)
    except AttributeError:
        pass
    d = os.path.normpath(a.katalog)
    if not os.path.isdir(d):
        print("BLAD: brak katalogu " + d)
        return 1
    try:
        limity = [int(x) for x in a.limity.split(",") if x.strip()]
    except ValueError:
        print("BLAD: --limity to liczby rozdzielone przecinkami, np. 800,400,200")
        return 1
    kat = os.path.basename(d)
    base_pom = "DO_PRZETLUMACZENIA_%s_petle" % kat
    proj = a.projekt_dir or os.path.join(os.path.expanduser("~"), "Dropbox", "AI_Claude", "Projekt TripleX")
    if not os.path.isdir(proj):
        proj = d
    kopie = os.path.join(proj, "kopie_zapasowe") if proj != d else os.path.join(d, "_kopie_napraw")
    raporty = os.path.join(proj, "raporty") if proj != d else d
    dl = zaladuj("dlugie_linie")

    rozj = rozjazdy(dl, d)
    for b, no, nr_ in rozj:
        print("ROZJAZD UKLADU: %s: linii z trescia: oryginal %d, wynik %d" % (b, no, nr_))
    if rozj:
        print("UWAGA: te pliki nie sa naprawiane automatycznie (patrz SKILL.md, sekcja 'Rozjazd ukladu po petli'); petle w pozostalych plikach naprawiam "
              "normalnie, ale na koncu NIE sprzatam katalogu.", flush=True)
    pliki, _ = skan(dl, d, limity[0])
    if not pliki:
        print("Brak linii z petlami w wynikach.")
    nr = 0
    for nr, limit in enumerate(limity, 1):
        pliki, _ = skan(dl, d, limit)
        if not pliki:
            break
        print("\n=== RUNDA %d z %d (limit kawalka %d znakow): linii z petlami: %d w %d plikach ===" % (
            nr, len(limity), limit, sum(len(p["dlugie"]) for p in pliki), len(pliki)), flush=True)
        odstaw_pl(d, base_pom, kopie, "przed_runda%d" % nr)
        rc = uruchom_dl(dl, [d, "--przygotuj", "--petle", "--limit-linii", str(limit)])
        if rc != 0:
            print("BLAD: nie udalo sie przygotowac pliku pomocniczego")
            return 1
        start = time.time()
        pom = os.path.join(d, "DO_PRZETLUMACZENIA_%s_petle.txt" % kat)
        print("\n>>> PRZETLUMACZ W DEEPL: %s\n>>> i zapisz (albo pobierz) jako: %s pl.txt\n" % (pom, base_pom), flush=True)
        p = czekaj_na_tlumaczenie(d, base_pom, start, a.czekaj_min * 60, a.pobrane)
        if not p:
            print("BRAK tlumaczenia w ciagu %.0f min; przerywam (plik pomocniczy zostaje, uruchom skrypt ponownie)." % a.czekaj_min)
            return 4
        rc = uruchom_dl(dl, [d, "--zastosuj", "--petle", "--limit-linii", str(limit)])
        if rc == 0:
            print("RUNDA %d: naprawiono." % nr, flush=True)
        else:
            print("RUNDA %d: nie udalo sie (petla wrocila albo kontrola nie przeszla)." % nr, flush=True)
            odstaw_pl(d, base_pom, kopie, "runda%d_odrzucony" % nr)
    pliki, _ = skan(dl, d, limity[-1])

    rozdz = os.path.join(HERE, "rozdziel.py")
    if not pliki:
        print("\nPetli juz nie ma.", flush=True)
        if rozj:
            print("Katalogu NIE sprzatam: zostal rozjazd ukladu linii (kod 5).")
            return 5
        if a.bez_sprzatania:
            return 0
        r = subprocess.run([sys.executable, rozdz, d, "--tylko-sprzatanie"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout[-3500:])
        return 0 if r.returncode == 0 else 1

    # wariant B
    print("\nWARIANT B: po %d rundach w %d liniach petla nadal jest." % (nr, sum(len(p["dlugie"]) for p in pliki), ), flush=True)
    poz, max_slowo, max_znak = [], 0, 0
    for p in pliki:
        for j, (dlp, tok) in sorted(p["petle"].items()):
            rd = p["rodzaj"].get(j, "s")
            poz.append((p["baza"], j + 1, dlp, tok[:30] if rd == "s" else "U+%04X" % ord(tok[0]), rd))
            if rd == "s":
                max_slowo = max(max_slowo, dlp)
            else:
                max_znak = max(max_znak, dlp)
    os.makedirs(raporty, exist_ok=True)
    rap = os.path.join(raporty, "%s_pozycje_napraw_%s.txt" % (kat, time.strftime("%Y%m%d")))
    with open(rap, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("%s - pozycje nienaprawione (wariant B, stala regula Darka z 2026-11-04)\nData: %s\n\n" % (kat, time.strftime("%Y-%m-%d")))
        for baza, nl, dlp, tok, rd in poz:
            fh.write("%s pl.txt | linia %d (numeracja z chwili rozdzielania, przed cieciem tur) | petla %s: %d x '%s'\n" % (
                baza, nl, "slowa" if rd == "s" else "znaku", dlp, tok))
        fh.write("\nProb naprawy: %d (limity kawalka: %s). Status: PRZYJETE DO WIADOMOSCI, NIENAPRAWIONE.\n" % (nr, ", ".join(map(str, limity[:nr]))))
    print("zapisano raport pozycji: " + rap)
    for baza, nl, dlp, tok, rd in poz:
        print("   %s: linia %d, petla %s %d x '%s'" % (baza[:50], nl, "slowa" if rd == "s" else "znaku", dlp, tok))
    if rozj:
        print("Katalogu NIE sprzatam: zostal rozjazd ukladu linii (kod 5).")
        return 5
    if a.bez_sprzatania:
        return 3
    arg = [sys.executable, rozdz, d, "--tylko-sprzatanie"]
    if max_slowo:
        arg += ["--min-petla-slow", str(max(10, max_slowo + 1))]
    if max_znak:
        arg += ["--min-ciag", str(max(60, max_znak + 1))]
    print("uruchamiam: " + " ".join(os.path.basename(x) if i < 2 else x for i, x in enumerate(arg)), flush=True)
    r = subprocess.run(arg, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-3500:])
    org = os.path.join(d, "org")
    if os.path.isdir(org):
        with open(os.path.join(org, "%s_poprawki_reczne.txt" % kat), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("%s - %s: %d miejsc z petla DeepL PRZYJETYCH DO WIADOMOSCI, NIENAPRAWIONYCH (stala regula Darka z 2026-11-04). Szczegoly: %s\n" % (
                time.strftime("%Y-%m-%d"), kat, len(poz), rap))
    return 3


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Poprawki slownika DeepL WSTECZ w istniejacych tlumaczeniach ' pl.txt' (Windows, macOS, Linux).

Stosuje poprawki z poprawki_deepl.txt (te same reguly i ta sama funkcja zastosuj_poprawki co w rozdziel.py) do gotowych tlumaczen w katalogach, ktorych nazwa pasuje do wzorca
(domyslnie konczacych sie na _4 lub -4). Nic poza slownikiem nie jest zmieniane (ani oryginaly, ani org, ani raporty, ani uklad linii).
Bezpieczenstwo: kopia zapasowa (zip) KAZDEGO zmienianego pliku przed zapisem; weryfikacja (ta sama liczba linii, zmienione tylko linie z dopasowana fraza,
drugi przebieg niczego nie zmienia, kontrola po zapisie); bezpiecznik: przy zbyt duzej liczbie zmian skrypt nie zapisuje, tylko pokazuje liczby.

Przyklady:
  python poprawki_wstecz.py --sucho                      # tylko zliczenie (domyslnie katalogi _4 w Dropbox/Wymina)
  python poprawki_wstecz.py                              # zastosuj (z kopia zip w Downloads)
  python poprawki_wstecz.py --sufiks "" --wszystkie      # wszystkie katalogi
  python poprawki_wstecz.py --filtr natrz --sucho        # tylko reguly zawierajace 'natrz'
  python poprawki_wstecz.py --korzen "D:\\Wymina" --procesy 4
Katalog glowny: --korzen, zmienna LITERT_KORZEN albo automatycznie ~/Dropbox/Wymina (Windows) / ~/Dropbox/Wymina lub ~/Library/CloudStorage/Dropbox/Wymina (Mac).
"""
import os, re, sys, time, zipfile, argparse, datetime, importlib.util, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rownolegle

_RZ = [None]


def _rozdziel():
    """Modul rozdziel.py (te same funkcje wczytaj_poprawki / zastosuj_poprawki), wczytywany raz na proces."""
    if _RZ[0] is None:
        spec = importlib.util.spec_from_file_location("rozdziel_modul", os.path.join(os.path.dirname(os.path.abspath(__file__)), "rozdziel.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _RZ[0] = m
    return _RZ[0]


def _przetworz(arg):
    """Praca na JEDNYM pliku (proces roboczy; nic nie zapisuje). arg = (katalog, plik, filtr). Zwraca slownik."""
    d, f, filtr = arg
    rz = _rozdziel()
    reguly = [(z, dd) for z, dd in rz.wczytaj_poprawki() if (not filtr or filtr in z.lower())]
    p = os.path.join(d, f)
    try:
        t = open(p, "rb").read().decode("utf-8")
    except UnicodeDecodeError:
        return {"d": d, "f": f, "status": "nie_utf8"}
    t2, liczby = rz.zastosuj_poprawki(t, reguly)
    if t2 == t:
        return {"d": d, "f": f, "status": "bez_zmian"}
    L1, L2 = t.split("\n"), t2.split("\n")
    zm = sum(1 for a, b in zip(L1, L2) if a != b)
    bledy = []
    if len(L1) != len(L2):
        bledy.append("zmieniona liczba linii")
    if zm > sum(liczby.values()):
        bledy.append("zbyt wiele zmienionych linii (%d > %d)" % (zm, sum(liczby.values())))
    t3, _ = rz.zastosuj_poprawki(t2, reguly)
    if t3 != t2:
        bledy.append("drugi przebieg cos zmienia")
    return {"d": d, "f": f, "status": "zmiana", "nowy": t2.encode("utf-8"), "liczby": dict(liczby), "linie": zm, "bledy": bledy}


def znajdz_korzen(podany):
    kand = [podany, os.environ.get("LITERT_KORZEN", ""), os.path.join(os.path.expanduser("~"), "Dropbox", "Wymina"),
            os.path.join(os.path.expanduser("~"), "Library", "CloudStorage", "Dropbox", "Wymina"), os.path.join(os.path.expanduser("~"), "Dropbox (Personal)", "Wymina")]
    return next((k for k in kand if k and os.path.isdir(k)), None)


def main():
    ap = argparse.ArgumentParser(description="Poprawki slownika DeepL wstecz w istniejacych tlumaczeniach")
    ap.add_argument("--korzen", default=""); ap.add_argument("--sufiks", default=r"[_-]4$", help="wzorzec (regex) nazwy katalogow; pusty = wszystkie (z --wszystkie)")
    ap.add_argument("--wszystkie", action="store_true", help="nie filtruj katalogow po nazwie"); ap.add_argument("--sucho", action="store_true", help="tylko zliczenie, bez zapisu")
    ap.add_argument("--filtr", default="", help="stosuj tylko reguly, w ktorych bledna forma zawiera ten fragment (male litery)")
    ap.add_argument("--kopia", default="", help="zip z kopia zapasowa (domyslnie ~/Downloads/slownik_wstecz_przed_poprawka_DATA.zip)")
    ap.add_argument("--procesy", type=int, default=0, help="liczba procesow roboczych (0 = automatycznie; 1 = bez rownoleglosci; zmienna LITERT_PROCESY)")
    ap.add_argument("--limit-zamian", type=int, default=3000); ap.add_argument("--limit-plikow", type=int, default=1200)
    ap.add_argument("--zestawienie", default="", help="zapisz zestawienie (katalog | plik | liczba zmienionych linii | zamiany) do pliku .md")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    korzen = znajdz_korzen(a.korzen)
    if not korzen:
        print("BLAD: nie znaleziono katalogu Wymina (podaj --korzen albo ustaw LITERT_KORZEN)")
        return 2
    rz = _rozdziel(); reguly = [(z, d) for z, d in rz.wczytaj_poprawki() if (not a.filtr or a.filtr.lower() in z.lower())]
    kat = [k for k in sorted(os.listdir(korzen)) if os.path.isdir(os.path.join(korzen, k)) and (a.wszystkie or not a.sufiks or re.search(a.sufiks, k))]
    print("korzen: %s | regul: %d%s | katalogow: %d | tryb: %s | procesow: %d" % (korzen, len(reguly), " (filtr '%s')" % a.filtr if a.filtr else "", len(kat),
          "SUCHO (bez zapisu)" if a.sucho else "ZAPIS", a.procesy or rownolegle.domyslna_liczba_procesow()))
    zadania = []
    for k in kat:
        d = os.path.join(korzen, k)
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(" pl.txt") and not re.search(r"_all(_\d+)? pl\.txt$", f, re.I) and not f.startswith("DO_PRZETLUMACZENIA") and os.path.isfile(os.path.join(d, f)):
                zadania.append((d, f, a.filtr.lower()))
    t0 = time.time(); wyniki = list(rownolegle.uruchom(_przetworz, zadania, a.procesy, rozmiar=sum(os.path.getsize(os.path.join(z[0], z[1])) for z in zadania)))
    zm = [w for w in wyniki if w["status"] == "zmiana"]; nie_utf = [w for w in wyniki if w["status"] == "nie_utf8"]
    liczby = collections.Counter(); per_kat = collections.defaultdict(lambda: [0, 0, 0])
    for w in zm:
        liczby.update(w["liczby"]); k = os.path.basename(w["d"]); per_kat[k][0] += 1; per_kat[k][1] += sum(w["liczby"].values()); per_kat[k][2] += w["linie"]
    bledy = [(w, b) for w in zm for b in w["bledy"]]
    print("przejrzano %d tlumaczen w %.0f s | plikow do zmiany: %d | zamian: %d | pominiete (nie UTF-8): %d" % (len(wyniki), time.time() - t0, len(zm), sum(liczby.values()), len(nie_utf)))
    print("weryfikacja przed zapisem: %s" % ("OK" if not bledy else "%d BLEDOW - NIE ZAPISUJE" % len(bledy)))
    for w, b in bledy[:10]:
        print("  BLAD %s\\%s: %s" % (os.path.basename(w["d"]), w["f"], b))
    print("\nwg regul (%d uzytych):" % len(liczby))
    for z, c in liczby.most_common(40):
        print("   %-44s %4d" % (z, c))
    print("\nwg katalogow (plikow / zamian / linii), %d katalogow:" % len(per_kat))
    for k, v in sorted(per_kat.items(), key=lambda kv: -kv[1][1])[:40]:
        print("   %-36s %3d / %4d / %4d" % (k[:36], v[0], v[1], v[2]))
    if a.zestawienie:
        L = ["# Poprawki slownika wstecz (%s)" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "", "Plikow %d, zamian %d, katalogow %d." % (len(zm), sum(liczby.values()), len(per_kat)), "", "| Katalog | Plik | Linie | Zamiany |", "|---|---|---:|---|"]
        for w in sorted(zm, key=lambda w: (os.path.basename(w["d"]), -w["linie"], w["f"])):
            L.append("| %s | %s | %d | %s |" % (os.path.basename(w["d"]), re.sub(r" pl\.txt$", "", w["f"]), w["linie"], ", ".join("%s ×%d" % kv for kv in sorted(w["liczby"].items(), key=lambda kv: -kv[1])[:4])))
        open(a.zestawienie, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n"); print("\nzestawienie: " + a.zestawienie)
    if bledy or a.sucho or not zm:
        return 1 if bledy else 0
    if sum(liczby.values()) > a.limit_zamian or len(zm) > a.limit_plikow:
        print("BEZPIECZNIK: zmian wiecej niz limit (%d zamian / %d plikow) - NIE ZAPISUJE (zwieksz --limit-zamian / --limit-plikow po sprawdzeniu liczb)" % (a.limit_zamian, a.limit_plikow))
        return 2
    kopia = a.kopia or os.path.join(os.path.expanduser("~"), "Downloads", "slownik_wstecz_przed_poprawka_%s.zip" % datetime.date.today().isoformat())
    if os.path.exists(kopia):
        print("UWAGA: kopia zip juz istnieje i zostanie nadpisana: " + kopia)
    with zipfile.ZipFile(kopia, "w", zipfile.ZIP_DEFLATED) as zf:
        for w in zm:
            zf.writestr("%s/%s" % (os.path.basename(w["d"]), w["f"]), open(os.path.join(w["d"], w["f"]), "rb").read())
    print("\nkopia zapasowa: %s (%d plikow, %.1f MB)" % (kopia, len(zm), os.path.getsize(kopia) / 1048576))
    for w in zm:
        open(os.path.join(w["d"], w["f"]), "wb").write(w["nowy"])
    ok = sum(1 for w in zm if open(os.path.join(w["d"], w["f"]), "rb").read() == w["nowy"])
    print("kontrola po zapisie: %d z %d plikow zgodnych" % (ok, len(zm)))
    return 0 if ok == len(zm) else 1


if __name__ == "__main__":
    sys.exit(main())

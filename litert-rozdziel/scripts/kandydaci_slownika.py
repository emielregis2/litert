# -*- coding: utf-8 -*-
"""Odkrywanie bledow DeepL w ISTNIEJACYCH tlumaczeniach: slowa spoza polskiego slownika (skill litert-rozdziel).

Przeszukuje pliki '* pl.txt' w podanych katalogach (rekurencyjnie, bez podkatalogow 'org'), liczy slowa, ktorych NIE MA w slowniku hunspell pl_PL
(np. 'polizaj', 'gryzili'), pomija imiona (wyrazy pisane wielka litera takze w srodku zdania) i wypisuje raport uszeregowany wg czestosci, z oznaczeniem
slow wygladajacych na tryb rozkazujacy lub czas przeszly (-aj, -ajcie, -uj, -ij, -zili), lematem (np. polizaj -> polizac) i podpowiedziami slownika.
UWAGA: slownik NIE zna blednych slow typu 'istniejace slowo w zlym kontekscie' (np. 'wytryskaj', 'wylizuj' - poprawne formy niedokonane); takie bledy
zglasza Darek. Podpowiedzi slownika dla rozkazujacych bywaja bledne ('polizaj' -> 'polizal'), wiec poprawna forme ustala sie recznie i sprawdza
poleceniem --sprawdz.

Uzycie:
  python kandydaci_slownika.py KATALOG [KATALOG ...] [--min 3] [--min-plikow 1] [--top 300] [--sugestie 60] [--wynik kandydaci_slownika.md]
  python kandydaci_slownika.py --sprawdz "poliz;polizaj;wyliż"       (czy formy sa w slowniku + podpowiedzi)
Wymaga: pip install spylls. Slownik pl_PL (LibreOffice, ok. 5 MB) pobiera sam do ~/.litert/ przy pierwszym uruchomieniu (albo --slownik SCIEZKA/pl_PL)."""
import os, re, sys, time, argparse, collections, itertools, urllib.request

URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/pl_PL/pl_PL.%s"
TOK = re.compile(r"[^\W\d_]+")
ROZK = ("aj", "ajcie", "ajmy", "uj", "ujcie", "ij", "ijcie", "yj", "yjcie")
PRZESZ = re.compile(r"(?:zili|ziliśmy|ziliście)$")


def wczytaj_slownik(sciezka=None):
    try:
        from spylls.hunspell import Dictionary
    except ImportError:
        print("BLAD: brak biblioteki spylls. Zainstaluj: pip install spylls")
        sys.exit(1)
    if not sciezka:
        d = os.path.join(os.path.expanduser("~"), ".litert")
        os.makedirs(d, exist_ok=True)
        sciezka = os.path.join(d, "pl_PL")
        for ext in ("aff", "dic"):
            p = "%s.%s" % (sciezka, ext)
            if not os.path.isfile(p) or os.path.getsize(p) < 1000:
                print("Pobieram slownik pl_PL.%s ..." % ext)
                try:
                    urllib.request.urlretrieve(URL % ext, p)
                except Exception as e:
                    print("BLAD pobierania slownika (%r). Pobierz recznie pl_PL.aff i pl_PL.dic z https://github.com/LibreOffice/dictionaries/tree/master/pl_PL "
                          "do %s i uruchom z --slownik" % (e, d))
                    sys.exit(1)
    return Dictionary.from_files(sciezka)


def sprawdz(D, formy):
    for w in formy:
        ok = bool(D.lookup(w)) or bool(D.lookup(w.capitalize()))
        sug = list(itertools.islice(D.suggest(w), 5)) if not ok else []
        print("  %-18s %-12s %s" % (w, "W SLOWNIKU" if ok else "BRAK", ("podpowiedzi: " + ", ".join(sug)) if sug else ""))


def lemat(D, w):
    kand = []
    if w.endswith("ajcie"):
        kand = [w[:-5] + "ać"]
    elif w.endswith("ajmy"):
        kand = [w[:-4] + "ać"]
    elif w.endswith("aj"):
        kand = [w[:-2] + "ać"]
    elif w.endswith("ujcie"):
        kand = [w[:-5] + s for s in ("ywać", "iwać", "ować")]
    elif w.endswith("uj"):
        kand = [w[:-2] + s for s in ("ywać", "iwać", "ować")]
    for k in kand:
        if D.lookup(k):
            return k
    return ""


def main():
    ap = argparse.ArgumentParser(description="Slowa spoza slownika polskiego w tlumaczeniach (kandydaci na wpisy do poprawki_deepl.txt)")
    ap.add_argument("katalogi", nargs="*")
    ap.add_argument("--min", type=int, default=3, help="minimalna liczba wystapien slowa (domyslnie 3)")
    ap.add_argument("--min-plikow", type=int, default=1, help="minimalna liczba plikow ze slowem (domyslnie 1)")
    ap.add_argument("--top", type=int, default=300, help="ile slow w raporcie (domyslnie 300)")
    ap.add_argument("--sugestie", type=int, default=60, help="dla ilu najczestszych slow szukac podpowiedzi slownika (kazde ok. 1 s; domyslnie 60)")
    ap.add_argument("--wynik", default="kandydaci_slownika.md", help="plik raportu (Markdown); obok powstaje kandydaci_slownika_reguly.txt")
    ap.add_argument("--slownik", default="", help="sciezka do slownika bez rozszerzenia (np. C:\\slowniki\\pl_PL)")
    ap.add_argument("--sprawdz", default="", help="formy rozdzielone srednikiem do sprawdzenia w slowniku")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    D = wczytaj_slownik(a.slownik or None)
    if a.sprawdz:
        sprawdz(D, [x.strip() for x in a.sprawdz.split(";") if x.strip()])
        return 0
    if not a.katalogi:
        print("Podaj katalog(i) z tlumaczeniami albo --sprawdz.")
        return 1
    t0 = time.time()
    cache = {}                                            # slowo -> True (jest w slowniku) / False (brak)
    cnt, pliki, mid, mid_up, przyklad = collections.Counter(), collections.defaultdict(set), collections.Counter(), collections.Counter(), {}
    nplik = nsl = 0
    for kat in a.katalogi:
        for dp, dn, fn in os.walk(kat):
            dn[:] = [x for x in dn if x.lower() != "org"]
            for f in fn:
                if not f.endswith(" pl.txt") or f.startswith("DO_PRZETLUMACZENIA") or re.search(r"_all(_\d+)? pl\.txt$", f):
                    continue
                nplik += 1
                try:
                    tekst = open(os.path.join(dp, f), "rb").read().decode("utf-8")
                except UnicodeDecodeError:
                    continue
                for nr, linia in enumerate(tekst.split("\n"), 1):
                    for m in TOK.finditer(linia):
                        s = m.group(0)
                        w = s.lower()
                        nsl += 1
                        st = cache.get(w)
                        if st is None:
                            st = cache[w] = len(w) < 3 or len(set(w)) <= 2 or bool(re.search("[qvx]", w)) or bool(D.lookup(w)) or bool(D.lookup(s)) or bool(D.lookup(w.capitalize()))
                        if st:
                            continue
                        cnt[w] += 1
                        pliki[w].add(nplik)
                        pre = linia[:m.start()].rstrip()
                        if pre and pre[-1] not in '.!?"„”«»…:;—–-':           # nie na poczatku zdania: wielka litera => imie
                            mid[w] += 1
                            mid_up[w] += s[0].isupper()
                        if w not in przyklad:
                            przyklad[w] = (f[:-7][:40], nr, linia[max(0, m.start() - 35):m.end() + 25].strip())
    wyniki = []
    for w, n in cnt.most_common():
        if n < a.min or len(pliki[w]) < a.min_plikow:
            continue
        if mid[w] >= 2 and mid_up[w] / mid[w] >= 0.85:                          # imie / nazwa wlasna
            continue
        typ = "rozkazujacy?" if (len(w) >= 4 and w.endswith(ROZK)) else ("czas przeszly?" if PRZESZ.search(w) else "inne")
        wyniki.append((w, n, len(pliki[w]), typ))
    wyniki = wyniki[:a.top]
    t1 = time.time()
    sug = {}
    pil = [x for x in wyniki if x[3] != "inne"][:a.sugestie] + [x for x in wyniki if x[3] == "inne"][:max(0, a.sugestie - sum(1 for x in wyniki if x[3] != "inne"))]
    for w, n, nf, typ in pil:
        if time.time() - t1 > 240:
            break
        try:
            sug[w] = list(itertools.islice(D.suggest(w), 4))
        except Exception:
            sug[w] = []
    sekcje = [("ROZKAZUJACE (koncowki -aj/-ajcie/-uj/-ij...)", "rozkazujacy?"), ("CZAS PRZESZLY (-zili..., analogia 'gryzili')", "czas przeszly?"), ("INNE slowa spoza slownika", "inne")]
    L = ["# Slowa spoza slownika polskiego w tlumaczeniach", "", "Przeszukano %d plikow, %d slow w %.0f s; slow unikalnych %d, w tym spoza slownika (po odsianiu imion i rzadkich): %d."
         % (nplik, nsl, time.time() - t0, len(cache), len(wyniki)), "",
         "**Uwaga:** slownik nie zna bledow typu 'istniejace slowo w zlym kontekscie' (np. wytryskaj, wylizuj); podpowiedzi dla rozkazujacych bywaja bledne - poprawna forme ustal i sprawdz `--sprawdz`.", ""]
    reguly = ["# Kandydaci na wpisy do poprawki_deepl.txt (NIC nie jest stosowane automatycznie). Odkomentuj i uzupelnij tylko zatwierdzone: zle => dobre", ""]
    for tytul, kod in sekcje:
        wiersze = [x for x in wyniki if x[3] == kod]
        if not wiersze:
            continue
        L += ["## " + tytul, "", "| slowo | wystapien | plikow | lemat | podpowiedzi slownika | przyklad |", "|---|---|---|---|---|---|"]
        for w, n, nf, typ in wiersze:
            ex = przyklad[w]
            L.append("| %s | %d | %d | %s | %s | %s (%s, l. %d) |" % (w, n, nf, lemat(D, w) or "", ", ".join(sug.get(w, [])), ex[2].replace("|", "/"), ex[0], ex[1]))
            if kod != "inne":
                reguly.append("# %s => ???    # %dx w %d plikach; lemat: %s; podpowiedzi: %s" % (w, n, nf, lemat(D, w) or "-", ", ".join(sug.get(w, [])) or "-"))
        L.append("")
    open(a.wynik, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    rpath = os.path.splitext(a.wynik)[0] + "_reguly.txt"
    open(rpath, "w", encoding="utf-8", newline="\n").write("\n".join(reguly) + "\n")
    print("Przeszukano %d plikow (%d slow) w %.0f s. Raport: %s | szablon regul: %s" % (nplik, nsl, time.time() - t0, a.wynik, rpath))
    for w, n, nf, typ in wyniki[:40]:
        print("  %-22s %6dx %4d plikow  %-15s %s" % (w, n, nf, typ, ", ".join(sug.get(w, [])[:3])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

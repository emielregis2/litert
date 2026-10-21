#!/usr/bin/env python3
"""Scala pliki .txt z katalogu w pliki <NazwaKatalogu>_all[_N].txt (limit rozmiaru, bez przecinania plikow).

Uzycie:  python scal.py "C:\\sciezka\\do\\KATALOG" [--limit 900000]
"""
import os, sys, glob, argparse

try:  # nazwy plikow z polskimi/specjalnymi znakami nie moga wywrocic wypisywania na konsole
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


def czytaj_plik(path):
    """Zwraca (tekst, kodowanie). Kolejnosc: UTF-16 (z BOM) -> UTF-8 (z BOM lub bez) ->
    cp1252 (zwykle "ANSI" angielskich plikow z Windows) -> awaryjnie cp1250."""
    raw = open(path, "rb").read()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        return raw.decode("cp1250", errors="replace"), "cp1250"


def dziel(txt, limit):
    """Dzieli tekst linia po linii na mozliwie rowne czesci, kazda <= limit bajtow (UTF-8).
    Zwraca liste stringow. Linia dluzsza niz limit trafia sama do czesci (nie jest przecinana)."""
    import math
    lines = txt.splitlines(keepends=True)
    sizes = [len(l.encode("utf-8")) for l in lines]
    total = sum(sizes)
    n = max(2, math.ceil(total / limit))
    while True:
        parts, i, remaining, ok = [], 0, total, True
        for k in range(n):
            left = n - k
            if left == 1:
                chunk = list(range(i, len(lines)))
                csize = sum(sizes[j] for j in chunk)
                if csize > limit and not (len(chunk) == 1):
                    ok = False
                    break
                parts.append(chunk); i = len(lines)
                break
            target = remaining / left
            csize, start = 0, i
            while i < len(lines):
                nxt = sizes[i]
                if i > start and (csize + nxt > limit or (csize >= target) or
                                  (csize + nxt > target and (csize + nxt - target) > (target - csize))):
                    break
                csize += nxt; i += 1
            if i == start:          # zabezpieczenie: zawsze co najmniej jedna linia
                csize = sizes[i]; i += 1
            parts.append(list(range(start, i)))
            remaining -= csize
        if ok and i >= len(lines):
            return ["".join(lines[j] for j in c) for c in parts if c]
        n += 1


def pakuj(items, limit):
    """Zwraca liste grup (list elementow items) uzywajac First Fit Decreasing, a gdy wynik
    przekracza dolna granice liczby plikow - probuje poprawic losowymi permutacjami."""
    import math, random
    cap = limit + 2
    w = lambda it: it[2] + 2

    def first_fit(order):
        bins, loads = [], []
        for it in order:
            for i, l in enumerate(loads):
                if l + w(it) <= cap:
                    bins[i].append(it); loads[i] += w(it)
                    break
            else:
                bins.append([it]); loads.append(w(it))
        return bins

    base = sorted(items, key=lambda x: (-x[2], x[0].lower()))
    best = first_fit(base)
    lower = max(1, math.ceil(sum(w(i) for i in items) / cap)) if items else 1
    rnd = random.Random(1)
    tries = 0
    while len(best) > lower and tries < 30000:
        order = base[:]
        rnd.shuffle(order)
        order.sort(key=lambda x: -(x[2] * rnd.uniform(0.9, 1.1)))   # lekko zaburzone sortowanie malejace
        cand = first_fit(order)
        if len(cand) < len(best):
            best = cand
        tries += 1
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("katalog")
    ap.add_argument("--limit", type=int, default=900000, help="maks. rozmiar pliku scalenia w bajtach")
    a = ap.parse_args()

    d = os.path.normpath(a.katalog)
    base = os.path.basename(d) + "_all"
    spis_name = os.path.basename(d) + "_spis_scalenia.txt"

    # Kasujemy WYLACZNIE wlasne pliki scalenia (base.txt, base_N.txt) i spis.
    # Przetlumaczone pliki (base_N pl.txt) i wszystko inne zostaje nietkniete.
    import re as _re
    wlasne = _re.compile(r"^" + _re.escape(base) + r"(_\d+)?\.txt$", _re.I)
    for f in os.listdir(d):
        if wlasne.match(f) or f.lower() == spis_name.lower():
            os.remove(os.path.join(d, f))

    def is_orig(f):
        low = f.lower()
        if not low.endswith(".txt"):
            return False
        if low.startswith(base.lower()) or low == spis_name.lower():
            return False
        if low[:-4].rstrip().endswith(" pl"):   # wersje tlumaczone
            return False
        if "_copy(" in low:                      # kopie tworzone przez Dropbox/edytor
            return False
        return True

    import re
    all_txt = {f.lower(): f for f in os.listdir(d) if f.lower().endswith(".txt")}
    cands = sorted((f for f in os.listdir(d) if is_orig(f)), key=str.lower)

    # Czesci z poprzedniego dzielenia (NazwaOryginalu_N.txt, gdy NazwaOryginalu.txt istnieje) nie sa oryginalami
    def czesc_z(f):
        m = re.match(r"^(.*)_(\d+)\.txt$", f, re.I)
        return m and (m.group(1) + ".txt").lower() in all_txt and (m.group(1) + ".txt").lower() != f.lower()
    stare_czesci = [f for f in cands if czesc_z(f)]
    names = [f for f in cands if f not in stare_czesci]
    items, duze, ostrz_kod, kodowania = [], [], [], {}
    for n in names:
        txt, enc = czytaj_plik(os.path.join(d, n))
        kodowania[enc] = kodowania.get(enc, 0) + 1
        if enc in ("utf-16", "cp1250"):      # cp1252 to zwykle ANSI - normalne, bez ostrzezenia
            ostrz_kod.append("%s: odczytano jako %s (nietypowe kodowanie) - sprawdz znaki specjalne" % (n, enc))
        if "\ufffd" in txt:
            ostrz_kod.append("%s: zawiera znak zastepczy U+FFFD (znaki uszkodzone juz w zrodle)" % n)
        txt = txt.replace("\r\n", "\n").strip("\n") + "\n"
        sz = len(txt.encode("utf-8"))
        if sz > a.limit:
            duze.append((n, txt, sz))        # duzy plik: dzielimy, nie scalamy
        else:
            items.append((n, txt, sz))

    # Numeracja oryginalow (alfabetycznie) i znacznik granicy: =====[[N|Nazwa]]=====
    # Numer jest kluczem przy rozdzielaniu po tlumaczeniu; nazwa jest tylko dla czytelnosci.
    items.sort(key=lambda x: x[0].lower())
    nowe = []
    for num, (n, txt, sz) in enumerate(items, 1):
        disp = n[:-4]
        for ch in "[]|":
            disp = disp.replace(ch, " ")
        znacznik = "=====[[%d|%s]]=====\n\n" % (num, " ".join(disp.split()))
        txt2 = znacznik + txt
        nowe.append((n, txt2, len(txt2.encode("utf-8")), num))
    items = nowe

    # Dzielenie duzych plikow na czesci NazwaOryginalu_1.txt, _2.txt ...
    podzielone = []
    for n, txt, sz in duze:
        stem = n[:-4]
        for f in list(stare_czesci):          # kasujemy tylko stare czesci TEGO pliku i tylko gdy jest duzy
            m = re.match(r"^(.*)_(\d+)\.txt$", f, re.I)
            if m.group(1).lower() == stem.lower():
                os.remove(os.path.join(d, f)); stare_czesci.remove(f)
        czesci = dziel(txt, a.limit)
        nazwy = []
        for i, c in enumerate(czesci, 1):
            fn = "%s_%d.txt" % (stem, i)
            with open(os.path.join(d, fn), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(c)
            nazwy.append((fn, len(c.encode("utf-8"))))
            print("   [podzial]", fn, len(c.encode("utf-8")), "bajtow")
        podzielone.append((n, sz, nazwy))
    if stare_czesci:
        print("UWAGA: pominalem w scalaniu prawdopodobne czesci (oryginal nie jest juz duzy):", ", ".join(stare_czesci))

    if not items and not duze:
        print("Brak plikow do scalenia (moze oryginaly zostaly przeniesione do podkatalogu org?) - nic nie zapisano.")
        return 0

    # Pakowanie: jak najmniej plikow scalenia, maksymalne wypelnienie limitu (bin packing).
    # Koszt pliku = rozmiar + 2 bajty separatora, pojemnosc = limit + 2 (separator jest tylko MIEDZY plikami).
    groups = pakuj(items, a.limit)
    for g in groups:
        g.sort(key=lambda x: x[0].lower())          # wewnatrz pliku scalenia: kolejnosc alfabetyczna
    groups.sort(key=lambda g: g[0][0].lower())      # numeracja plikow scalenia wg pierwszej nazwy alfabetycznie
    for g in groups:
        tot = sum(x[2] for x in g) + 2 * (len(g) - 1)
        if tot > a.limit:
            print("UWAGA: plik", g[0][0], "sam przekracza limit", a.limit, "bajtow (nie jest przecinany)")

    single = len(groups) == 1
    spis = []
    for i, g in enumerate(groups, 1):
        fn = os.path.join(d, base + (".txt" if single else "_%d.txt" % i))
        with open(fn, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n\n".join(x[1] for x in g))
        print(os.path.basename(fn), os.path.getsize(fn), "bajtow")
        spis.append(os.path.basename(fn))
        for x in g:
            print("   ", x[0], x[2])
            spis.append("    %d. %s" % (x[3], x[0]))
        spis.append("")

    if podzielone:
        spis.append("Pliki podzielone (nie scalane):")
        for n, sz, nazwy in podzielone:
            spis.append(n + " (" + str(sz) + " bajtow)")
            for fn, fsz in nazwy:
                spis.append("    " + fn + " (" + str(fsz) + " bajtow)")
        spis.append("")
    # Spis scalenia: oryginalne nazwy plikow w kazdym pliku scalenia
    with open(os.path.join(d, spis_name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(spis).rstrip("\n") + "\n")
    print(spis_name, "zapisany")
    print("Pominiete (pl/_copy) nie sa wypisywane; scalono plikow:", len(items))
    print("Kodowanie wejscia: " + ", ".join("%s: %d" % (k, v) for k, v in sorted(kodowania.items())))
    print("Kodowanie wyniku: UTF-8 bez BOM, konce linii LF")
    for w in ostrz_kod:
        print("UWAGA (kodowanie):", w)


if __name__ == "__main__":
    sys.exit(main())

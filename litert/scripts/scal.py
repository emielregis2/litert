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


def _bez_pustych_na_granicach(lines, ranges):
    """Wycina puste linie z brzegow czesci (czesc nie zaczyna sie ani nie konczy pusta linia, bo DeepL przycina
    puste linie na poczatku pliku). Zwraca (teksty czesci, [liczba pustych linii miedzy czescia i-1 a i, dla i>=1])."""
    trimmed = []
    for k, c in enumerate(ranges):
        lo, hi, lead, trail = c[0], c[-1] + 1, 0, 0
        if k > 0:
            while lo < hi and lines[lo] == "\n":
                lo += 1; lead += 1
        if k < len(ranges) - 1:
            while hi > lo and lines[hi - 1] == "\n":
                hi -= 1; trail += 1
        if lo >= hi:                                    # zabezpieczenie: czesc z samych pustych linii zostaje bez zmian
            lo, hi, lead, trail = c[0], c[-1] + 1, 0, 0
        trimmed.append((lo, hi, lead, trail))
    teksty = ["".join(lines[lo:hi]) for lo, hi, _, _ in trimmed]
    przerwy = [trimmed[k - 1][3] + trimmed[k][2] for k in range(1, len(trimmed))]
    return teksty, przerwy


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
            return _bez_pustych_na_granicach(lines, [c for c in parts if c])
        n += 1


def analizuj_kopie(d, zastepuj=True):
    """Analiza kopii NazwaOryginalu_copy(N).txt wzgledem oryginalow PRZED scalaniem.
    - kopia NOWSZA (o co najmniej 60 s; pliki wgrane hurtem maja ten sam czas) i WIEKSZA od oryginalu -> zastepuje oryginal
      (oryginal trafia do podkatalogu _zastapione),
    - kopia identyczna (ta sama tresc) -> bez zmian (kopia niepotrzebna, nie jest scalana),
    - kazda inna sytuacja (mniejsza, starsza-ale-wieksza, ten sam rozmiar a inna tresc, brak oryginalu)
      -> tylko raport DO DECYZJI uzytkownika, nic sie nie zmienia.
    Rozmiary porownywane po normalizacji (UTF-8, LF), zeby kodowanie/konce linii nie fałszowaly wyniku.
    Zwraca liste (status, nazwa kopii, opis)."""
    import re, shutil, datetime
    rx = re.compile(r"^(.*)_copy\((\d+)\)(\.txt)$", re.I)
    pliki = {f.lower(): f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))}
    org_dir = os.path.join(d, "org")
    org_pliki = {f.lower(): f for f in os.listdir(org_dir)} if os.path.isdir(org_dir) else {}
    kopie = []
    for f in pliki.values():
        m = rx.match(f)
        if m:
            kopie.append((f, m.group(1) + m.group(3), int(m.group(2))))
    if not kopie:
        return []

    def tekst(path):
        t, _ = czytaj_plik(path)
        return t.replace("\r\n", "\n").strip("\n") + "\n"

    def czas(ts):
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    wyniki = []
    for kf, on, nr in sorted(kopie, key=lambda x: (x[1].lower(), x[2])):
        kp = os.path.join(d, kf)
        if on.lower() in pliki:
            op, gdzie = os.path.join(d, pliki[on.lower()]), "katalog"
        elif on.lower() in org_pliki:
            op, gdzie = os.path.join(org_dir, org_pliki[on.lower()]), "org"
        else:
            wyniki.append(("BRAK_ORYGINALU", kf, "nie znaleziono oryginalu '%s' (ani w katalogu, ani w org)" % on))
            continue
        tk, to = tekst(kp), tekst(op)
        sk, so = len(tk.encode("utf-8")), len(to.encode("utf-8"))
        mk, mo = os.path.getmtime(kp), os.path.getmtime(op)
        opis = "kopia %d B (%s) | oryginal %d B (%s)%s | slow %d/%d, puste linie %d/%d (kopia/oryginal)" % (
            sk, czas(mk), so, czas(mo), "" if gdzie == "katalog" else " [oryginal w org]",
            len(tk.split()), len(to.split()), sum(1 for x in tk.split("\n") if not x.strip()), sum(1 for x in to.split("\n") if not x.strip()))
        if tk == to:
            wyniki.append(("IDENTYCZNA", kf, opis + " | ta sama tresc"))
        elif sk > so and mk - mo >= 60:
            if zastepuj and gdzie == "katalog":
                kat = os.path.join(d, "_zastapione")
                os.makedirs(kat, exist_ok=True)
                cel = os.path.join(kat, os.path.basename(op))
                if os.path.exists(cel):
                    cel = os.path.join(kat, "%s_%s" % (datetime.datetime.now().strftime("%Y%m%d-%H%M%S"), os.path.basename(op)))
                shutil.move(op, cel)
                shutil.move(kp, op)
                pliki.pop(kf.lower(), None)
                wyniki.append(("ZASTEPIONO", kf, opis + " | oryginal zachowany w _zastapione"))
            else:
                powod = "tryb tylko-analiza" if gdzie == "katalog" else "oryginal jest w org, nie zastepuje automatycznie"
                wyniki.append(("DO_DECYZJI", kf, opis + " | kopia nowsza i wieksza (kandydat do zastapienia; " + powod + ")"))
        elif sk > so and mk > mo:
            wyniki.append(("DO_DECYZJI", kf, opis + " | kopia wieksza i nowsza tylko o %d s (pliki wgrane hurtem?) - za malo, by zastapic automatycznie" % int(mk - mo)))
        elif sk < so:
            wyniki.append(("DO_DECYZJI", kf, opis + " | kopia MNIEJSZA od oryginalu"))
        elif sk > so:
            wyniki.append(("DO_DECYZJI", kf, opis + " | kopia wieksza, ale STARSZA od oryginalu"))
        else:
            wyniki.append(("DO_DECYZJI", kf, opis + " | ten sam rozmiar, ale INNA tresc"))

    print("=== ANALIZA KOPII _copy: %d plikow ===" % len(wyniki))
    for status, tytul in (("ZASTEPIONO", "zastapiono oryginal nowsza i wieksza kopia"),
                          ("IDENTYCZNA", "kopia identyczna z oryginalem (niepotrzebna, nie jest scalana)"),
                          ("DO_DECYZJI", "DO DECYZJI UZYTKOWNIKA (nic nie zmieniono)"),
                          ("BRAK_ORYGINALU", "DO DECYZJI: kopia bez oryginalu")):
        grupa = [w for w in wyniki if w[0] == status]
        if grupa:
            print("%s: %d" % (tytul, len(grupa)))
            for _, nazwa, opis in grupa:
                print("   - %s\n       %s" % (nazwa, opis))
    print("=== koniec analizy kopii ===")
    return wyniki


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


def skroc_przeciagniecia(txt, min_dl=5, do=4):
    """Skraca przeciagniete litery oraz znaki ! ? . (ciagi >= min_dl tego samego znaku) do 'do' znakow. Dziala tylko na
    tekscie wysylanym do tlumaczenia: przeciagniete okrzyki ('Daddddyyyy!!!!!!!') wprawiaja DeepL w petle i powoduja zgubione
    konce zdan. Zwraca (tekst, liczba skroconych ciagow)."""
    import re as _re
    return _re.subn(r"([^\W\d_]|[!?.])\1{%d,}" % (min_dl - 1), lambda m: m.group(1) * do, txt)


def dziel_dluga_linie(linia, prog=4000, cel=3000, min_kawalek=1200, min_tura=1500):
    """Dzieli bardzo dluga linie na kawalki na granicach: najpierw zmiany mowcy ('"" ' albo '" "', czyli zamkniecie i otwarcie cudzyslowu), a gdy
    ich brak w oknie - zdania (pojedyncza spacja po . ! ? albo po zamykajacym cudzyslowie/nawiasie po nich). Polaczenie kawalkow pojedyncza spacja
    odtwarza linie co do znaku. Linie do 'prog' znakow zwraca bez zmian. Powod: DeepL traci jakosc na bardzo dlugich liniach (podwojone slowa,
    zaimki 'On/Ja', rozsypane 'sie'); w danych wszystkie pliki z 'czkawka' mialy linie > 6900 znakow. Kawalki nie sa za krotkie (min. 1200 znakow,
    cel 3000), bo DeepL scala krotkie linie, a kazdy odcinek traci kontekst (np. rodzaj narratora)."""
    if len(linia) <= prog:
        return [linia]

    def tura(i):          # spacja na granicy zmiany mowcy: '"" ' (zamkniecie + otwarcie cudzyslowu) albo '" "'
        return i >= 2 and i + 1 < len(linia) and linia[i] == " " and linia[i - 1] == '"' and (linia[i - 2] == '"' or linia[i + 1] == '"')

    def granica(i):
        if tura(i):
            return True
        if i < 2 or i + 1 >= len(linia) or linia[i] != " " or linia[i - 1] == " " or linia[i + 1] == " ":
            return False
        p = linia[i - 1]
        return p in ".!?" or (p in "\"'\u201d\u2019)" and linia[i - 2] in ".!?")
    kawalki, start = [], 0
    while len(linia) - start > prog:
        b = None
        for i in range(start + cel, start + min_tura, -1):               # 1. preferuj granice zmiany mowcy ("" lub " ")
            if tura(i):
                b = i
                break
        if b is None:                                                     # 2. ostatnia granica zdania w oknie [min, cel]
            for i in range(start + cel, start + min_kawalek, -1):
                if granica(i):
                    b = i
                    break
        if b is None:                                                     # 3. pierwsza granica za 'cel' (do 2 x cel)
            for i in range(start + cel + 1, min(len(linia) - 1, start + 2 * cel)):
                if granica(i):
                    b = i
                    break
        if b is None:                                                     # 4. ostatnia pojedyncza spacja w oknie
            for i in range(start + cel, start + min_kawalek, -1):
                if linia[i] == " " and linia[i - 1] != " " and linia[i + 1] != " ":
                    b = i
                    break
        if b is None:
            break
        kawalki.append(linia[start:b])
        start = b + 1
    kawalki.append(linia[start:])
    return kawalki


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("katalog")
    ap.add_argument("--limit", type=int, default=900000, help="maks. rozmiar pliku scalenia w bajtach")
    ap.add_argument("--nie-zastepuj-kopii", action="store_true", help="analizuj kopie _copy, ale niczego nie zastepuj")
    ap.add_argument("--tylko-analiza-kopii", action="store_true", help="tylko raport o kopiach _copy (bez zmian i bez scalania)")
    ap.add_argument("--bez-skracania", action="store_true",
                    help="NIE skracaj przeciagniec w tekscie wysylanym do DeepL (domyslnie ciagi 5+ tego samego znaku - litery, ! ? . - sa "
                         "skracane do 4, co zapobiega petlom DeepL; oryginaly sa zawsze nietkniete)")
    ap.add_argument("--skracaj-przeciagniecia", action="store_true", help=argparse.SUPPRESS)   # stara flaga: skracanie jest teraz domyslne
    ap.add_argument("--bez-dzielenia", action="store_true",
                    help="NIE dziel bardzo dlugich linii na kawalki (domyslnie linie dluzsze niz --prog-linii sa dzielone na granicach zdan, "
                         "a rozdziel sklada je z powrotem po tlumaczeniu; DeepL traci jakosc na bardzo dlugich liniach)")
    ap.add_argument("--prog-linii", type=int, default=4000, help="od ilu znakow linia jest dzielona na kawalki (domyslnie 4000)")
    a = ap.parse_args()

    d = os.path.normpath(a.katalog)
    base = os.path.basename(d) + "_all"
    spis_name = os.path.basename(d) + "_spis_scalenia.txt"

    # Analiza kopii _copy PRZED scalaniem (nowsza i wieksza kopia zastepuje oryginal; reszta do decyzji uzytkownika)
    analizuj_kopie(d, zastepuj=not (a.nie_zastepuj_kopii or a.tylko_analiza_kopii))
    if a.tylko_analiza_kopii:
        return 0

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
    items, duze, ostrz_kod, kodowania, skrocone = [], [], [], {}, {}
    dzielone_linie = {}
    for n in names:
        txt, enc = czytaj_plik(os.path.join(d, n))
        kodowania[enc] = kodowania.get(enc, 0) + 1
        if enc in ("utf-16", "cp1250"):      # cp1252 to zwykle ANSI - normalne, bez ostrzezenia
            ostrz_kod.append("%s: odczytano jako %s (nietypowe kodowanie) - sprawdz znaki specjalne" % (n, enc))
        if "\ufffd" in txt:
            ostrz_kod.append("%s: zawiera znak zastepczy U+FFFD (znaki uszkodzone juz w zrodle)" % n)
        if enc in ("cp1252", "cp1250", "utf-8"):      # mieszane kodowanie: bajty D3/D4 (cudzyslow, apostrof) + uszkodzony nastepny znak
            import re as _re
            uszk = len(_re.findall(rb"[\xd3\xd4][\x80-\xbf]", open(os.path.join(d, n), "rb").read()))
            if uszk >= 5 and (enc != "utf-8" or (sum(1 for c in txt if "\u04c0" <= c <= "\u053f") >= 5 and sum(1 for c in txt if "\u0410" <= c <= "\u044f") <= uszk)):
                ostrz_kod.append("%s: wykryto %d uszkodzonych sekwencji cudzyslowow/apostrofow (bajty D3/D4 + uszkodzony znak) - PRZED tlumaczeniem uruchom napraw_kodowanie.py" % (n, uszk))
        txt = txt.replace("\r\n", "\n").strip("\n") + "\n"
        if not a.bez_skracania:                       # tylko tekst do tlumaczenia; znaczniki granic dodawane sa PO tym kroku
            txt, ile = skroc_przeciagniecia(txt)
            if ile:
                skrocone[n] = ile
        if not a.bez_dzielenia:                       # bardzo dlugie linie -> kawalki na granicach zdan (spacja -> nowa linia, rozmiar bez zmian)
            dz, nowe_l = [], []
            for j, l in enumerate(txt.split("\n")[:-1]):
                ch = dziel_dluga_linie(l, a.prog_linii)
                if len(ch) > 1:
                    dz.append((j, len(ch)))
                nowe_l.extend(ch)
            if dz:
                txt = "\n".join(nowe_l) + "\n"
                dzielone_linie[n] = dz
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
        czesci, przerwy = dziel(txt, a.limit)
        nazwy = []
        for i, c in enumerate(czesci, 1):
            fn = "%s_%d.txt" % (stem, i)
            with open(os.path.join(d, fn), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(c)
            nazwy.append((fn, len(c.encode("utf-8")), przerwy[i - 2] if i >= 2 else None))
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
            for fn, fsz, pr in nazwy:
                spis.append("    " + fn + " (" + str(fsz) + " bajtow" + ("" if pr is None else ", przerwa " + str(pr)) + ")")
        spis.append("")
    if dzielone_linie:                      # sekcja NA KONCU spisu (starsze wersje rozdziel ja ignoruja)
        if not podzielone:
            spis.extend(["Pliki podzielone (nie scalane):", "    (brak)", ""])
        spis.append("Linie dzielone (dlugie linie > %d znakow rozdzielone na kawalki; rozdziel sklada je z powrotem):" % a.prog_linii)
        for n in sorted(dzielone_linie, key=str.lower):
            spis.append("    %s: dzielone linie %s" % (n, ", ".join("%dx%d" % x for x in dzielone_linie[n])))
        spis.append("")
    # Spis scalenia: oryginalne nazwy plikow w kazdym pliku scalenia
    with open(os.path.join(d, spis_name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(spis).rstrip("\n") + "\n")
    print(spis_name, "zapisany")
    print("Pominiete (pl/_copy) nie sa wypisywane; scalono plikow:", len(items))
    print("Kodowanie wejscia: " + ", ".join("%s: %d" % (k, v) for k, v in sorted(kodowania.items())))
    print("Kodowanie wyniku: UTF-8 bez BOM, konce linii LF")
    if not a.bez_skracania:
        print("Skracanie przeciagniec (domyslne; --bez-skracania wylacza): %d ciagow w %d plikach (ciagi 5+ tego samego znaku -> 4); oryginaly nietkniete"
              % (sum(skrocone.values()), len(skrocone)))
        for n, k in sorted(skrocone.items(), key=lambda x: -x[1])[:10]:
            print("   - %s: %d" % (n, k))
    if dzielone_linie:
        print("Dzielenie dlugich linii (> %d znakow, domyslne; --bez-dzielenia wylacza): %d linii w %d plikach; rozdziel zlozy je z powrotem po tlumaczeniu"
              % (a.prog_linii, sum(len(v) for v in dzielone_linie.values()), len(dzielone_linie)))
        for n, v in sorted(dzielone_linie.items(), key=lambda x: -len(x[1]))[:10]:
            print("   - %s: %d linii (kawalkow: %d)" % (n, len(v), sum(k for _, k in v)))
    for w in ostrz_kod:
        print("UWAGA (kodowanie):", w)


if __name__ == "__main__":
    sys.exit(main())

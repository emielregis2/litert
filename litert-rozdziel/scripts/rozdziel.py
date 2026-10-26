#!/usr/bin/env python3
"""Rozdziela przetlumaczone pliki scalenia ("... pl.txt") na pliki oryginalne z koncowka " pl".

Wejscie (w katalogu):  NazwaKatalogu_spis_scalenia.txt  oraz  NazwaKatalogu_all_N pl.txt  (lub NazwaKatalogu_all pl.txt)
Wyjscie: "<oryginalna angielska nazwa> pl.txt" dla kazdego pliku ze spisu.
Granice wyznaczaja znaczniki  =====[[N|Nazwa]]=====  - liczy sie tylko numer N; nazwe w znaczniku DeepL mogl przetlumaczyc.
Dodatkowo sklada przetlumaczone czesci duzych plikow (Nazwa_1 pl.txt, Nazwa_2 pl.txt, ...) w jeden plik "Nazwa pl.txt"
na podstawie sekcji "Pliki podzielone" ze spisu.

Po KONTROLI kompletnosci (kazdy plik ze spisu ma zapisany, niepusty wynik "pl" bez znacznikow, bez petli tlumaczenia
(dlugi ciag tego samego znaku, ktorego nie ma w oryginale), bez pominietych akapitow (mniej linii z trescia niz w oryginale)
i bez podejrzanie malego rozmiaru, brak ostrzezen) przenosi angielskie oryginaly do podkatalogu "org", a pliki techniczne KASUJE: pliki scalenia
(_all_N.txt) i ich tlumaczenia (_all_N pl.txt), czesci duzych plikow i ich tlumaczenia, spis oraz archiwa .zip (tylko gdy
zawieraja wylacznie tlumaczenia z tej partii). Raport naprawy zostaje w org. Wynik: w katalogu glownym tylko tlumaczenia,
w org tylko oryginaly. Flagi: --zachowaj-techniczne (pliki techniczne do org zamiast kasowania), --tylko-sprzatanie
(sama kontrola i sprzatanie dla katalogu rozdzielonego wczesniej, bez rozdzielania).
Pojedyncze znaki zastepcze U+FFFD w tlumaczeniu (uszkodzone przez DeepL) sa usuwane z wyniku automatycznie, z raportem
(do --max-fffd na plik; wiecej = ostrzezenie bez usuwania). Przetlumaczone pliki zrodlowe nie sa zmieniane.

Brakujace przetlumaczone pliki skrypt sam wypakowuje z archiwum .zip lezacego w katalogu (np. "DeepL Translations ... .zip"),
tylko te brakujace, bez nadpisywania; wylaczenie: --bez-zip.

Uzycie:  python rozdziel.py "C:\\sciezka\\KATALOG" [--nadpisz] [--bez-org] [--bez-zip] [--max-fffd 10]
                                                         [--zachowaj-techniczne] [--tylko-sprzatanie] [--min-ciag 60]
                                                         [--bez-poprawek] [--tylko-poprawki [--sucho]]
                                                         [--bez-kontroli-akapitow]
"""
import os, re, sys, argparse, shutil, collections

MARK = re.compile(r"^[\s=\-_*#~]*\[\[\s*(\d+)\s*(?:\|[^\]\n]*)?\]\][\s=\-_*#~]*$")


try:  # nazwy plikow z polskimi znakami nie moga wywrocic wypisywania na konsole
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

KODOWANIE = {}   # sciezka -> uzyte kodowanie
PRZERWY = {}     # nazwa czesci -> liczba pustych linii miedzy ta czescia a poprzednia (ze spisu)
PLAN_DZIEL = {}  # nazwa oryginalu -> [(indeks linii oryginalu, liczba kawalkow)] - dlugie linie podzielone przy scalaniu (ze spisu)
POLSKIE = re.compile("[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
# typowe slady UTF-8 odczytanego jako cp1250/cp1252 oraz znak zastepczy
ZEPSUTE = re.compile("Ä…|Ä™|Ä‡|Å‚|Å„|Å›|Åº|Å¼|Ăł|Ã³|\ufffd")


def czytaj(path):
    """Odczyt z wykrywaniem kodowania: UTF-16 (BOM) -> UTF-8 (z BOM lub bez) -> awaryjnie cp1250."""
    raw = open(path, "rb").read()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        enc, txt = "utf-16", raw.decode("utf-16")
    else:
        try:
            enc, txt = "utf-8", raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            enc, txt = "cp1250", raw.decode("cp1250", errors="replace")
    KODOWANIE[path] = enc
    return txt.replace("\r\n", "\n")


def napraw_fffd(tekst, etykieta, max_n, naprawy, nazwy=None, zrodlo=None):
    """Usuwa pojedyncze znaki zastepcze U+FFFD (uszkodzone przez DeepL) z tlumaczenia i zapisuje w 'naprawy', gdzie to zrobiono.
    Gdy w jednym pliku jest ich wiecej niz max_n (wyglada to na systemowe uszkodzenie kodowania, a nie pojedynczy artefakt),
    niczego nie usuwa - sprawdz_pl zglosi wtedy ostrzezenie i przenoszenie do org zostanie wstrzymane. max_n = 0 wylacza usuwanie."""
    n = tekst.count("\ufffd")
    if n == 0 or n > max_n:
        return tekst
    wyn, cur, start = [], None, 0
    for i, line in enumerate(tekst.split("\n"), 1):
        m = MARK.match(line)
        if m:
            cur, start = int(m.group(1)), i
        if "\ufffd" in line:
            naprawy.append({"plik": etykieta, "linia": i, "nr": cur, "nazwa": (nazwy or {}).get(cur),
                            "wynik_linia": (i - start - 1) if cur is not None else None,
                            "ile": line.count("\ufffd"), "zrodlo": zrodlo})
            line = line.replace("\ufffd", "")
        wyn.append(line)
    return "\n".join(wyn)


def sprawdz_pl(nazwa, path, tekst, problemy):
    """Ostrzega, gdy polskie znaki w przetlumaczonym pliku wygladaja na zepsute lub ich brak."""
    if KODOWANIE.get(path) == "cp1250":
        problemy.append("%s: odczytano jako cp1250 (nie UTF-8) - sprawdz polskie znaki" % nazwa)
    if ZEPSUTE.search(tekst):
        problemy.append("%s: wykryto zepsute polskie znaki (np. Å‚, Ä…, U+FFFD) - plik nie jest poprawnym UTF-8" % nazwa)
    elif not POLSKIE.search(tekst):
        problemy.append("%s: brak polskich znakow diakrytycznych - czy to na pewno tlumaczenie?" % nazwa)


def parsuj_spis(path):
    """Zwraca (kolejnosc plikow scalenia, {nr: nazwa oryginalu}, {plik scalenia: [nr,...]},
    [(oryginal duzego pliku, [nazwy czesci w kolejnosci])])"""
    pliki, nazwy, w_pliku, cur = [], {}, {}, None
    podzielone, sekcja_podz, sekcja_dz = [], False, False
    for line in czytaj(path).split("\n"):
        if line.startswith("Linie dzielone"):          # sekcja na koncu spisu: dlugie linie podzielone przy scalaniu
            sekcja_dz, sekcja_podz = True, False
            continue
        if sekcja_dz:
            m = re.match(r"^\s+(.+?\.txt): dzielone linie (.+?)\s*$", line)
            if m:
                PLAN_DZIEL[m.group(1)] = [tuple(int(x) for x in p.split("x")) for p in m.group(2).split(", ")]
            continue
        if line.startswith("Pliki podzielone"):
            sekcja_podz = True
            continue
        if sekcja_podz:
            m = re.match(r"^(\s*)(.+?\.txt)\s*(?:\(\d+ bajtow(?:, przerwa (\d+))?\))?\s*$", line)
            if m and m.group(1) == "" and line.strip():
                podzielone.append((m.group(2), []))
            elif m and m.group(1) and podzielone:
                podzielone[-1][1].append(m.group(2))
                if m.group(3) is not None:
                    PRZERWY[m.group(2)] = int(m.group(3))
            continue
        m = re.match(r"^\s+(\d+)\.\s+(.+?)\s*$", line)
        if m and cur:
            nr = int(m.group(1))
            nazwy[nr] = m.group(2)
            w_pliku[cur].append(nr)
        elif line.strip() and not line.startswith(" "):
            cur = line.strip()
            pliki.append(cur)
            w_pliku[cur] = []
    return pliki, nazwy, w_pliku, podzielone


def _sklej_kawalki(czesci):
    """Sklada kawalki jednej dlugiej linii pojedyncza spacja; zachowuje spacje na poczatku pierwszego i na koncu ostatniego kawalka
    (wciecie akapitu, spacja na koncu linii), a w miejscach laczenia usuwa nadmiarowe."""
    wynik = czesci[0].rstrip()
    for x in czesci[1:-1]:
        wynik += " " + x.strip()
    if len(czesci) > 1:
        wynik += " " + czesci[-1].lstrip()
    return wynik


def zloz_dzielone(tekst, orig, d, problemy, etykieta):
    """Sklada z powrotem dlugie linie, ktore scal.py podzielil na kawalki (plan ze spisu). Skladamy TYLKO wtedy, gdy uklad linii (puste/niepuste)
    wyniku dokladnie zgadza sie z oczekiwanym; w przeciwnym razie nic nie zmieniamy i zglaszamy problem (DeepL mogl scalic lub pominac linie)."""
    plan = PLAN_DZIEL.get(orig)
    if not plan:
        return tekst
    op = next((x for x in (os.path.join(d, orig), os.path.join(d, "org", orig)) if os.path.isfile(x)), None)
    if not op:
        problemy.append("%s: NIE zlozono dlugich linii (brak oryginalu %s do sprawdzenia ukladu)" % (etykieta, orig))
        return tekst
    raw = open(op, "rb").read()
    try:
        o = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        o = raw.decode("cp1252", errors="replace")
    lo = o.replace("\r\n", "\n").strip("\n").split("\n")
    k_dla = dict(plan)
    oczek = []
    for j, l in enumerate(lo):
        oczek += [bool(l.strip())] * k_dla.get(j, 1)
    wyn = tekst.split("\n")
    if wyn and wyn[-1] == "":
        wyn = wyn[:-1]
    if [bool(x.strip()) for x in wyn] != oczek:
        problemy.append("%s: NIE zlozono dlugich linii (podzielonych przy scalaniu): uklad linii wyniku (%d) nie zgadza sie z oczekiwanym (%d) - DeepL mogl scalic lub pominac linie"
                        % (etykieta, len(wyn), len(oczek)))
        return tekst
    nowe, i = [], 0
    for j in range(len(lo)):
        k = k_dla.get(j, 1)
        nowe.append(wyn[i] if k == 1 else _sklej_kawalki(wyn[i:i + k]))
        i += k
    print("   zlozono dlugie linie: %s (%d linii z %d kawalkow)" % (etykieta, len(plan), sum(k for _, k in plan)))
    return "\n".join(nowe) + "\n"


def uzupelnij_z_zip(d, oczekiwane):
    """Brakujace przetlumaczone pliki (lista nazw) probuje wypakowac z archiwow .zip lezacych w katalogu
    (np. 'DeepL Translations ... .zip'). Wypakowuje TYLKO brakujace pliki o oczekiwanych nazwach (dopasowanie po
    nazwie, bez sciezek z archiwum), nigdy nie nadpisuje istniejacych plikow i nie kasuje archiwum.
    Gdy ten sam plik jest w kilku archiwach, wybiera najnowsze archiwum."""
    import zipfile
    brak = [n for n in oczekiwane if not os.path.exists(os.path.join(d, n))]
    if not brak:
        return []
    zipy = sorted((f for f in os.listdir(d) if f.lower().endswith(".zip") and os.path.isfile(os.path.join(d, f))),
                  key=lambda f: os.path.getmtime(os.path.join(d, f)), reverse=True)
    if not zipy:
        return []
    wypakowane = []
    for zn in zipy:
        if not brak:
            break
        try:
            z = zipfile.ZipFile(os.path.join(d, zn))
        except zipfile.BadZipFile:
            print("UWAGA: ZIP: uszkodzone archiwum, pomijam:", zn)
            continue
        wpisy = {}
        for info in z.infolist():
            if not info.is_dir():
                wpisy.setdefault(os.path.basename(info.filename.replace("\\", "/")).lower(), info)
        for n in list(brak):
            info = wpisy.get(n.lower())
            if info is None:
                continue
            dane = z.read(info)                      # zipfile weryfikuje sume kontrolna CRC
            try:
                with open(os.path.join(d, n), "xb") as fh:   # tryb 'x': nigdy nie nadpisuje
                    fh.write(dane)
            except FileExistsError:
                continue
            wypakowane.append((n, zn, len(dane)))
            brak.remove(n)
            print("ZIP: wypakowano brakujacy plik %s z archiwum %s (%d bajtow)" % (n, zn, len(dane)))
        z.close()
    if brak:
        print("ZIP: w archiwach (%s) nie znaleziono: %s" % (", ".join(zipy), ", ".join(brak)))
    return wypakowane


def _usun(pth, proby=6, pauza=1.0):
    """Kasuje plik z ponawianiem: Dropbox lub antywirus potrafia chwilowo zablokowac swiezo zapisany plik (PermissionError).
    Zwraca True, gdy pliku juz nie ma."""
    import time
    for _ in range(proby):
        try:
            os.remove(pth)
            return True
        except FileNotFoundError:
            return True
        except OSError:
            time.sleep(pauza)
    return not os.path.exists(pth)


def _przenies(src, dst, proby=6, pauza=1.0):
    """Przenosi plik z ponawianiem przy chwilowej blokadzie. Zwraca True, gdy plik jest w miejscu docelowym."""
    import time
    for _ in range(proby):
        try:
            shutil.move(src, dst)
            return True
        except OSError:
            time.sleep(pauza)
    return os.path.exists(dst) and not os.path.exists(src)


def _do_kosza(path):
    """Przenosi plik do Kosza (tylko Windows). Zwraca True, gdy pliku juz nie ma w miejscu."""
    if os.name != "nt":
        return False
    import ctypes

    class SHFILEOPSTRUCT(ctypes.Structure):
        _fields_ = [("hwnd", ctypes.c_void_p), ("wFunc", ctypes.c_uint), ("pFrom", ctypes.c_wchar_p), ("pTo", ctypes.c_wchar_p),
                    ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", ctypes.c_int), ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", ctypes.c_wchar_p)]
    op = SHFILEOPSTRUCT()
    op.wFunc = 3                                  # FO_DELETE
    op.pFrom = path + "\0"
    op.pTo = None
    op.fFlags = 0x40 | 0x10 | 0x4 | 0x400         # ALLOWUNDO (Kosz), bez pytan i okien
    wynik = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return wynik == 0 and not op.fAnyOperationsAborted and not os.path.exists(path)


def wczytaj_poprawki(sciezka=None):
    """Slownik poprawek bledow DeepL (plik poprawki_deepl.txt obok SKILL.md): linie 'zle => dobrze', '#' = komentarz.
    Zamieniane sa tylko cale wyrazy, bez rozroznienia wielkosci liter (wielkosc liter jest zachowana)."""
    sciezka = sciezka or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "poprawki_deepl.txt")
    reguly = []
    if os.path.isfile(sciezka):
        for linia in open(sciezka, encoding="utf-8-sig"):
            linia = linia.split("#", 1)[0].strip()
            if "=>" in linia:
                z, d = (x.strip() for x in linia.split("=>", 1))
                if z and d:
                    reguly.append((z, d))
    return reguly


def zastosuj_poprawki(tekst, reguly):
    """Zwraca (nowy_tekst, Counter regula -> liczba zamian). Nie zmienia liczby linii."""
    liczby = collections.Counter()
    for z, d in reguly:
        rx = re.compile(r"(?<![^\W\d_])" + re.escape(z) + r"(?![^\W\d_])", re.I)

        def zam(m, z=z, d=d):
            s = m.group(0)
            liczby[z] += 1
            if len(s) > 1 and s.isupper():
                return d.upper()
            if s[0].isupper():
                return d[0].upper() + d[1:]
            return d
        tekst = rx.sub(zam, tekst)
    return tekst, liczby


def tylko_poprawki(d, reguly, sucho=False):
    """Stosuje slownik poprawek do istniejacych tlumaczen ' pl.txt' w katalogu (bez spisu, bez org). sucho=True: tylko liczby."""
    if not reguly:
        print("BLAD: brak regul (plik poprawki_deepl.txt)")
        return 1
    lacznie, sprawdzone, zmienione = collections.Counter(), 0, 0
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if not (f.endswith(" pl.txt") and os.path.isfile(p)) or re.search(r"_all(_\d+)? pl\.txt$", f) or f.startswith("DO_PRZETLUMACZENIA"):
            continue
        sprawdzone += 1
        try:
            t = open(p, "rb").read().decode("utf-8")
        except UnicodeDecodeError:
            print("POMINIETO (nie jest UTF-8):", f)
            continue
        nowy, l = zastosuj_poprawki(t, reguly)
        if l:
            zmienione += 1
            lacznie.update(l)
            if not sucho:
                with open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(nowy)
    print("POPRAWKI SLOWNIKOWE%s: sprawdzono %d plikow, %s %d, zamian %d%s" % (
        " (SUCHO: nic nie zapisano)" if sucho else "", sprawdzone, "do zmiany" if sucho else "zmieniono", zmienione, sum(lacznie.values()),
        (" (" + ", ".join("%s=%d" % kv for kv in lacznie.most_common()) + ")") if lacznie else ""))
    return 0


def _raport_czkawki(nazwa, tekst, op):
    """Informacyjny raport 'czkawki' DeepL (nie blokuje): nadwyzka podwojonych slow, powtorzonych sasiednich linii i 4x tego samego slowa
    wzgledem oryginalu."""
    o = ""
    if op:
        raw = open(op, "rb").read()
        try:
            o = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            o = raw.decode("cp1252", errors="replace")
    dbl = re.compile(r"\b([^\W\d_]{3,})\s+\1\b", re.I)
    x4 = re.compile(r"\b([^\W\d_]+)(?:\s+\1){3,}\b", re.I)

    def powt(txt):
        L = [x.strip() for x in txt.split("\n") if x.strip()]
        return sum(1 for a, b in zip(L, L[1:]) if len(a) >= 25 and a == b)
    nad = len(dbl.findall(tekst)) - len(dbl.findall(o))
    if nad >= 20 and 1e4 * nad / max(1, len(tekst.split())) >= 50:
        print("INFO: CZKAWKA: %s: %d podwojonych slow ponad oryginal (%.0f na 10 tys. slow) - DeepL mogl podwajac slowa" % (nazwa, nad, 1e4 * nad / max(1, len(tekst.split()))))
    if powt(tekst) - powt(o) >= 3:
        print("INFO: CZKAWKA: %s: %d powtorzonych sasiednich linii ponad oryginal" % (nazwa, powt(tekst) - powt(o)))
    if len(x4.findall(tekst)) - len(x4.findall(o)) >= 3:
        print("INFO: CZKAWKA: %s: to samo slowo 4 razy z rzedu: %d miejsc ponad oryginal" % (nazwa, len(x4.findall(tekst)) - len(x4.findall(o))))


def oczekiwane_pliki(nazwy, pliki, podzielone):
    """Zwraca (oryginaly, wyniki, pliki techniczne) na podstawie spisu."""
    oryginaly = [nazwy[nr] for nr in sorted(nazwy)] + [o for o, _ in podzielone]
    wyniki = [o[:-4] + " pl.txt" for o in oryginaly]
    czesci = [c for _, cz in podzielone for c in cz]
    tech = list(pliki) + [pl[:-4] + " pl.txt" for pl in pliki] + czesci + [c[:-4] + " pl.txt" for c in czesci]
    return oryginaly, wyniki, tech


def _sprawdz_petle(nazwa, tekst, op, min_ciag, problemy):
    """Wykrywa 'petle' tlumaczenia: dlugi ciag tego samego znaku (>= min_ciag) w wyniku, ktorego nie ma w oryginale
    (ciag musi byc ponad 2x dluzszy niz najdluzszy ciag tego znaku w oryginale). Taka petla (np. setki liter K) oznacza,
    ze DeepL utknal, a tekst za nia mogl zostac zgubiony. Bez oryginalu flaguje dopiero ciagi >= 5 * min_ciag."""
    import re as _re
    petle = list(_re.finditer(r"([^\s])\1{%d,}" % (min_ciag - 1), tekst))
    if not petle:
        return
    o = None
    if op:
        raw = open(op, "rb").read()
        try:
            o = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            o = raw.decode("cp1252", errors="replace")
    najdl = {}
    zgloszone = 0
    for m in petle:
        c, dl = m.group(1), len(m.group(0))
        if c not in najdl:
            najdl[c] = max((len(x.group(0)) for x in _re.finditer(_re.escape(c) + "+", o)), default=0) if o is not None else None
        if najdl[c] is None:
            podejrzana = dl >= 5 * min_ciag
        else:
            podejrzana = dl > 2 * najdl[c]
        if podejrzana:
            zgloszone += 1
            if zgloszone <= 5:
                linia = tekst.count("\n", 0, m.start()) + 1
                problemy.append("KONTROLA: w wyniku %s, linia %d: ciag %d x '%s' (najdluzszy ciag tego znaku w oryginale: %s) - wyglada na petle "
                                "tlumaczenia DeepL (tekst za nia mogl zostac zgubiony)" % (nazwa, linia, dl, c, "brak oryginalu" if najdl[c] is None else najdl[c]))


def _pominiete_akapity(dl_o, dl_w):
    """Ktore linie z trescia oryginalu (indeksy w dl_o = dlugosci linii oryginalu) nie maja odpowiednika w wyniku (dl_w)?
    Dopasowanie programowaniem dynamicznym w waskim pasie po dlugosciach linii (tlumaczenie jest ok. 1.13x dluzsze).
    Zwraca posortowana liste indeksow pominietych linii oryginalu albo None, gdy sie nie da (np. wynik ma wiecej linii)."""
    import math
    n, m = len(dl_o), len(dl_w)
    k = n - m
    if k <= 0 or k > 60:
        return None
    szer = k + 6
    INF = 1e18
    dp = [[INF] * (szer + 1) for _ in range(n + 1)]
    prev = [[None] * (szer + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n):
        for d in range(szer + 1):
            c = dp[i][d]
            if c >= INF:
                continue
            j = i - d
            if 0 <= j < m:                                          # dopasuj linie oryginalu i z linia wyniku j
                nc = c + abs(math.log((dl_w[j] + 5) / (1.13 * dl_o[i] + 5)))
                if nc < dp[i + 1][d]:
                    dp[i + 1][d] = nc
                    prev[i + 1][d] = (d, "m")
            if d + 1 <= szer:                                       # linia oryginalu pominieta w wyniku
                nc = c + 1.6
                if nc < dp[i + 1][d + 1]:
                    dp[i + 1][d + 1] = nc
                    prev[i + 1][d + 1] = (d, "s")
    if dp[n][k] >= INF:
        return None
    wynik, d, i = [], k, n
    while i > 0:
        pd, op = prev[i][d]
        if op == "s":
            wynik.append(i - 1)
        d, i = pd, i - 1
    return sorted(wynik)


def _sprawdz_akapity(nazwa, tekst, op, problemy, krotko=20):
    """Kontrola liczby linii z trescia: DeepL potrafi po cichu pominac akapit. Wynik z mniejsza liczba linii z trescia niz oryginal
    to problem (pominiecia linii do 'krotko' znakow sa tylko zgloszone jako INFO i nie blokuja)."""
    raw = open(op, "rb").read()
    try:
        o = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        o = raw.decode("cp1252", errors="replace")
    lo = [(i + 1, len(x.strip())) for i, x in enumerate(o.replace("\r\n", "\n").split("\n")) if x.strip()]
    lw = [len(x.strip()) for x in tekst.split("\n") if x.strip()]
    if len(lw) == len(lo):
        return
    if len(lw) > len(lo):
        print("INFO: wynik %s ma wiecej linii z trescia niz oryginal (%d wobec %d) - mozliwy podzial linii" % (nazwa, len(lw), len(lo)))
        return
    idx = _pominiete_akapity([l for _, l in lo], lw)
    if idx is None:
        problemy.append("KONTROLA: wynik %s ma mniej linii z trescia niz oryginal (%d wobec %d) - DeepL mogl pominac akapity (nie udalo sie ustalic ktore)"
                        % (nazwa, len(lw), len(lo)))
        return
    duze = ["%d (%d zn.)" % lo[i] for i in idx if lo[i][1] > krotko]
    male = [str(lo[i][0]) for i in idx if lo[i][1] <= krotko]
    if male:
        print("INFO: w wyniku %s brakuje %d krotkich linii oryginalu (do %d znakow): linie %s" % (nazwa, len(male), krotko, ", ".join(male[:10])))
    if duze:
        problemy.append("KONTROLA: w wyniku %s brakuje %d akapitow oryginalu (DeepL je pominal lub scalil z sasiednia linia - zweryfikuj tlumaczeniem pliku pomocniczego): linie oryginalu %s" % (nazwa, len(duze), ", ".join(duze[:10])))


def zweryfikuj_wyniki(d, org, oryginaly, wyniki, min_ciag=60, kontrola_akapitow=True):
    """Kontrola, czy kazdy wynik jest zapisany i kompletny: istnieje, nie jest pusty, jest poprawnym UTF-8,
    nie ma znacznikow granic, nie ma 'petli' (dlugiego ciagu tego samego znaku, ktorego brak w oryginale) i nie jest
    podejrzanie maly wzgledem oryginalu (ucięte tlumaczenie)."""
    problemy = []
    for o, w in zip(oryginaly, wyniki):
        wp = os.path.join(d, w)
        if not os.path.isfile(wp):
            problemy.append("KONTROLA: brak wyniku " + w)
            continue
        raw = open(wp, "rb").read()
        if not raw:
            problemy.append("KONTROLA: pusty wynik " + w)
            continue
        try:
            t = raw.decode("utf-8")
        except UnicodeDecodeError:
            problemy.append("KONTROLA: wynik %s nie jest poprawnym UTF-8" % w)
            continue
        if "=====[[" in t:
            problemy.append("KONTROLA: w wyniku %s pozostal znacznik granicy" % w)
        if not t.endswith("\n"):
            problemy.append("KONTROLA: wynik %s nie konczy sie znakiem nowej linii" % w)
        op = next((x for x in (os.path.join(d, o), os.path.join(org, o)) if os.path.isfile(x)), None)
        if op:
            so = os.path.getsize(op)
            if so >= 2000 and len(raw) < 0.85 * so:
                problemy.append("KONTROLA: wynik %s jest podejrzanie krotki (%.2f rozmiaru oryginalu) - tlumaczenie moglo zostac ucięte"
                                % (w, len(raw) / so))
        if min_ciag > 0:
            _sprawdz_petle(w, t, op, min_ciag, problemy)
        if kontrola_akapitow and op:
            _sprawdz_akapity(w, t, op, problemy)
        _raport_czkawki(w, t, op)
    return problemy


def wykonaj_sprzatanie(d, spis_nazwa, oryginaly, wyniki, tech, raport_nazwa, zachowaj):
    """Po pozytywnej kontroli: oryginaly -> org (z weryfikacja rozmiaru), pliki techniczne (scalenia i ich tlumaczenia,
    czesci i ich tlumaczenia, spis, archiwa .zip zawierajace wylacznie tlumaczenia z tej partii) -> KASOWANE
    (zachowaj=True: przenoszone do org). Niczego spoza tej listy nie rusza."""
    import zipfile
    org = os.path.join(d, "org")
    os.makedirs(org, exist_ok=True)
    chronione = {x.lower() for x in list(oryginaly) + list(wyniki)}
    przen, ostrz = [], []
    for o in dict.fromkeys(oryginaly):
        zrodlo, cel = os.path.join(d, o), os.path.join(org, o)
        if os.path.exists(zrodlo):
            if os.path.exists(cel):
                ostrz.append("oryginal %s jest juz w org - nie przeniesiono (zostaje tez w katalogu glownym)" % o)
            else:
                rozm = os.path.getsize(zrodlo)
                _przenies(zrodlo, cel)
                if os.path.exists(cel) and os.path.getsize(cel) == rozm:
                    przen.append(o)
                else:
                    ostrz.append("BLAD przenoszenia oryginalu " + o)
    brak_org = [o for o in dict.fromkeys(oryginaly) if not os.path.exists(os.path.join(org, o))]
    rp, rc = os.path.join(d, raport_nazwa), os.path.join(org, raport_nazwa)
    if os.path.exists(rp) and not os.path.exists(rc):
        _przenies(rp, rc)
        przen.append(raport_nazwa)
    print("ORG: przeniesiono %d plikow do %s (oryginaly%s)" % (len(przen), org, " i raport naprawy" if raport_nazwa in przen else ""))
    for w in ostrz:
        print("UWAGA: ORG:", w)
    if brak_org:
        print("UWAGA: SPRZATANIE: w org brakuje %d oryginalow (np. %s) - pliki techniczne zostaja, niczego nie kasuje" % (len(brak_org), brak_org[0]))
        return
    oczek_pl = {t.lower() for t in tech if t.endswith(" pl.txt")}
    dup_do_usuniecia = []                 # kolejne pobrania tego samego tlumaczenia z DeepL: "X pl (1).txt", "X pl (2).txt"
    for baza in (d, org):
        for f in sorted(os.listdir(baza)):
            m = re.match(r"^(.+ pl) \(\d+\)\.txt$", f)
            if not m or (m.group(1) + ".txt").lower() not in oczek_pl:
                continue
            pk, pf = os.path.join(baza, m.group(1) + ".txt"), os.path.join(baza, f)
            if os.path.isfile(pk) and open(pk, "rb").read() == open(pf, "rb").read():
                dup_do_usuniecia.append(pf)
            else:
                print("UWAGA: SPRZATANIE: %s wyglada na kolejne pobranie z DeepL, ale rozni sie od %s.txt (lub go brak) - zostawiam" % (f, m.group(1)))
    usuniete, przeniesione_tech = [], []
    for n in dict.fromkeys(list(tech) + [spis_nazwa]):
        if n.lower() in chronione:
            continue
        for baza in (d, org):
            pth = os.path.join(baza, n)
            if not os.path.isfile(pth):
                continue
            rozm = os.path.getsize(pth)
            if zachowaj:
                if baza == d and not os.path.exists(os.path.join(org, n)):
                    _przenies(pth, os.path.join(org, n))
                    przeniesione_tech.append(n)
            else:
                _usun(pth)
                if os.path.exists(pth):
                    print("UWAGA: SPRZATANIE: nie udalo sie usunac", pth)
                else:
                    usuniete.append((n, rozm))
    for pf in dup_do_usuniecia:
        rozm = os.path.getsize(pf)
        if zachowaj:
            if os.path.dirname(pf) == d and not os.path.exists(os.path.join(org, os.path.basename(pf))):
                _przenies(pf, os.path.join(org, os.path.basename(pf)))
                przeniesione_tech.append(os.path.basename(pf))
        else:
            _usun(pf)
            if os.path.exists(pf):
                print("UWAGA: SPRZATANIE: nie udalo sie usunac", pf)
            else:
                usuniete.append((os.path.basename(pf), rozm))
    for baza in (d, org):
        for z in sorted(f for f in os.listdir(baza) if f.lower().endswith(".zip") and os.path.isfile(os.path.join(baza, f))):
            zp = os.path.join(baza, z)
            try:
                with zipfile.ZipFile(zp) as zf:
                    wpisy = [os.path.basename(i.filename.replace("\\", "/")).lower() for i in zf.infolist() if not i.is_dir()]
            except zipfile.BadZipFile:
                print("UWAGA: SPRZATANIE: archiwum %s jest uszkodzone - zostawiam" % z)
                continue
            if wpisy and all(w in oczek_pl for w in wpisy):
                rozm = os.path.getsize(zp)
                if zachowaj:
                    if baza == d and not os.path.exists(os.path.join(org, z)):
                        _przenies(zp, os.path.join(org, z))
                        przeniesione_tech.append(z)
                else:
                    _usun(zp)
                    if os.path.exists(zp):
                        print("UWAGA: SPRZATANIE: nie udalo sie usunac", zp)
                    else:
                        usuniete.append((z, rozm))
            else:
                print("UWAGA: SPRZATANIE: archiwum %s zawiera pliki spoza tej partii - zostawiam" % z)
    if zachowaj:
        print("SPRZATANIE: pliki techniczne przeniesione do org (--zachowaj-techniczne): %d" % len(przeniesione_tech))
    else:
        print("SPRZATANIE: skasowano %d plikow technicznych (%d B lacznie)" % (len(usuniete), sum(r for _, r in usuniete)))
        for n, r in usuniete:
            print("   - %s (%d B)" % (n, r))
        # pliki pomocnicze dodatkowych tlumaczen (petle, pominiete akapity): zasada Darka - zawsze na koniec je sprzatamy (do Kosza)
        pomocnicze = []
        for f in sorted(os.listdir(d)):
            pf = os.path.join(d, f)
            if re.match(r"^DO_PRZETLUMACZENIA_.*\.txt$", f) and os.path.isfile(pf):
                if _do_kosza(pf) or _usun(pf):
                    pomocnicze.append(f)
                else:
                    print("UWAGA: SPRZATANIE: nie udalo sie usunac pliku pomocniczego", pf)
        if pomocnicze:
            print("SPRZATANIE: pliki pomocnicze DO_PRZETLUMACZENIA_* przeniesione do Kosza: %d (%s)" % (len(pomocnicze), ", ".join(pomocnicze)))
    gl = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
    print("STAN KONCOWY: katalog glowny: %d plikow (w tym %d tlumaczen), org: %d plikow" % (len(gl), sum(1 for f in gl if f.lower() in {w.lower() for w in wyniki}), len(os.listdir(org))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("katalog")
    ap.add_argument("--nadpisz", action="store_true", help="nadpisz istniejace pliki wynikowe")
    ap.add_argument("--bez-org", action="store_true", help="nie przenos plikow zrodlowych do podkatalogu org")
    ap.add_argument("--bez-zip", action="store_true", help="nie uzupelniaj brakujacych tlumaczen z archiwow .zip w katalogu")
    ap.add_argument("--max-fffd", type=int, default=10,
                    help="ile znakow U+FFFD w jednym przetlumaczonym pliku usuwac automatycznie (0 = nie usuwaj; wiecej = ostrzezenie)")
    ap.add_argument("--zachowaj-techniczne", action="store_true",
                    help="pliki techniczne (scalenia, spis, czesci, zip) przenies do org zamiast je kasowac")
    ap.add_argument("--tylko-sprzatanie", action="store_true",
                    help="tylko kontrola kompletnosci i sprzatanie (bez rozdzielania) - dla katalogu rozdzielonego wczesniej")
    ap.add_argument("--min-ciag", type=int, default=60,
                    help="od ilu powtorzen jednego znaku ciag w wyniku jest sprawdzany jako mozliwa petla DeepL (0 = wylacz kontrole)")
    ap.add_argument("--bez-kontroli-akapitow", action="store_true",
                    help="wylacz kontrole liczby linii z trescia (wykrywanie akapitow pominietych przez DeepL)")
    ap.add_argument("--bez-poprawek", action="store_true", help="nie stosuj slownika poprawek DeepL (poprawki_deepl.txt) przy zapisie wynikow")
    ap.add_argument("--tylko-poprawki", action="store_true",
                    help="tylko zastosuj slownik poprawek DeepL do istniejacych tlumaczen ' pl.txt' w katalogu (bez rozdzielania i sprzatania)")
    ap.add_argument("--sucho", action="store_true", help="z --tylko-poprawki: tylko policz zamiany, nic nie zapisuj")
    a = ap.parse_args()
    d = os.path.normpath(a.katalog)
    reguly = [] if a.bez_poprawek else wczytaj_poprawki()
    zam_licznik, zam_plikow = collections.Counter(), [0]
    if a.tylko_poprawki:
        return tylko_poprawki(d, reguly, a.sucho)
    spis_nazwa = os.path.basename(d) + "_spis_scalenia.txt"
    spis_path = os.path.join(d, spis_nazwa)
    if a.tylko_sprzatanie and not os.path.exists(spis_path) and os.path.exists(os.path.join(d, "org", spis_nazwa)):
        spis_path = os.path.join(d, "org", spis_nazwa)       # spis zostal w org po wczesniejszym rozdzieleniu
    if not os.path.exists(spis_path):
        print("BLAD: brak pliku spisu:", spis_path)
        if os.path.exists(os.path.join(d, "org", os.path.basename(spis_path))):
            print("      Spis jest w podkatalogu org - pliki zrodlowe zostaly juz przeniesione po poprzednim rozdzieleniu.")
        return 1
    pliki, nazwy, w_pliku, podzielone = parsuj_spis(spis_path)
    if a.tylko_sprzatanie:      # sama kontrola kompletnosci i sprzatanie, bez rozdzielania
        oryginaly, wyniki, tech = oczekiwane_pliki(nazwy, pliki, podzielone)
        brak = [w for w in wyniki if not os.path.exists(os.path.join(d, w))]
        weryf = [] if brak else zweryfikuj_wyniki(d, os.path.join(d, "org"), oryginaly, wyniki, a.min_ciag, not a.bez_kontroli_akapitow)
        for w in brak:
            print("UWAGA: BRAK wyniku:", w)
        for w in weryf:
            print("UWAGA:", w)
        if brak or weryf or not wyniki:
            print("SPRZATANIE: nic nie przenosze i niczego nie kasuje - kontrola nie przeszla (brakujace wyniki: %d, uwagi: %d)" % (len(brak), len(weryf)))
            return 2
        print("KONTROLA: %d z %d wynikow zapisanych i kompletnych" % (len(wyniki), len(wyniki)))
        wykonaj_sprzatanie(d, spis_nazwa, oryginaly, wyniki, tech, os.path.basename(d) + "_raport_naprawy.txt", a.zachowaj_techniczne)
        return 0
    if not a.bez_zip:   # brakujace przetlumaczone pliki wypakuj z archiwum .zip z DeepL (jesli lezy w katalogu)
        oczek_pl = [pl[:-4] + " pl.txt" for pl in pliki] + [c[:-4] + " pl.txt" for _, cz in podzielone for c in cz]
        uzupelnij_z_zip(d, oczek_pl)
    problemy, zapisane = [], 0
    naprawy = []                                                   # usuniete znaki U+FFFD (do raportu)
    raport_nazwa = os.path.basename(d) + "_raport_naprawy.txt"

    for plik in pliki:
        pl_name = plik[:-4] + " pl.txt"
        pl_path = os.path.join(d, pl_name)
        if not os.path.exists(pl_path):
            problemy.append("BRAK przetlumaczonego pliku: " + pl_name)
            continue
        czesci, cur, przed = {}, None, []
        tekst_pl = napraw_fffd(czytaj(pl_path), pl_name, a.max_fffd, naprawy, nazwy)
        sprawdz_pl(pl_name, pl_path, tekst_pl, problemy)
        for line in tekst_pl.split("\n"):
            m = MARK.match(line)
            if m:
                cur = int(m.group(1))
                if cur in czesci:
                    problemy.append("%s: znacznik %d wystapil wiecej niz raz" % (pl_name, cur))
                czesci.setdefault(cur, [])
            elif cur is None:
                przed.append(line)
            else:
                czesci[cur].append(line)
        if any(x.strip() for x in przed):
            problemy.append("%s: tekst przed pierwszym znacznikiem (nie zapisany)" % pl_name)
        oczek, znal = w_pliku[plik], set(czesci)
        for nr in oczek:
            if nr not in znal:
                problemy.append("%s: BRAK znacznika %d (%s) - tego pliku nie rozdzielono" % (pl_name, nr, nazwy[nr]))
        for nr in sorted(znal - set(oczek)):
            problemy.append("%s: nadmiarowy znacznik %d (nie ma go w spisie dla tego pliku)" % (pl_name, nr))
        # Gdy brakuje znacznika, tekst tego pliku skleilby sie z POPRZEDNIM - jego nie zapisujemy
        podejrzane = {oczek[i - 1] for i, nr in enumerate(oczek) if nr not in znal and i > 0}
        for nr in oczek:
            if nr not in czesci:
                continue
            if nr in podejrzane:
                problemy.append("%s: %s (%d) NIE zapisano - nastepny plik nie ma znacznika, tekst moglby sie skleic"
                                % (pl_name, nazwy[nr], nr))
                continue
            tekst = "\n".join(czesci[nr]).strip("\n") + "\n"
            out_name = nazwy[nr][:-4] + " pl.txt"
            out_path = os.path.join(d, out_name)
            if os.path.exists(out_path) and not a.nadpisz:
                problemy.append("POMINIETO (plik juz istnieje, uzyj --nadpisz): " + out_name)
                continue
            tekst = zloz_dzielone(tekst, nazwy[nr], d, problemy, out_name)
            tekst, _zl = zastosuj_poprawki(tekst, reguly)
            if _zl:
                zam_licznik.update(_zl)
                zam_plikow[0] += 1
            with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(tekst)
            zapisane += 1
            print("OK", out_name, len(tekst.encode("utf-8")), "bajtow")
    # Skladanie przetlumaczonych czesci duzych plikow: Nazwa_1 pl.txt + Nazwa_2 pl.txt + ... -> Nazwa pl.txt
    for orig, czesci_nazwy in podzielone:
        out_name = orig[:-4] + " pl.txt"
        out_path = os.path.join(d, out_name)
        pl_czesci = [c[:-4] + " pl.txt" for c in czesci_nazwy]
        brak = [c for c in pl_czesci if not os.path.exists(os.path.join(d, c))]
        if brak:
            problemy.append("%s: nie zlozono - BRAK przetlumaczonych czesci: %s" % (out_name, ", ".join(brak)))
            continue
        if os.path.exists(out_path) and not a.nadpisz:
            problemy.append("POMINIETO (plik juz istnieje, uzyj --nadpisz): " + out_name)
            continue
        kawalki = []
        for c in pl_czesci:
            t = napraw_fffd(czytaj(os.path.join(d, c)), c, a.max_fffd, naprawy, None, orig)
            sprawdz_pl(c, os.path.join(d, c), t, problemy)
            kawalki.append(t)
        if all(cn in PRZERWY for cn in czesci_nazwy[1:]):
            # nowy format spisu: czesci nie maja pustych linii na brzegach, a liczba pustych linii miedzy nimi jest w spisie
            tekst = kawalki[0].strip("\n") + "\n"
            for cn, kw in zip(czesci_nazwy[1:], kawalki[1:]):
                tekst += "\n" * PRZERWY[cn] + kw.strip("\n") + "\n"
        else:                                       # starszy spis (bez informacji o przerwach): laczenie bez zmian
            tekst = "".join(k if k.endswith("\n") else k + "\n" for k in kawalki)
        tekst = zloz_dzielone(tekst, orig, d, problemy, out_name)
        tekst, _zl = zastosuj_poprawki(tekst, reguly)
        if _zl:
            zam_licznik.update(_zl)
            zam_plikow[0] += 1
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(tekst)
        zapisane += 1
        print("OK (zlozono z %d czesci)" % len(pl_czesci), out_name, len(tekst.encode("utf-8")), "bajtow")
    print("Zapisano plikow:", zapisane, "(UTF-8 bez BOM, konce linii LF)")
    if zam_licznik:
        print("POPRAWKI SLOWNIKOWE: %d zamian w %d plikach (%s)" % (sum(zam_licznik.values()), zam_plikow[0], ", ".join("%s=%d" % kv for kv in zam_licznik.most_common())))
    for p in problemy:
        print("UWAGA:", p)
    if naprawy:   # raport z automatycznego usuwania znakow U+FFFD (tez zapisywany do pliku)
        import datetime
        lacznie = sum(x["ile"] for x in naprawy)
        raport = ["NAPRAWA U+FFFD: usunieto %d znak(ow) w %d miejscu(ach) (limit na plik: %d)" % (lacznie, len(naprawy), a.max_fffd)]
        for x in naprawy:
            if x["nr"] is not None:
                gdzie = "plik nr %d%s%s" % (x["nr"], " '%s'" % x["nazwa"] if x["nazwa"] else "",
                        ", linia %d wyniku '%s'" % (x["wynik_linia"], x["nazwa"][:-4] + " pl.txt") if x["nazwa"] else "")
            else:
                gdzie = "czesc duzego pliku '%s'" % x["zrodlo"] if x["zrodlo"] else "poza znacznikami"
            raport.append("   - '%s', linia %d (%s), znakow w linii: %d" % (x["plik"], x["linia"], gdzie, x["ile"]))
        for l in raport:
            print(l)
        with open(os.path.join(d, raport_nazwa), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("%s\n%s\n\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "\n".join(raport)))

    # Kontrola kompletnosci; gdy wszystko OK: oryginaly do org, pliki techniczne kasowane (--zachowaj-techniczne: do org)
    if a.bez_org:
        print("ORG: pominieto (--bez-org)")
    else:
        krytyczne = [p for p in problemy if not p.startswith("POMINIETO")]
        oryginaly, wyniki, tech = oczekiwane_pliki(nazwy, pliki, podzielone)
        brak_wynikow = [w for w in wyniki if not os.path.exists(os.path.join(d, w))]
        weryf = [] if brak_wynikow else zweryfikuj_wyniki(d, os.path.join(d, "org"), oryginaly, wyniki, a.min_ciag, not a.bez_kontroli_akapitow)
        for w in weryf:
            print("UWAGA:", w)
        problemy.extend(weryf)
        if krytyczne or brak_wynikow or weryf or not wyniki:
            print("ORG: nie przenosze plikow i niczego nie kasuje - rozdzielanie niekompletne (ostrzezenia: %d, brakujace wyniki: %d, uwagi kontroli: %d)"
                  % (len(krytyczne), len(brak_wynikow), len(weryf)))
        else:
            print("KONTROLA: %d z %d wynikow zapisanych i kompletnych" % (len(wyniki), len(wyniki)))
            wykonaj_sprzatanie(d, spis_nazwa, oryginaly, wyniki, tech, raport_nazwa, a.zachowaj_techniczne)
    return 0 if not problemy else 2


if __name__ == "__main__":
    sys.exit(main())

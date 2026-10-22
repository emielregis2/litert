#!/usr/bin/env python3
"""Rozdziela przetlumaczone pliki scalenia ("... pl.txt") na pliki oryginalne z koncowka " pl".

Wejscie (w katalogu):  NazwaKatalogu_spis_scalenia.txt  oraz  NazwaKatalogu_all_N pl.txt  (lub NazwaKatalogu_all pl.txt)
Wyjscie: "<oryginalna angielska nazwa> pl.txt" dla kazdego pliku ze spisu.
Granice wyznaczaja znaczniki  =====[[N|Nazwa]]=====  - liczy sie tylko numer N; nazwe w znaczniku DeepL mogl przetlumaczyc.
Dodatkowo sklada przetlumaczone czesci duzych plikow (Nazwa_1 pl.txt, Nazwa_2 pl.txt, ...) w jeden plik "Nazwa pl.txt"
na podstawie sekcji "Pliki podzielone" ze spisu.

Po KONTROLI kompletnosci (kazdy plik ze spisu ma zapisany, niepusty wynik "pl" bez znacznikow i bez podejrzanie malego
rozmiaru, brak ostrzezen) przenosi angielskie oryginaly do podkatalogu "org", a pliki techniczne KASUJE: pliki scalenia
(_all_N.txt) i ich tlumaczenia (_all_N pl.txt), czesci duzych plikow i ich tlumaczenia, spis oraz archiwa .zip (tylko gdy
zawieraja wylacznie tlumaczenia z tej partii). Raport naprawy zostaje w org. Wynik: w katalogu glownym tylko tlumaczenia,
w org tylko oryginaly. Flagi: --zachowaj-techniczne (pliki techniczne do org zamiast kasowania), --tylko-sprzatanie
(sama kontrola i sprzatanie dla katalogu rozdzielonego wczesniej, bez rozdzielania).
Pojedyncze znaki zastepcze U+FFFD w tlumaczeniu (uszkodzone przez DeepL) sa usuwane z wyniku automatycznie, z raportem
(do --max-fffd na plik; wiecej = ostrzezenie bez usuwania). Przetlumaczone pliki zrodlowe nie sa zmieniane.

Brakujace przetlumaczone pliki skrypt sam wypakowuje z archiwum .zip lezacego w katalogu (np. "DeepL Translations ... .zip"),
tylko te brakujace, bez nadpisywania; wylaczenie: --bez-zip.

Uzycie:  python rozdziel.py "C:\\sciezka\\KATALOG" [--nadpisz] [--bez-org] [--bez-zip] [--max-fffd 10]
                                                         [--zachowaj-techniczne] [--tylko-sprzatanie]
"""
import os, re, sys, argparse, shutil

MARK = re.compile(r"^[\s=\-_*#~]*\[\[\s*(\d+)\s*(?:\|[^\]\n]*)?\]\][\s=\-_*#~]*$")


try:  # nazwy plikow z polskimi znakami nie moga wywrocic wypisywania na konsole
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

KODOWANIE = {}   # sciezka -> uzyte kodowanie
PRZERWY = {}     # nazwa czesci -> liczba pustych linii miedzy ta czescia a poprzednia (ze spisu)
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
    podzielone, sekcja_podz = [], False
    for line in czytaj(path).split("\n"):
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


def oczekiwane_pliki(nazwy, pliki, podzielone):
    """Zwraca (oryginaly, wyniki, pliki techniczne) na podstawie spisu."""
    oryginaly = [nazwy[nr] for nr in sorted(nazwy)] + [o for o, _ in podzielone]
    wyniki = [o[:-4] + " pl.txt" for o in oryginaly]
    czesci = [c for _, cz in podzielone for c in cz]
    tech = list(pliki) + [pl[:-4] + " pl.txt" for pl in pliki] + czesci + [c[:-4] + " pl.txt" for c in czesci]
    return oryginaly, wyniki, tech


def zweryfikuj_wyniki(d, org, oryginaly, wyniki):
    """Kontrola, czy kazdy wynik jest zapisany i kompletny: istnieje, nie jest pusty, jest poprawnym UTF-8,
    nie ma znacznikow granic i nie jest podejrzanie maly wzgledem oryginalu (ucięte tlumaczenie)."""
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
                shutil.move(zrodlo, cel)
                if os.path.exists(cel) and os.path.getsize(cel) == rozm:
                    przen.append(o)
                else:
                    ostrz.append("BLAD przenoszenia oryginalu " + o)
    brak_org = [o for o in dict.fromkeys(oryginaly) if not os.path.exists(os.path.join(org, o))]
    rp, rc = os.path.join(d, raport_nazwa), os.path.join(org, raport_nazwa)
    if os.path.exists(rp) and not os.path.exists(rc):
        shutil.move(rp, rc)
        przen.append(raport_nazwa)
    print("ORG: przeniesiono %d plikow do %s (oryginaly%s)" % (len(przen), org, " i raport naprawy" if raport_nazwa in przen else ""))
    for w in ostrz:
        print("UWAGA: ORG:", w)
    if brak_org:
        print("UWAGA: SPRZATANIE: w org brakuje %d oryginalow (np. %s) - pliki techniczne zostaja, niczego nie kasuje" % (len(brak_org), brak_org[0]))
        return
    oczek_pl = {t.lower() for t in tech if t.endswith(" pl.txt")}
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
                    shutil.move(pth, os.path.join(org, n))
                    przeniesione_tech.append(n)
            else:
                os.remove(pth)
                if os.path.exists(pth):
                    print("UWAGA: SPRZATANIE: nie udalo sie usunac", pth)
                else:
                    usuniete.append((n, rozm))
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
                        shutil.move(zp, os.path.join(org, z))
                        przeniesione_tech.append(z)
                else:
                    os.remove(zp)
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
    a = ap.parse_args()
    d = os.path.normpath(a.katalog)
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
        weryf = [] if brak else zweryfikuj_wyniki(d, os.path.join(d, "org"), oryginaly, wyniki)
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
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(tekst)
        zapisane += 1
        print("OK (zlozono z %d czesci)" % len(pl_czesci), out_name, len(tekst.encode("utf-8")), "bajtow")
    print("Zapisano plikow:", zapisane, "(UTF-8 bez BOM, konce linii LF)")
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
        weryf = [] if brak_wynikow else zweryfikuj_wyniki(d, os.path.join(d, "org"), oryginaly, wyniki)
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

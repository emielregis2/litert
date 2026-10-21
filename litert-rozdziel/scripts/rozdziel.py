#!/usr/bin/env python3
"""Rozdziela przetlumaczone pliki scalenia ("... pl.txt") na pliki oryginalne z koncowka " pl".

Wejscie (w katalogu):  NazwaKatalogu_spis_scalenia.txt  oraz  NazwaKatalogu_all_N pl.txt  (lub NazwaKatalogu_all pl.txt)
Wyjscie: "<oryginalna angielska nazwa> pl.txt" dla kazdego pliku ze spisu.
Granice wyznaczaja znaczniki  =====[[N|Nazwa]]=====  - liczy sie tylko numer N; nazwe w znaczniku DeepL mogl przetlumaczyc.
Dodatkowo sklada przetlumaczone czesci duzych plikow (Nazwa_1 pl.txt, Nazwa_2 pl.txt, ...) w jeden plik "Nazwa pl.txt"
na podstawie sekcji "Pliki podzielone" ze spisu.

Gdy rozdzielanie jest KOMPLETNE (kazdy plik ze spisu ma swoj odpowiednik "pl", brak ostrzezen), przenosi do podkatalogu
"org" wszystko poza wynikami: angielskie oryginaly, pliki scalenia (_all_N.txt) i ich tlumaczenia (_all_N pl.txt),
czesci duzych plikow i ich tlumaczenia, spis oraz archiwa .zip z katalogu. Nic nie kasuje i nie nadpisuje.

Brakujace przetlumaczone pliki skrypt sam wypakowuje z archiwum .zip lezacego w katalogu (np. "DeepL Translations ... .zip"),
tylko te brakujace, bez nadpisywania; wylaczenie: --bez-zip.

Uzycie:  python rozdziel.py "C:\\sciezka\\KATALOG" [--nadpisz] [--bez-org] [--bez-zip]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("katalog")
    ap.add_argument("--nadpisz", action="store_true", help="nadpisz istniejace pliki wynikowe")
    ap.add_argument("--bez-org", action="store_true", help="nie przenos plikow zrodlowych do podkatalogu org")
    ap.add_argument("--bez-zip", action="store_true", help="nie uzupelniaj brakujacych tlumaczen z archiwow .zip w katalogu")
    a = ap.parse_args()
    d = os.path.normpath(a.katalog)
    spis_path = os.path.join(d, os.path.basename(d) + "_spis_scalenia.txt")
    if not os.path.exists(spis_path):
        print("BLAD: brak pliku spisu:", spis_path)
        if os.path.exists(os.path.join(d, "org", os.path.basename(spis_path))):
            print("      Spis jest w podkatalogu org - pliki zrodlowe zostaly juz przeniesione po poprzednim rozdzieleniu.")
        return 1
    pliki, nazwy, w_pliku, podzielone = parsuj_spis(spis_path)
    if not a.bez_zip:   # brakujace przetlumaczone pliki wypakuj z archiwum .zip z DeepL (jesli lezy w katalogu)
        oczek_pl = [pl[:-4] + " pl.txt" for pl in pliki] + [c[:-4] + " pl.txt" for _, cz in podzielone for c in cz]
        uzupelnij_z_zip(d, oczek_pl)
    problemy, zapisane = [], 0

    for plik in pliki:
        pl_name = plik[:-4] + " pl.txt"
        pl_path = os.path.join(d, pl_name)
        if not os.path.exists(pl_path):
            problemy.append("BRAK przetlumaczonego pliku: " + pl_name)
            continue
        czesci, cur, przed = {}, None, []
        tekst_pl = czytaj(pl_path)
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
            t = czytaj(os.path.join(d, c))
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

    # Porzadkowanie: gdy wszystko komplet, przenosimy materialy zrodlowe do ./org (nic nie kasujemy)
    if a.bez_org:
        print("ORG: pominieto (--bez-org)")
    else:
        krytyczne = [p for p in problemy if not p.startswith("POMINIETO")]
        wyniki = [nazwy[nr][:-4] + " pl.txt" for nr in sorted(nazwy)] + [o[:-4] + " pl.txt" for o, _ in podzielone]
        brak_wynikow = [w for w in wyniki if not os.path.exists(os.path.join(d, w))]
        if krytyczne or brak_wynikow or not wyniki:
            print("ORG: nie przenosze plikow - rozdzielanie niekompletne (ostrzezenia: %d, brakujace wyniki: %d)"
                  % (len(krytyczne), len(brak_wynikow)))
        else:
            do_przen = [nazwy[nr] for nr in sorted(nazwy)]                                   # angielskie oryginaly
            do_przen += list(pliki) + [pl[:-4] + " pl.txt" for pl in pliki]                  # scalenia i ich tlumaczenia
            for orig, czesci_n in podzielone:                                                # duze pliki: oryginal, czesci, tlumaczenia czesci
                do_przen += [orig] + list(czesci_n) + [c[:-4] + " pl.txt" for c in czesci_n]
            do_przen.append(os.path.basename(spis_path))                                     # spis
            wyniki_low = {w.lower() for w in wyniki}
            org = os.path.join(d, "org")
            os.makedirs(org, exist_ok=True)
            przen, istnieje = [], []
            for n in dict.fromkeys(do_przen):
                if n.lower() in wyniki_low:
                    continue                                                                  # wynikow nigdy nie przenosimy
                zrodlo, cel = os.path.join(d, n), os.path.join(org, n)
                if not os.path.exists(zrodlo):
                    continue
                if os.path.exists(cel):
                    istnieje.append(n)
                    continue
                shutil.move(zrodlo, cel)
                przen.append(n)
            # Archiwa .zip z katalogu (np. pobrane z DeepL) tez trafiaja do org - po udanym i kompletnym rozdzieleniu
            zipy = sorted(f for f in os.listdir(d) if f.lower().endswith(".zip") and os.path.isfile(os.path.join(d, f)))
            przen_zip = []
            for zf in zipy:
                cel = os.path.join(org, zf)
                if os.path.exists(cel):
                    istnieje.append(zf)
                    continue
                shutil.move(os.path.join(d, zf), cel)
                przen_zip.append(zf)
            print("ORG: przeniesiono %d plikow do %s%s" % (len(przen) + len(przen_zip), org,
                  " (w tym archiwa zip: %s)" % ", ".join(przen_zip) if przen_zip else ""))
            for n in istnieje:
                print("UWAGA: ORG: nie przeniesiono (taki plik juz jest w org):", n)
    return 0 if not problemy else 2


if __name__ == "__main__":
    sys.exit(main())

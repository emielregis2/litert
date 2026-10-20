#!/usr/bin/env python3
"""Rozdziela przetlumaczone pliki scalenia ("... pl.txt") na pliki oryginalne z koncowka " pl".

Wejscie (w katalogu):  NazwaKatalogu_spis_scalenia.txt  oraz  NazwaKatalogu_all_N pl.txt  (lub NazwaKatalogu_all pl.txt)
Wyjscie: "<oryginalna angielska nazwa> pl.txt" dla kazdego pliku ze spisu.
Granice wyznaczaja znaczniki  =====[[N|Nazwa]]=====  - liczy sie tylko numer N; nazwe w znaczniku DeepL mogl przetlumaczyc.
Dodatkowo sklada przetlumaczone czesci duzych plikow (Nazwa_1 pl.txt, Nazwa_2 pl.txt, ...) w jeden plik "Nazwa pl.txt"
na podstawie sekcji "Pliki podzielone" ze spisu.

Uzycie:  python rozdziel.py "C:\\sciezka\\KATALOG" [--nadpisz]
"""
import os, re, sys, argparse

MARK = re.compile(r"^[\s=\-_*#~]*\[\[\s*(\d+)\s*(?:\|[^\]\n]*)?\]\][\s=\-_*#~]*$")


def czytaj(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1250"):
        try:
            return raw.decode(enc).replace("\r\n", "\n")
        except UnicodeDecodeError:
            continue


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
            m = re.match(r"^(\s*)(.+?\.txt)\s*(?:\(\d+ bajtow\))?\s*$", line)
            if m and m.group(1) == "" and line.strip():
                podzielone.append((m.group(2), []))
            elif m and m.group(1) and podzielone:
                podzielone[-1][1].append(m.group(2))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("katalog")
    ap.add_argument("--nadpisz", action="store_true", help="nadpisz istniejace pliki wynikowe")
    a = ap.parse_args()
    d = os.path.normpath(a.katalog)
    spis_path = os.path.join(d, os.path.basename(d) + "_spis_scalenia.txt")
    if not os.path.exists(spis_path):
        print("BLAD: brak pliku spisu:", spis_path)
        return 1
    pliki, nazwy, w_pliku, podzielone = parsuj_spis(spis_path)
    problemy, zapisane = [], 0

    for plik in pliki:
        pl_name = plik[:-4] + " pl.txt"
        pl_path = os.path.join(d, pl_name)
        if not os.path.exists(pl_path):
            problemy.append("BRAK przetlumaczonego pliku: " + pl_name)
            continue
        czesci, cur, przed = {}, None, []
        for line in czytaj(pl_path).split("\n"):
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
            kawalki.append(t if t.endswith("\n") else t + "\n")
        tekst = "".join(kawalki)
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(tekst)
        zapisane += 1
        print("OK (zlozono z %d czesci)" % len(pl_czesci), out_name, len(tekst.encode("utf-8")), "bajtow")
    print("Zapisano plikow:", zapisane)
    for p in problemy:
        print("UWAGA:", p)
    return 0 if not problemy else 2


if __name__ == "__main__":
    sys.exit(main())

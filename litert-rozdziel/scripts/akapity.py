# -*- coding: utf-8 -*-
"""Laczenie twardo zawinietych linii w akapity (skill litert-rozdziel).

Niektore teksty zrodlowe maja linie zawiniete na ok. 60-90 znakow, a akapity sa oddzielone pustymi liniami. DeepL zachowuje ten uklad 1:1, wiec w gotowym
tlumaczeniu zdania sa porwane na krotkie linie (np. czytnik Speechify robi pauze na kazdym koncu linii). Ten modul sklada je z powrotem w akapity.

Wykrywanie (plik): blok = ciag niepustych linii. Blok jest 'zawiniety', gdy ma co najmniej 2 linie, zadna nie jest dluzsza niz WMAX znakow, co najmniej 2/3 linii
poza ostatnia ma co najmniej MIN_PELNA znakow i przynajmniej jedna z nich nie konczy sie znakiem konca zdania. Plik jest zawiniety, gdy takie bloki zawieraja
co najmniej PROG_PLIKU (30%) niepustych linii.
Laczenie: linie sa sklejane spacja (bez spacji przed , . ; : ! ? ) ” » i po lacznikach przed mala litera). Nie lacze: po linii konczacej sie znakiem konca
zdania, gdy nastepna zaczyna sie wypowiedzia (cudzyslow otwierajacy lub pauza dialogowa), dlugich linii (pelne akapity) oraz - w plikach bez pustych linii miedzy
akapitami - krotkich linii konczacych sie kropka (to koniec akapitu). Weryfikacja: tekst bez bialych znakow musi pozostac identyczny."""
import re

KON = ".!?\u2026\u201d\"\u00bb"                       # znaki konca zdania lub cytatu
OTW = "\u201e\u201c\"\u00ab\u2013\u2014"               # poczatek wypowiedzi: cudzyslow otwierajacy lub pauza dialogowa
PROG_PLIKU = 0.30                                      # minimalny udzial linii w blokach zawinietych
WMAX = 140                                             # dluzsza linia to pelny akapit, nie zawiniety wiersz (polskie linie sa ok. 10-15% dluzsze niz angielskie)
MIN_PELNA = 35                                         # 'pelna' (zawinieta) linia ma co najmniej tyle znakow
MAX_AKAPIT = 4000                                      # dluzszy akapit dzielimy na koncach zdan
MIN_CZESC = 1200                                       # ... co najmniej po tylu znakach
MIN_LINII = 30                                         # mniejszych plikow nie ruszamy


def _konczy(s):
    return bool(s) and s.rstrip()[-1:] in KON


def _bloki(linie):
    """Lista (poczatek, koniec_wylacznie) ciagow niepustych linii."""
    wyn, start = [], None
    for i, l in enumerate(linie):
        if l.strip():
            if start is None:
                start = i
        elif start is not None:
            wyn.append((start, i))
            start = None
    if start is not None:
        wyn.append((start, len(linie)))
    return wyn


def blok_zawiniety(blok):
    s = [x.strip() for x in blok]
    if len(s) < 2 or any(len(x) > WMAX for x in s):
        return False
    pierwsze = s[:-1]
    pelne = sum(1 for x in pierwsze if len(x) >= MIN_PELNA)
    male = sum(1 for x in s[1:] if x[:1].islower())          # kontynuacje zdan; wiersze (kazda linia wielka litera) nie sa zawinietym tekstem
    return pelne * 3 >= len(pierwsze) * 2 and any(not _konczy(x) for x in pierwsze) and male * 3 >= len(s[1:])


def wykryj(linie):
    """Zwraca (czy_plik_zawiniety, udzial_linii_w_blokach_zawinietych, liczba_blokow_zawinietych)."""
    nb = sum(1 for l in linie if l.strip())
    if nb < MIN_LINII:
        return False, 0.0, 0
    zaw = bl = 0
    for a, b in _bloki(linie):
        if blok_zawiniety(linie[a:b]):
            zaw += b - a
            bl += 1
    u = zaw / nb
    return u >= PROG_PLIKU, u, bl


def _skleic(a, b):
    a, b = a.rstrip(), b.lstrip()
    if b[:1] in ",.;:!?)\u201d\u00bb\u2026":
        return a + b
    if a.endswith("-") and not a.endswith("--") and a[-2:-1].isalpha() and b[:1].islower():
        return a + b                                     # zlozenie lub podzial wyrazu: laczymy bez spacji, lacznik zostaje
    return a + " " + b


def _laczyc(a, b, akap_pustymi, w95):
    a, b = a.strip(), b.strip()
    if len(a) > WMAX or len(b) > WMAX:
        return False
    if _konczy(a) and b[:1] in OTW:
        return False                                     # poczatek wypowiedzi (zmiana mowcy)
    if akap_pustymi or not _konczy(a):
        return True
    return len(a) >= 0.85 * w95                          # w plikach bez pustych linii krotka linia z kropka konczy akapit


def _podziel_dlugi(par):
    if len(par) <= MAX_AKAPIT:
        return [par]
    czesci, start = [], 0
    for m in re.finditer(r"[.!?\u2026\u201d] ", par):
        if m.end() - start >= MIN_CZESC and len(par) - m.end() >= 200:
            czesci.append(par[start:m.end()].rstrip())
            start = m.end()
    czesci.append(par[start:])
    return czesci


def rozwin(linie):
    """Laczy linie wewnatrz blokow. Zwraca (nowe_linie, liczba_polaczen). Nie dotyka pustych linii."""
    nb = [l.strip() for l in linie if l.strip()]
    if not nb:
        return list(linie), 0
    dl = sorted(min(len(x), WMAX) for x in nb)
    w95 = dl[min(len(dl) - 1, int(0.95 * len(dl)))]
    akap_pustymi = (len(linie) - len(nb)) / max(1, len(linie)) >= 0.15
    wyj, poz, pol = [], 0, 0
    for a, b in _bloki(linie):
        wyj.extend(linie[poz:a])                          # puste linie przed blokiem
        akap, ost = [linie[a]], linie[a]                  # ost = poprzednia ORYGINALNA linia (limit dlugosci dotyczy linii, nie narastajacego akapitu)
        for l in linie[a + 1:b]:
            if _laczyc(ost, l, akap_pustymi, w95):
                akap[-1] = _skleic(akap[-1], l)
                pol += 1
            else:
                akap.append(l)
            ost = l
        for p in akap:
            wyj.extend(_podziel_dlugi(p.rstrip()))
        poz = b
    wyj.extend(linie[poz:])
    return wyj, pol


def rozwin_tekst(tekst, wymus=False):
    """Zwraca (nowy_tekst, info). info: czy, udzial, bloki, przed, po, polaczen, blad. Tekst niezmieniony, gdy plik nie jest zawiniety (chyba ze wymus)."""
    crlf = "\r\n" in tekst
    linie = tekst.replace("\r\n", "\n").split("\n")
    czy, udzial, bl = wykryj(linie)
    przed = sum(1 for l in linie if l.strip())
    info = dict(czy=czy, udzial=udzial, bloki=bl, przed=przed, po=przed, polaczen=0, blad="")
    if not (czy or wymus):
        return tekst, info
    nowe, pol = rozwin(linie)
    nowy = "\n".join(nowe)
    if re.sub(r"\s+", "", nowy) != re.sub(r"\s+", "", "\n".join(linie)):
        info["blad"] = "tresc po polaczeniu rozni sie od oryginalu (poza bialymi znakami) - nie zmieniam pliku"
        return tekst, info
    info["po"] = sum(1 for l in nowe if l.strip())
    info["polaczen"] = pol
    return (nowy.replace("\n", "\r\n") if crlf else nowy), info

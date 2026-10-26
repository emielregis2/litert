# -*- coding: utf-8 -*-
"""Ponowne tlumaczenie bardzo dlugich linii w ISTNIEJACYCH tlumaczeniach (skill litert-rozdziel).

DeepL traci jakosc na bardzo dlugich liniach ('czkawka': podwojone slowa, zaimki 'On/Ja', rozsypane 'sie'). Ten skrypt naprawia
juz gotowe tlumaczenia: dlugie linie oryginalu (> --prog znakow, domyslnie 4000) tnie na kawalki na granicach zdan, zbiera je w jeden plik
pomocniczy w KATALOGU (DO_PRZETLUMACZENIA_<Katalog>.txt, kawalki oddzielone pustymi liniami), a po przetlumaczeniu go w DeepL
(zapisz jako 'DO_PRZETLUMACZENIA_<Katalog> pl.txt') sklada kawalki w pojedyncze linie i podmienia nimi odpowiednie linie wynikow.

Uzycie:
  python dlugie_linie.py KATALOG --przygotuj [--pliki "Nazwa A;Nazwa B"] [--prog 4000]
  python dlugie_linie.py KATALOG --zastosuj  [--pliki "..."] [--prog 4000] [--sucho]
--pliki: nazwy oryginalow bez .txt, rozdzielone srednikiem (domyslnie wszystkie z linia dluzsza niz --prog). Oryginaly sa brane z podkatalogu
org (albo z katalogu). Wynik musi miec taka sama liczbe linii z trescia jak oryginal (inaczej plik jest pomijany z komunikatem).
--zastosuj: kontrole przed zapisem (liczba linii tlumaczenia = liczba kawalkow, proporcje dlugosci linii i kazdego kawalka, brak U+FFFD i petli), zapis wszystko
albo nic, stosuje tez slownik poprawek DeepL, a na koniec przenosi pliki pomocnicze do Kosza."""
import os, re, sys, argparse, importlib.util


def zaladuj_rozdziel():
    spec = importlib.util.spec_from_file_location("rozdziel_mod", os.path.join(os.path.dirname(os.path.abspath(__file__)), "rozdziel.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dziel_dluga_linie(linia, prog=4000, cel=3000, min_kawalek=1200, min_tura=1500):
    """Identyczna z funkcja w litert/scripts/scal.py (podzial najpierw na granicach zmiany mowcy, potem zdan; polaczenie spacja odtwarza linie co do znaku)."""
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


def dziel_na_turach(linia, prog=4000, min_odc=0, prog_tur=None):
    """Dzieli linie dluzsza niz 'prog' w KAZDEJ zmianie mowcy: MIEDZY dwoma sasiednimi cudzyslowami ('""' albo typograficzne '”“' - linia konczy sie
    cudzyslowem, nastepna zaczyna sie cudzyslowem, nic nie jest usuwane) oraz w srodkowej spacji '" "' / '” “' (spacja jest usuwana). Zwraca
    (kawalki, odstepy): odstepy to napis dlugosci len(kawalki)-1, 'q' = ciecie miedzy cudzyslowami (laczenie bez niczego), 's' = ciecie na spacji
    (laczenie spacja); laczenie wg odstepow odtwarza linie co do znaku. Odcinek musi miec co najmniej 'min_odc' znakow i co najmniej 2 litery/cyfry
    (nie robimy linii z samego cudzyslowu). Odcinki nadal dluzsze niz 'prog' (brak granic zmiany mowcy) sa dzielone po zdaniach (dziel_dluga_linie).
    'prog_tur' (domyslnie = 'prog') to dlugosc linii, powyzej ktorej w ogole tniemy na zmianach mowcy (0 = tniemy kazda linie)."""
    if len(linia) <= (prog if prog_tur is None else prog_tur):
        return [linia], ""
    n = len(linia)
    kand = []                                        # (miejsce ciecia, poczatek nastepnego odcinka, rodzaj)
    for p in range(1, n - 1):
        c, d = linia[p], linia[p + 1]
        if c == '"' and d == '"' and linia[p - 1] != '"' and (p + 2 >= n or linia[p + 2] != '"'):
            kand.append((p + 1, p + 1, "q"))
        elif c == "\u201d" and d == "\u201c":
            kand.append((p + 1, p + 1, "q"))
        elif c == " " and p + 1 < n and ((linia[p - 1] == '"' and d == '"') or (linia[p - 1] == "\u201d" and d == "\u201c")):
            kand.append((p, p + 1, "s"))
    pref = [0]                                       # sumy prefiksowe liczby liter/cyfr (liniowo zamiast liczenia dla kazdego kandydata)
    for ch in linia:
        pref.append(pref[-1] + (1 if ch.isalnum() else 0))
    odcinki, odst, start = [], [], 0
    for cut, nxt, r in kand:
        if cut - start >= max(min_odc, 1) and n - nxt >= max(min_odc, 1) and pref[cut] - pref[start] >= 2 and pref[n] - pref[nxt] >= 2:
            odcinki.append(linia[start:cut])
            odst.append(r)
            start = nxt
    odcinki.append(linia[start:])
    wynik, sep = [], []
    for i, o in enumerate(odcinki):
        czesci = dziel_dluga_linie(o, prog) if len(o) > prog else [o]
        wynik.extend(czesci)
        sep.extend(["s"] * (len(czesci) - 1))
        if i < len(odst):
            sep.append(odst[i])
    return wynik, "".join(sep)


def tnij_po_kropce(tekst, dl=1000, okno=1000, min_ogon=150, twardy=False):
    """Tnie 'tekst' na kawalki. Tryb domyslny: po osiagnieciu 'dl' znakow szuka NAJBLIZSZEJ kropki konczacej zdanie (kropka, ewentualnie zamykajacy
    cudzyslow/nawias, pojedyncza spacja i poczatek nastepnego zdania; nie tniemy na wielokropku) i tnie w tej spacji; gdy w nastepnych 'okno' znakach
    nie ma kropki, uzywa '!' lub '?', a w ostatecznosci dowolnej pojedynczej spacji. Tryb 'twardy': zaden kawalek nie ma wiecej niz 'dl' znakow -
    tniemy na OSTATNIEJ kropce przed limitem (gdy brak: '!' '?', potem ',;:', na koncu ostatnia spacja przed limitem). Spacja w miejscu ciecia jest
    usuwana; polaczenie kawalkow pojedyncza spacja odtwarza tekst co do znaku. Ogon krotszy niz 'min_ogon' znakow zostaje przy ostatnim kawalku
    (w trybie twardym dbamy o to, o ile limit na to pozwala)."""
    n = len(tekst)
    if dl <= 0 or n <= dl:
        return [tekst]

    def zdanie(i, znaki):
        if i < 2 or i + 1 >= n or tekst[i] != " " or tekst[i - 1] == " " or tekst[i + 1] == " " or tekst[i + 1] == ".":
            return False
        p = tekst[i - 1]
        return p in znaki or (p in "\"'\u201d\u2019)" and tekst[i - 2] in znaki)
    kawalki, start = [], 0
    while n - start > dl:
        b = None
        if twardy:
            gorna = start + dl
            dolna = start + max(100, dl // 4)
            for hi in (min(gorna, n - 1 - min_ogon), gorna):
                for znaki in (".", "!?", ",;:"):
                    for i in range(hi, dolna, -1):
                        if zdanie(i, znaki):
                            b = i
                            break
                    if b is not None:
                        break
                if b is not None:
                    break
            if b is None:
                for i in range(gorna, start + 1, -1):
                    if i + 1 < n and tekst[i] == " " and tekst[i - 1] != " " and tekst[i + 1] != " ":
                        b = i
                        break
        else:
            koniec = min(n - 1, start + dl + okno)
            for znaki in (".", "!?"):
                for i in range(start + dl, koniec):
                    if zdanie(i, znaki) and n - (i + 1) >= min_ogon:
                        b = i
                        break
                if b is not None:
                    break
            if b is None:
                for i in range(start + dl, koniec):
                    if tekst[i] == " " and tekst[i - 1] != " " and tekst[i + 1] != " " and n - (i + 1) >= min_ogon:
                        b = i
                        break
        if b is None:
            break
        kawalki.append(tekst[start:b])
        start = b + 1
    kawalki.append(tekst[start:])
    return kawalki


def rozbij_po_kropce(ch, sp, dl, twardy=False):
    """Stosuje tnij_po_kropce do kazdego kawalka z listy 'ch' (z odstepami 'sp': 's' = spacja, 'q' = bez niczego) i zwraca (kawalki, odstepy)."""
    nowe, nsp = [], []
    for i, p in enumerate(ch):
        czesci = tnij_po_kropce(p, dl, twardy=twardy)
        nowe.extend(czesci)
        nsp.extend(["s"] * (len(czesci) - 1))
        if i < len(ch) - 1:
            nsp.append(sp[i])
    return nowe, "".join(nsp)


def skroc(l):
    return re.sub(r"([^\W\d_]|[!?.])\1{4,}", lambda m: m.group(1) * 4, l)


def czytaj_linie(p):
    raw = open(p, "rb").read()
    try:
        t = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        t = raw.decode("cp1252", errors="replace")
    return t.replace("\r\n", "\n").strip("\n").split("\n")


def zbierz_plan(d, prog, nazwy, tury=False, min_odc=0, ciecie=0, limit=0):
    """Zwraca (lista plikow do naprawy: dict z kluczami baza, Lo, dlugie [(j, kawalki)], idx_wyniku {j: indeks linii wyniku}), lista pominietych)."""
    zrodlo = os.path.join(d, "org") if os.path.isdir(os.path.join(d, "org")) else d
    pliki, pominiete = [], []
    for f in sorted(os.listdir(zrodlo), key=str.lower):
        if not f.lower().endswith(".txt") or f.lower().endswith(" pl.txt") or re.search(r"_all|_spis|_raport|^DO_PRZETLUMACZENIA", f, re.I):
            continue
        baza = f[:-4]
        if nazwy and baza.lower() not in nazwy:
            continue
        wp = os.path.join(d, baza + " pl.txt")
        if not os.path.isfile(wp):
            continue
        Lo = czytaj_linie(os.path.join(zrodlo, f))
        dlugie = []
        for j, l in enumerate(Lo):
            if len(l) > prog:
                if tury:
                    kaw, sp = dziel_na_turach(skroc(l), prog, min_odc)
                else:
                    kaw = dziel_dluga_linie(skroc(l), prog)
                    sp = "s" * (len(kaw) - 1)
                if limit:
                    kaw, sp = rozbij_po_kropce(kaw, sp, limit, True)
                elif ciecie:
                    kaw, sp = rozbij_po_kropce(kaw, sp, ciecie)
                dlugie.append((j, kaw, sp))
        if not dlugie:
            continue
        R = open(wp, "rb").read().decode("utf-8").split("\n")
        nb_o = [i for i, x in enumerate(Lo) if x.strip()]
        nb_r = [i for i, x in enumerate(R) if x.strip()]
        if len(nb_o) != len(nb_r):
            pominiete.append((baza, "rozna liczba linii z trescia: oryginal %d, wynik %d" % (len(nb_o), len(nb_r))))
            continue
        pozycja = {j: k for k, j in enumerate(nb_o)}
        pliki.append({"baza": baza, "Lo": Lo, "dlugie": dlugie, "idx": {j: nb_r[pozycja[j]] for j, _, _ in dlugie}, "wynik": wp})
    return pliki, pominiete


def podwojone(t):
    return len(re.findall(r"(?<![^\W\d_])([^\W\d_]{3,})\s\1(?![^\W\d_])", t, re.I)), max(1, len(t.split()))


def main():
    ap = argparse.ArgumentParser(description="Ponowne tlumaczenie dlugich linii w istniejacych tlumaczeniach")
    ap.add_argument("katalog")
    ap.add_argument("--przygotuj", action="store_true")
    ap.add_argument("--zastosuj", action="store_true")
    ap.add_argument("--pliki", default="", help="nazwy oryginalow bez .txt rozdzielone srednikiem (domyslnie wszystkie z dluga linia)")
    ap.add_argument("--prog", type=int, default=4000)
    ap.add_argument("--dziel-tury", action="store_true", help="tnij w KAZDYM miejscu zmiany mowcy (jak w scal.py --dziel-tury); przy --zastosuj uzyj tych samych flag co przy --przygotuj")
    ap.add_argument("--min-odcinek", type=int, default=0, help="z --dziel-tury: minimalna dlugosc odcinka w znakach (domyslnie 0 = ciecie w kazdej granicy)")
    ap.add_argument("--ciecie-po", type=int, default=0, help="po osiagnieciu tylu znakow tnij na najblizszej kropce (jak w scal.py --ciecie-po); przy --zastosuj uzyj tych samych flag co przy --przygotuj")
    ap.add_argument("--limit-linii", type=int, default=0, help="twardy limit dlugosci kawalka w znakach (jak w scal.py --limit-linii); przy --zastosuj uzyj tych samych flag co przy --przygotuj")
    ap.add_argument("--sucho", action="store_true", help="z --zastosuj: tylko sprawdz, nic nie zapisuj")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    d = os.path.normpath(a.katalog)
    if not os.path.isdir(d) or not (a.przygotuj or a.zastosuj):
        print("Uzycie: dlugie_linie.py KATALOG --przygotuj | --zastosuj [--pliki \"A;B\"] [--prog 4000] [--sucho]")
        return 1
    nazwy = {x.strip().lower() for x in a.pliki.split(";") if x.strip()}
    pliki, pominiete = zbierz_plan(d, a.prog, nazwy, a.dziel_tury, a.min_odcinek, a.ciecie_po, a.limit_linii)
    for b, powod in pominiete:
        print("POMINIETO %s: %s" % (b, powod))
    for nz in sorted(nazwy - {p["baza"].lower() for p in pliki} - {b.lower() for b, _ in pominiete}):
        print("UWAGA: nie znaleziono pliku do naprawy (brak dlugiej linii, oryginalu albo wyniku): " + nz)
    if not pliki:
        print("Brak plikow do naprawy.")
        return 0
    wszystkie = [k for p in pliki for _, kaw, _s in p["dlugie"] for k in kaw]
    pom = os.path.join(d, "DO_PRZETLUMACZENIA_" + os.path.basename(d) + ".txt")
    print("plikow do naprawy: %d | dlugich linii: %d | kawalkow do przetlumaczenia: %d | znakow: %d" % (
        len(pliki), sum(len(p["dlugie"]) for p in pliki), len(wszystkie), sum(len(k) for k in wszystkie)))
    for p in pliki:
        print("  %-60s linie %s | dlugosci %s | kawalkow %d" % (p["baza"][:60], [j + 1 for j, _, _s in p["dlugie"]], [len(p["Lo"][j]) for j, _, _s in p["dlugie"]], sum(len(k) for _, k, _s in p["dlugie"])))
    if a.przygotuj:
        with open(pom, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n\n".join(wszystkie) + "\n")
        print("\nZAPISANO plik pomocniczy: %s (%d B, %d kawalkow)" % (pom, os.path.getsize(pom), len(wszystkie)))
        print("Przetlumacz go w DeepL i zapisz jako: DO_PRZETLUMACZENIA_%s pl.txt (w tym samym katalogu), potem uruchom z --zastosuj." % os.path.basename(d))
        return 0
    tr = next((x for x in (os.path.join(d, "DO_PRZETLUMACZENIA_" + os.path.basename(d) + " pl.txt"), os.path.join(d, "DO_PRZETLUMACZENIA_" + os.path.basename(d) + " pl (1).txt")) if os.path.isfile(x)), None)
    if not tr:
        print("BLAD: brak pliku z tlumaczeniem (DO_PRZETLUMACZENIA_%s pl.txt)" % os.path.basename(d))
        return 1
    tekst_tr = open(tr, "rb").read().decode("utf-8-sig").replace("\r\n", "\n")
    T = [x.strip() for x in tekst_tr.split("\n") if x.strip()]
    print("\nlinii w tlumaczeniu: %d (oczekiwane %d)" % (len(T), len(wszystkie)))
    rz = zaladuj_rozdziel()
    if len(T) != len(wszystkie):
        if len(T) < len(wszystkie):
            idx = rz._pominiete_akapity([len(x) for x in wszystkie], [len(x) for x in T])
            print("BLAD: DeepL pominal lub scalil kawalki; prawdopodobnie brakuje kawalkow o numerach (od 1): %s" % ([i + 1 for i in idx] if idx else "nie udalo sie ustalic"))
        else:
            print("BLAD: w tlumaczeniu jest wiecej linii niz kawalkow")
        return 1
    if "\ufffd" in tekst_tr or re.search(r"([^\s])\1{19,}", tekst_tr):
        print("BLAD: w tlumaczeniu sa znaki U+FFFD albo ciagi 20+ tego samego znaku")
        return 1
    reguly = rz.wczytaj_poprawki()
    zmiany, i, zle, lacznie_zam = {}, 0, [], rz.collections.Counter()
    for p in pliki:
        nowe = {}
        for j, kaw, sp in p["dlugie"]:
            tl = T[i:i + len(kaw)]
            i += len(kaw)
            r = sum(len(x) for x in tl) / max(1, sum(len(x) for x in kaw))
            if not 0.7 <= r <= 1.7:
                zle.append("%s linia %d: stosunek dlugosci %.2f" % (p["baza"][:40], j + 1, r))
            for n_k, (k_o, k_t) in enumerate(zip(kaw, tl), 1):          # kontrola kazdego kawalka z osobna (ucięty kawalek nie moze zginac w sumie)
                rk = len(k_t) / max(1, len(k_o))
                if len(k_o) >= 300 and not 0.7 <= rk <= 1.7:
                    zle.append("%s linia %d, kawalek %d z %d: stosunek dlugosci %.2f" % (p["baza"][:40], j + 1, n_k, len(kaw), rk))
            linia, zam = rz.zastosuj_poprawki(rz._sklej_kawalki(tl, sp), reguly)
            lacznie_zam.update(zam)
            nowe[p["idx"][j]] = linia
        zmiany[p["wynik"]] = nowe
    if zle:
        print("BLAD: podejrzane proporcje dlugosci (tlumaczenie ucięte lub rozdete):")
        for x in zle:
            print("   " + x)
        return 1
    print("kontrole przed zapisem: OK (liczba linii, proporcje dlugosci linii i kazdego kawalka 0,7-1,7, brak U+FFFD i petli)")
    print("\n%-60s %s" % ("plik", "podwojone slowa na 10 tys. slow: przed -> po"))
    nowe_teksty = {}
    for wp, nowe in zmiany.items():
        t = open(wp, "rb").read().decode("utf-8")
        R = t.split("\n")
        for k, linia in nowe.items():
            lead = R[k][:len(R[k]) - len(R[k].lstrip())]
            R[k] = lead + linia
        nt = "\n".join(R)
        if nt.count("\n") != t.count("\n"):
            print("BLAD: zmiana liczby linii w", wp)
            return 1
        pr, sl = podwojone(t)
        po, sl2 = podwojone(nt)
        print("%-60s %6.0f -> %6.0f" % (os.path.basename(wp)[:60], 1e4 * pr / sl, 1e4 * po / sl2))
        nowe_teksty[wp] = nt
    if a.sucho:
        print("\n(--sucho: nic nie zapisano)")
        return 0
    for wp, nt in nowe_teksty.items():
        with open(wp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(nt)
    print("\nZAPISANO: podmieniono %d dlugich linii w %d plikach; zamian ze slownika poprawek: %d" % (sum(len(v) for v in zmiany.values()), len(zmiany), sum(lacznie_zam.values())))
    usuniete = []
    for f in sorted(os.listdir(d)):
        if re.match(r"^DO_PRZETLUMACZENIA_.*\.txt$", f):
            pf = os.path.join(d, f)
            if rz._do_kosza(pf) or rz._usun(pf):
                usuniete.append(f)
    print("pliki pomocnicze przeniesione do Kosza: %s" % usuniete)
    return 0


if __name__ == "__main__":
    sys.exit(main())

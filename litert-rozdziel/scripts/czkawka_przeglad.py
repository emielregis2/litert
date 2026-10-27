# -*- coding: utf-8 -*-
"""Przeglad 'czkawki' DeepL w tlumaczeniach (skill litert-rozdziel): PODWOJONE SLOWA i bledy na WIELKICH LITERACH, z kontekstem angielskiego oryginalu.

Podwojone slowo ('sie sie', 'jej jej', 'tuz tuz') bywa czkawka DeepL, ale bywa tez poprawne: powtorzenie jest w oryginale ('yeah, yeah', 'ding ding'),
polski idiom ('tuz tuz'), zaimek plus przeczenie ('na nie nie spojrzalem'), nazwa wlasna ('Duran Duran'). Dlatego kazde podwojenie jest klasyfikowane po
oryginale: tylko gdy oryginal NIE ma powtorzenia, a slowo nalezy do krotkiej listy SAFE (sie, tak, ze, do, jak), jest bezpieczna autopoprawka (i, w, na, z: 'i i tak', 'w w pelni', 'na na wpol' sa poprawne);
reszta podejrzanych trafia do przegladu. Druga kontrola: linie oryginalu pisane WIELKIMI LITERAMI, w ktorych tlumaczenie jest nieproporcjonalnie dlugie/krotkie
albo ma powtorzenia (np. 'KISS' -> 'POCZUWALNY' x13, 'HANDSOME' -> 'PRZYKLADOWY PRZYKLADOWY').
Linie tlumaczenia sa wyrownywane do linii oryginalu: gdy liczba niepustych linii jest rowna - 1:1, inaczej (po ciecia tur) wyrownanie po dlugosciach (Gale-Church).

Uzycie:
  python czkawka_przeglad.py KATALOG [KATALOG ...] [--korzen KATALOG_GLOWNY] [--csv plik.csv] [--md plik.md] [--napraw [--kopia plik.zip]]
Oryginaly sa brane z podkatalogu org (albo z katalogu). Bez --napraw skrypt tylko czyta."""
import os, re, sys, csv, argparse, collections

SAFE = ("się", "tak", "że", "do", "jak")          # tylko slowa, ktorych podwojenie praktycznie nigdy nie jest poprawne (i, w, na, z: 'i i tak', 'w w pelni', 'na na wpol' sa poprawne)
ZAIMKI = {"jej", "jego", "ich", "mi", "ci", "mu", "im", "go", "ją", "je", "nas", "was", "mnie", "cię", "tobie", "sobie", "tu", "tam"}
PRZYIMKI = {"na", "o", "w", "do", "dla", "za", "przed", "nad", "pod", "przez", "po", "od", "z", "ze", "u", "przy", "bez", "wobec", "ku", "wśród", "między", "mimo"}
LEGIT_NASTEPNE = {("i", "tak"), ("i", "to"), ("w", "pełni"), ("na", "wpół")}      # poprawne konstrukcje: 'i i tak', 'w w pelni', 'na na wpol'
KONTEKST_RAZEM = {"tym", "innym", "jednym", "następnym", "każdym", "pierwszym", "kolejnym", "tamtym", "razem"}   # 'tym razem razem'
KROTKIE = {"i", "w", "na", "z", "a", "o", "u"}          # krotkie slowa funkcyjne: tez do przegladu (z pominieciem poprawnych konstrukcji), ale nigdy autopoprawka
RUN = re.compile(r"(?<![^\W\d_])([^\W\d_]+)((?:\s+\1)+)(?![^\W\d_])", re.I)
K_ZRODLO, K_NAZWA, K_IDIOM, K_ZAIMEK = "uzasadnione: powtorzenie w oryginale", "nazwa podwojona BEZ powtorzenia w oryginale (sprawdz)", "idiom (tuz tuz)", "zaimek (mozliwa poprawna gramatyka)"
K_AUTO, K_PRZEGLAD, K_CAPS, K_PETLA = "CZKAWKA (autopoprawka)", "CZKAWKA? (do przegladu)", "WIELKIE LITERY: podejrzane tlumaczenie", "PETLA slowa (3+ powtorzen)"
K_PL_SAFE, K_PL_PRZEGLAD = "podejrzane BEZ oryginalu (krotkie slowo)", "do przegladu BEZ oryginalu"
ZLE = (K_AUTO, K_PRZEGLAD, K_CAPS, K_PETLA, K_NAZWA, K_PL_SAFE, K_PL_PRZEGLAD)


def dec(raw):
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def zr_powtorzenia(tekst):
    t = [re.sub(r"['’]s?$", "", w.lower()) for w in re.findall(r"[A-Za-z'’]+", tekst)]          # Joe Joe's -> joe joe
    return sorted({a for a, b in zip(t, t[1:]) if a == b and len(a) >= 2})


def wyrownaj(src, tr, K=12, B=200):
    """src, tr: listy dlugosci niepustych linii; zwraca mp[j] = indeks linii zrodla dla kawalka tlumaczenia j (po dlugosciach, monotonicznie)."""
    N, M = len(src), len(tr)
    if N == 0 or M < N:
        return None
    r = sum(tr) / max(1, sum(src)); INF = 1e18; pref = [0]
    for x in tr:
        pref.append(pref[-1] + x)
    prev = {0: 0.0}; back = []
    for i in range(1, N + 1):
        centre = int(i * M / N); cur = {}; bk = {}; exp = r * src[i - 1]
        for j in range(max(i, centre - B), min(M, centre + B) + 1):
            best = INF; bk_k = 0
            for k in range(1, K + 1):
                pj = j - k
                if pj in prev:
                    L = pref[j] - pref[pj]; c = prev[pj] + (L - exp) ** 2 / (exp + 20.0) + 0.5 * (k - 1)
                    if c < best:
                        best, bk_k = c, k
            if bk_k:
                cur[j] = best; bk[j] = bk_k
        prev = cur; back.append(bk)
    if M not in prev:
        return None
    j = M; mp = [0] * M
    for i in range(N, 0, -1):
        k = back[i - 1][j]
        for q in range(j - k, j):
            mp[q] = i - 1
        j -= k
    return mp


def mapuj(src_nb, tr_nb):
    """Zwraca (mapowanie, dokladne): dokladne=True, gdy liczby niepustych linii sa rowne (uklad 1:1)."""
    if len(src_nb) == len(tr_nb):
        return list(range(len(tr_nb))), True
    return wyrownaj([len(l) for _, l in src_nb], [len(l) for _, l in tr_nb]), False


def wstepna(m, l):
    """Ocena samego slowa i kontekstu (bez oryginalu). Zwraca None, gdy to poprawna konstrukcja (pomijamy), albo klase."""
    toks = re.findall(r"[^\W\d_]+", m.group(0)); tok = toks[0]; low = tok.lower()
    if m.start() > 0 and l[m.start() - 1] in "'\u2019":
        return None                                           # "Jerome'a a": koncowka odmiany po apostrofie, nie podwojenie
    pre = l[:m.start()].rstrip(); poczatek = (not pre) or pre[-1] in ".!?…:;„”\"–—-"
    nm = re.match(r"\s+([^\W\d_]+)", l[m.end():]); nxt = nm.group(1).lower() if nm else ""
    pm = re.search(r"([^\W\d_]+)\W*$", pre); prv = pm.group(1).lower() if pm else ""
    if len(tok) == 1 and any(t != tok for t in toks[1:]):
        return None                                           # 'E&I i': akronim, nie podwojenie
    if tok[0].isupper() and not tok.isupper() and any(t[0].islower() for t in toks[1:]) and not poczatek:
        return None                                           # 'Sam sam chcial': imie + slowo
    if (low, nxt) in LEGIT_NASTEPNE or (low == "razem" and prv in KONTEKST_RAZEM):
        return None
    if tok[0].isupper() and all(t[0].isupper() for t in toks) and not tok.isupper():
        return K_NAZWA
    if low == "tuż":
        return K_IDIOM
    if low == "nie":
        return K_ZAIMEK if prv in PRZYIMKI else K_PRZEGLAD    # 'na nie nie patrzy' (zaimek) vs 'nie nie zgadzalem' (czkawka)
    if low in ZAIMKI:
        return K_ZAIMEK
    if low in SAFE:
        return K_AUTO
    return K_PRZEGLAD


def przegladaj(tr_lines, src_lines):
    """tr_lines, src_lines: listy WSZYSTKICH linii. Zwraca (znaleziska, mapowanie_ok). Znalezisko: dict(linia, klasa, slowo, pl, en, start, koniec, idx, tok).
    Przy ukladzie 1:1 oryginal sprawdzam tylko w okolicy tego samego miejsca linii, przy wyrownaniu po cieciu: w liniach i-1..i+1."""
    tr_nb = [(i, l) for i, l in enumerate(tr_lines) if l.strip()]; src_nb = [(i, l) for i, l in enumerate(src_lines) if l.strip()]
    mp, dokl = mapuj(src_nb, tr_nb)
    if mp is None:
        return [], False
    wyn = []; grupy = collections.defaultdict(list)
    for j, i in enumerate(mp):
        grupy[i].append(j)
    for j, (n, l) in enumerate(tr_nb):
        i = mp[j]; sl = src_nb[i][1]; g = grupy[i]
        for m in RUN.finditer(l):
            tok = m.group(1); pow_ = 1 + len(re.findall(r"\s+", m.group(2)))
            if len(tok) < 3 and tok.lower() not in SAFE and tok.lower() not in KROTKIE:
                continue
            przed = sum(len(tr_nb[q][1]) for q in g if q < j) + m.start(); poz = int(len(sl) * przed / max(1, sum(len(tr_nb[q][1]) for q in g)))
            if dokl:
                pol = max(250, int(0.15 * len(sl))); okol = sl[max(0, poz - pol):poz + pol]
            else:
                okol = " ".join(src_nb[q][1] for q in range(max(0, i - 1), min(len(src_nb), i + 2)))
            pre = wstepna(m, l)
            if pre is None:
                continue
            if zr_powtorzenia(okol):
                kl = K_ZRODLO                                  # powtorzenie jest w oryginale (takze onomatopeje: 'Doh doh doh')
            else:
                kl = K_PETLA if pow_ >= 3 else pre
            wyn.append(dict(linia=n + 1, klasa=kl, slowo=m.group(0)[:60], pl=l[max(0, m.start() - 70):m.end() + 70], en=sl[max(0, poz - 110):poz + 110].replace("\n", " "), start=m.start(), koniec=m.end(), idx=n, tok=tok, dokl=dokl))
    for i, (sn_, s) in enumerate(src_nb):
        lit = [c for c in s if c.isalpha()]
        if len(lit) < 8 or sum(1 for c in lit if c.isupper()) / len(lit) < 0.8:
            continue
        g = grupy.get(i, [])
        if not g:
            continue
        t = " ".join(tr_nb[q][1] for q in g); ratio = len(t) / max(1, len(s))
        seria = re.search(r"(.)\1{7,}", t)
        if (len(s) >= 20 and (ratio > 2.5 or ratio < 0.35)) or (seria and not re.search(re.escape(seria.group(1)) + "{8,}", s)):
            wyn.append(dict(linia=tr_nb[g[0]][0] + 1, klasa=K_CAPS, slowo="stosunek %.2f%s" % (ratio, (", seria '%s' x%d" % (seria.group(1), len(seria.group(0)))) if seria else ""), pl=t[:140], en=s[:140], start=0, koniec=0, idx=tr_nb[g[0]][0], tok="", dokl=dokl))
    return wyn, True


def przegladaj_pl(tr_lines):
    """Tryb BEZ oryginalu (starsze katalogi bez org): tylko klasyfikacja po slowie, bez autopoprawki."""
    wyn = []
    for n, l in enumerate(tr_lines):
        for m in RUN.finditer(l):
            tok = m.group(1); pow_ = 1 + len(re.findall(r"\s+", m.group(2)))
            if len(tok) < 3 and tok.lower() not in SAFE and tok.lower() not in KROTKIE:
                continue
            pre = wstepna(m, l)
            if pre is None:
                continue
            k = K_PETLA if pow_ >= 3 else {K_AUTO: K_PL_SAFE, K_PRZEGLAD: K_PL_PRZEGLAD}.get(pre, pre)
            wyn.append(dict(linia=n + 1, klasa=k, slowo=m.group(0)[:60], pl=l[max(0, m.start() - 70):m.end() + 70], en="", start=m.start(), koniec=m.end(), idx=n, tok=tok, dokl=False))
    return wyn


def napraw_linie(tr_lines, wyn, tylko_dokladne=False):
    """Stosuje bezpieczne autopoprawki (K_AUTO) w liscie linii tlumaczenia (liczba linii sie nie zmienia). Zwraca liczbe poprawek."""
    n = 0
    for w in sorted([x for x in wyn if x["klasa"] == K_AUTO and (x.get("dokl") or not tylko_dokladne)], key=lambda x: (x["idx"], -x["start"])):
        l = tr_lines[w["idx"]]
        if l[w["start"]:w["koniec"]] == w["slowo"]:
            tr_lines[w["idx"]] = l[:w["start"]] + w["tok"] + l[w["koniec"]:]; n += 1
    return n


def napraw_tekst(tekst, zrodlo, napraw=True):
    """Dla rozdziel: (nowy_tekst, znaleziska, liczba_autopoprawek). Autopoprawki tylko przy ukladzie linii 1:1 z oryginalem (inaczej tylko raport)."""
    tl = tekst.split("\n"); wyn, ok = przegladaj(tl, zrodlo.replace("\r\n", "\n").split("\n"))
    if not ok:
        return tekst, [], 0
    n = napraw_linie(tl, wyn, True) if napraw else 0
    return "\n".join(tl), wyn, n


def main():
    ap = argparse.ArgumentParser(description="Przeglad czkawki DeepL: podwojone slowa i bledy na wielkich literach")
    ap.add_argument("katalogi", nargs="*"); ap.add_argument("--korzen", default="", help="katalog glowny: przegladaj wszystkie podkatalogi, ktore maja org")
    ap.add_argument("--csv", default=""); ap.add_argument("--md", default="")
    ap.add_argument("--wszystkie", action="store_true", help="z --korzen: przegladaj tez katalogi BEZ org (tryb bez oryginalu, tylko klasyfikacja po slowie)")
    ap.add_argument("--napraw", action="store_true", help="zastosuj bezpieczne autopoprawki (K_AUTO) w plikach tlumaczen"); ap.add_argument("--kopia", default="", help="zip z wersjami zmienianych plikow (z --napraw)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    kat = list(a.katalogi)
    if a.korzen:
        kat += [os.path.join(a.korzen, x) for x in sorted(os.listdir(a.korzen)) if os.path.isdir(os.path.join(a.korzen, x)) and (a.wszystkie or os.path.isdir(os.path.join(a.korzen, x, "org")))]
    import zipfile
    zf = zipfile.ZipFile(a.kopia, "w", zipfile.ZIP_DEFLATED) if (a.napraw and a.kopia) else None
    wiersze = []; kl = collections.Counter(); slowa = collections.Counter(); pliki_zle = set(); ukl = []; nplik = nkat = nbrak = nnap = 0
    for d in kat:
        org = os.path.join(d, "org"); zr = org if os.path.isdir(org) else d; nkat += 1
        for f in sorted(os.listdir(d)):
            if not f.endswith(" pl.txt") or re.search(r"_all(_\d+)? pl\.txt$", f) or f.startswith("DO_PRZETLUMACZENIA"):
                continue
            sp = os.path.join(zr, f[:-7] + ".txt")
            raw = open(os.path.join(d, f), "rb").read()
            try:
                tl = raw.decode("utf-8").split("\n")
            except UnicodeDecodeError:
                continue
            if not os.path.exists(sp):
                nbrak += 1
                if not a.wszystkie:
                    continue
                wyn = przegladaj_pl(tl)
            else:
                nplik += 1
                wyn, ok = przegladaj(tl, dec(open(sp, "rb").read()).replace("\r\n", "\n").split("\n"))
                if not ok:
                    ns = sum(1 for x in dec(open(sp, "rb").read()).split("\n") if x.strip()); nt = sum(1 for x in tl if x.strip())
                    ukl.append((os.path.basename(d), f[:-7], ns, nt)); print("UKLAD LINII: %s\\%s: niepustych linii oryginal %d, tlumaczenie %d (brakuje %d)" % (os.path.basename(d), f, ns, nt, ns - nt)); continue
            for w in wyn:
                kl[w["klasa"]] += 1
                if w["klasa"] in ZLE:
                    pliki_zle.add((d, f)); slowa[(w["klasa"], w["tok"].lower() if w["tok"] else "(wielkie litery)")] += 1
                wiersze.append([os.path.basename(d), f[:-7], w["linia"], w["klasa"], w["slowo"], w["pl"].replace("\n", " "), w["en"]])
            if a.napraw and any(x["klasa"] == K_AUTO for x in wyn):
                if zf:
                    zf.writestr(os.path.join(os.path.basename(d), f), raw)
                nnap += napraw_linie(tl, wyn); open(os.path.join(d, f), "wb").write("\n".join(tl).encode("utf-8"))
        print("  %-36s plikow: %d, podejrzanych miejsc w katalogu: %d" % (os.path.basename(d)[:36], sum(1 for x in os.listdir(d) if x.endswith(" pl.txt")), sum(1 for r in wiersze if r[0] == os.path.basename(d) and r[3] in ZLE)))
        sys.stdout.flush()
    if zf:
        zf.close()
    print("Przejrzano %d katalogow, %d tlumaczen z oryginalem (bez oryginalu: %d%s)" % (nkat, nplik, nbrak, ", przejrzane w trybie bez oryginalu" if a.wszystkie else ", pominiete"))
    print("Znaleziska wg klas:")
    for k, n in kl.most_common():
        print("  %-52s %6d" % (k, n))
    print("Pliki z podejrzana czkawka (K_AUTO / K_PRZEGLAD / K_CAPS): %d" % len(pliki_zle))
    for (k, w), n in slowa.most_common(25):
        print("  %-26s %-32s %5d" % (k[:26], w[:32], n))
    if ukl:
        print("Pliki z MNIEJSZA liczba niepustych linii niz oryginal (utracone akapity?): %d" % len(ukl))
        for x in ukl:
            print("  %s | %s | oryginal %d, tlumaczenie %d" % x)
    if a.napraw:
        print("Zastosowano autopoprawek: %d" % nnap)
    if a.csv:
        with open(a.csv, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";"); w.writerow(["katalog", "plik", "linia", "klasa", "slowo", "kontekst_pl", "kontekst_en"]); w.writerows(wiersze)
        print("CSV:", a.csv)
    if a.md:
        L = ["# Przeglad czkawki DeepL", "", "Katalogow %d, tlumaczen z oryginalem %d." % (nkat, nplik), "", "| klasa | liczba |", "|---|---|"] + ["| %s | %d |" % kv for kv in kl.most_common()]
        L += ["", "## Najczestsze podejrzane", ""] + ["- %s: **%s** x%d" % (k, w, n) for (k, w), n in slowa.most_common(60)]
        L += ["", "## Wszystkie podejrzane (katalog | plik | linia | slowo)", ""] + ["- %s | %s | l.%s | %s | %s" % (r[0], r[1], r[2], r[3], r[4]) for r in wiersze if r[3] in ZLE]
        open(a.md, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n"); print("MD:", a.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

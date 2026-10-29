# -*- coding: utf-8 -*-
"""Raport kontrolny katalogu (litert-rozdziel): plik 'Raport tłumaczeń katalogu <NAZWA>.md' w opracowywanym katalogu.

Powstaje automatycznie na końcu pracy nad katalogiem (po kontroli, sprzątaniu, łączeniu akapitów i cięciu tur) albo na żądanie (rozdziel.py KATALOG --tylko-raport).
Źródła: tłumaczenia w katalogu, oryginały w org, listy cięć i akapitów w org oraz dane przebiegu (słownik, czkawka, ostrzeżenia), które pełny przebieg rozdziel
zapisuje na chwilę w pliku <Katalog>_przebieg_rozdziel.json (raport go zużywa i kasuje). Ręczne poprawki opisane w pliku <Katalog>_poprawki_reczne.txt (w katalogu)
trafiają do raportu, a plik jest przenoszony do org."""
import datetime, json, os, re, shutil, statistics

NAZWA_PREFIX = "Raport tłumaczeń katalogu "
STOP_EN = frozenset("the and you your her his she was with that for said what this have had not but are him they were from there when would could about into than then them will just like know".split())
DBL = re.compile(r"\b([^\W\d_]{2,})[ \t]+\1\b", re.I)
PL_ZNAKI = re.compile("[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")


def kat(d):
    return os.path.basename(os.path.normpath(d))


def nazwa_raportu(d):
    return NAZWA_PREFIX + kat(d) + ".md"


def sciezka_przebiegu(d):
    return os.path.join(d, kat(d) + "_przebieg_rozdziel.json")


def zapisz_przebieg(d, ctx):
    with open(sciezka_przebiegu(d), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ctx, fh, ensure_ascii=False)


def wczytaj_przebieg(d):
    p = sciezka_przebiegu(d)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _czytaj(p):
    raw = open(p, "rb").read()
    try:
        return raw.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace").replace("\r\n", "\n")


def _listy_org(d):
    org = os.path.join(d, "org"); ciecia, akap = {}, {}
    lp = os.path.join(org, kat(d) + "_tury_pl.txt")
    if os.path.isfile(lp):
        for w in open(lp, encoding="utf-8").read().split("\n")[1:]:
            m = re.match(r"^\s*(\d+)\s{2}(.+?)\s*$", w)
            if m:
                ciecia[m.group(2)] = int(m.group(1))
    la = os.path.join(org, kat(d) + "_akapity.txt")
    if os.path.isfile(la):
        for w in open(la, encoding="utf-8").read().split("\n"):
            m = re.match(r"^\s+(\d+)\s+->\s+(\d+)\s+\(zawiniete bloki:\s*(\d+)%\)\s+(.+?)\s*$", w)
            if m:
                akap[m.group(4)] = (int(m.group(1)), int(m.group(2)))
    return ciecia, akap


def _angielskie(linie):
    wyn = []
    for i, l in enumerate(linie):
        s = l.strip()
        if len(s) < 40 or PL_ZNAKI.search(s):
            continue
        sl = re.findall(r"[a-z']+", s.lower())
        if len(sl) >= 6 and sum(1 for w in sl if w in STOP_EN) >= max(3, len(sl) // 5):
            wyn.append(i + 1)
    return wyn


def _c(s):
    return str(s).replace("|", "\\|")


def zbuduj(d, wyniki, ctx, zastosuj_poprawki=None, reguly=None):
    """Zwraca (tekst_markdown, flagi_liczba). wyniki: lista nazw 'X pl.txt'."""
    org = os.path.join(d, "org"); ciecia, akap = _listy_org(d)
    wiersze, flagi, podw, ang_all, slowa_t, dl_o = [], [], [], [], 0, 0
    zn_o = zn_t = nb_o_sum = nb_t_sum = zg = bez_org = mam = resztki = 0; ratios = []; dlugie = 0
    for f in sorted(wyniki, key=str.lower):
        t = _czytaj(os.path.join(d, f)); L = t.split("\n"); nb_t = sum(1 for x in L if x.strip())
        op = next((x for x in (os.path.join(org, f[:-7] + ".txt"), os.path.join(d, f[:-7] + ".txt")) if os.path.isfile(x)), None)
        fl = []; cuts = ciecia.get(f, 0); ak = akap.get(f)
        slowa = len(re.findall(r"\w+", t)); slowa_t += slowa
        dw = [m for m in DBL.finditer(t)]; podw.extend((f[:-7], t[max(0, m.start() - 40):m.start()].replace("\n", " "), m.group(0), t[m.end():m.end() + 30].replace("\n", " ")) for m in dw)
        ang = _angielskie(L)
        if ang:
            fl.append("możliwie nieprzetłumaczone linie: " + ", ".join(map(str, ang[:6])))
            ang_all.append((f[:-7], ang))
        if zastosuj_poprawki and reguly:
            _, c = zastosuj_poprawki(t, reguly)
            if c:
                resztki += sum(c.values()); fl.append("pozostały znane błędy słownika: %d" % sum(c.values()))
        mam += len(re.findall(r"mamusiow", t, re.I))
        if op:
            o = _czytaj(op); ol = o.split("\n"); nb_o = sum(1 for x in ol if x.strip()); ratio = len(t) / max(1, len(o))
            zn_o += len(o); zn_t += len(t); nb_o_sum += nb_o; nb_t_sum += nb_t; ratios.append(ratio); dlugie += sum(1 for x in ol if len(x) > 800)
            oczek = (ak[1] if ak else nb_o) + cuts
            if oczek == nb_t:
                zg += 1
            else:
                fl.append("układ linii: oczekiwano %d niepustych (oryginał %s + cięcia %d), jest %d" % (oczek, ("po akapitach %d" % ak[1]) if ak else nb_o, cuts, nb_t))
            if ratio < 0.85 or ratio > 1.40:
                fl.append("nietypowy stosunek długości %.2f" % ratio)
            wiersze.append((f[:-7], len(o), len(t), ratio, nb_o, nb_t, cuts, len(dw), fl))
        else:
            bez_org += 1; fl.append("brak oryginału (nie sprawdzono układu ani długości)")
            wiersze.append((f[:-7], None, len(t), None, None, nb_t, cuts, len(dw), fl))
        if fl:
            flagi.append((f[:-7], fl))
    n = len(wyniki); par = n - bez_org; dwoj = len(podw)
    L = ["# Raport tłumaczeń katalogu %s" % kat(d), "",
         "*Wygenerowano: %s%s. Narzędzie: skill litert-rozdziel. Ten plik powstaje automatycznie po zakończeniu pracy nad katalogiem.*" % (
             ctx.get("czas") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), (", komputer " + ctx["komputer"]) if ctx.get("komputer") else ""), "",
         "## Podsumowanie", "", "| Wskaźnik | Wartość |", "|---|---|",
         "| Przetłumaczone pliki | %d (oryginały w `org`: %d) |" % (n, par),
         "| Liczba znaków | oryginały %s, tłumaczenia %s, mediana stosunku %.2f |" % (format(zn_o, ","), format(zn_t, ","), statistics.median(ratios) if ratios else 0),
         "| Układ linii zgodny z oryginałem | %d z %d plików (niepuste w oryginale + cięcia = niepuste w tłumaczeniu) |" % (zg, par),
         "| Cięcia tur (zmiana mówcy) | %d w %d plikach |" % (sum(ciecia.values()), len(ciecia)),
         "| Łączenie twardo zawiniętych linii w akapity | %s |" % (("%d plików (niepustych linii %d → %d)" % (len(akap), sum(a for a, b in akap.values()), sum(b for a, b in akap.values()))) if akap else "nie dotyczy (żaden plik nie był zawinięty)"),
         "| Linie dłuższe niż 800 znaków w oryginałach | %d (cięte przed tłumaczeniem, złożone z powrotem) |" % dlugie,
         "| Podwojone słowa w jednej linii | %d (%.2f na 10 tys. słów; odniesienie: średnio 0,5, mediana 0,1) |" % (dwoj, 1e4 * dwoj / max(1, slowa_t)),
         "| Resztki znanych błędów DeepL (słownik) | %d |" % resztki,
         "| Formy `mamusiow*` (reguły wyłączone) | %d |" % mam,
         "| Linie możliwie nieprzetłumaczone | %d w %d plikach |" % (sum(len(x[1]) for x in ang_all), len(ang_all)),
         "| Pliki z flagami do sprawdzenia | %d |" % len(flagi), "", "## Przebieg", ""]
    zam = ctx.get("zam")
    if zam is not None:
        L.append("- **Słownik poprawek DeepL:** %s." % (("%d zamian w %d plikach (%s)" % (sum(zam.values()), ctx.get("zam_plikow", 0), ", ".join("%s ×%d" % (k, v) for k, v in sorted(zam.items(), key=lambda kv: -kv[1])))) if zam else "brak zamian"))
    else:
        L.append("- **Słownik poprawek DeepL:** brak danych (raport z osobnego przebiegu).")
    cl = ctx.get("czk_linie")
    if cl is not None:
        _cache = {}

        def _naprawione(x):
            """Wpis 'do przegladu' z pierwszego przebiegu jest juz nieaktualny, gdy jego tekst zniknal z pliku (reczna poprawka po przegladzie)."""
            m = re.match(r"^do przegladu: (.+? pl\.txt) l\.\d+ \[[^\]]*\] '(.*?)' \| PL: \.\.\.(.*?)(?:\.\.\.)?(?: \| EN:.*)?$", x)
            if not m:
                return False
            p = os.path.join(d, m.group(1))
            if not os.path.isfile(p):
                return False
            if p not in _cache:
                _cache[p] = _czytaj(p)
            slowo, frag = m.group(2), m.group(3)[:50]
            if slowo and not slowo.startswith("stosunek") and slowo not in _cache[p]:
                return True
            return bool(frag) and frag not in _cache[p]
        auto = sum(1 for x in cl if x.startswith("poprawiono"))
        nap = [x for x in cl if x.startswith("do przegladu") and _naprawione(x)]
        prz = len(cl) - auto
        L.append("- **Czkawka DeepL** (podwojone słowa, błędy na wielkich literach, porównane z oryginałem): autopoprawek %d, do przeglądu %d%s, uzasadnionych podwojeń pominiętych %d." % (
            auto, prz, (" (z tego %d naprawiono ręcznie po przeglądzie, patrz Poprawki ręczne; otwartych: %d)" % (len(nap), prz - len(nap))) if nap else "", ctx.get("czk_uzasadnione", 0)))
        for x in cl[:40]:
            L.append("  - " + ("**[naprawione ręcznie]** " if x in nap else "") + _c(x)[:300])
    if ctx.get("ffd_znakow"):
        L.append("- **Znaki uszkodzone (U+FFFD):** usunięto %d znak(ów) w %d miejscach." % (ctx["ffd_znakow"], ctx.get("ffd_miejsc", 0)))
    if ctx.get("kopia_zip"):
        L.append("- **Nadpisanie istniejących wyników:** stare wersje zachowano w `%s`." % ctx["kopia_zip"])
    for u in ctx.get("uwagi", []):
        L.append("- **Uwaga z przebiegu:** " + _c(u)[:300])
    rp = os.path.join(d, kat(d) + "_poprawki_reczne.txt"); reczne = _czytaj(rp).strip() if os.path.isfile(rp) else ""
    L += ["", "## Poprawki ręczne", "", reczne if reczne else "Brak (wszystko załatwiły kroki automatyczne).", "", "## Pliki z flagami do sprawdzenia", ""]
    if flagi:
        for f, fl in flagi:
            L.append("- **%s:** %s" % (_c(f), "; ".join(fl)))
    else:
        L.append("Brak flag.")
    L += ["", "## Podwojone słowa w jednej linii (do wglądu)", ""]
    if podw:
        L.append("Lista pomocnicza, nie błędów: większość to poprawne konstrukcje (`to to`, `nie nie`, onomatopeje). Pokazano do 40.")
        L.append("")
        for f, a, w, b in podw[:40]:
            L.append("- %s: …%s**%s**%s…" % (_c(f[:40]), _c(a), _c(w), _c(b)))
    else:
        L.append("Brak.")
    L += ["", "## Pliki", "", "| Plik | Oryginał (zn.) | Tłumaczenie (zn.) | Stosunek | Niepuste linie oryg. → tłum. | Cięcia tur | Podwojone słowa | Flagi |", "|---|---:|---:|---:|---|---:|---:|---|"]
    for f, zo, zt, ra, no, nt, cu, dw, fl in wiersze:
        L.append("| %s | %s | %s | %s | %s | %d | %d | %s |" % (_c(f), format(zo, ",") if zo is not None else "–", format(zt, ","), ("%.2f" % ra) if ra is not None else "–", ("%d → %d" % (no, nt)) if no is not None else "– → %d" % nt, cu, dw, "; ".join(fl) if fl else ""))
    return "\n".join(L) + "\n", len(flagi)


def zapisz_raport(d, wyniki, ctx=None, zastosuj_poprawki=None, reguly=None):
    """Buduje i zapisuje raport w katalogu d. Zwraca (sciezka, liczba_flag)."""
    ctx = dict(ctx) if ctx else wczytaj_przebieg(d)
    tekst, nflag = zbuduj(d, wyniki, ctx, zastosuj_poprawki, reguly)
    sciezka = os.path.join(d, nazwa_raportu(d))
    with open(sciezka, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(tekst)
    p = sciezka_przebiegu(d)
    if os.path.isfile(p):
        os.remove(p)
    rp = os.path.join(d, kat(d) + "_poprawki_reczne.txt")
    if os.path.isfile(rp) and os.path.isdir(os.path.join(d, "org")):
        shutil.move(rp, os.path.join(d, "org", os.path.basename(rp)))
    return sciezka, nflag

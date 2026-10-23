# -*- coding: utf-8 -*-
"""Szukanie duplikatow wsrod oryginalow w katalogu PRZED scalaniem (skill litert).

Uzycie:  python duplikaty.py "C:\\sciezka\\KATALOG" [--wzorzec @] [--prog 0.6] [--do-kosza]

Plik-kandydat (w nazwie jest --wzorzec, domyslnie '@') ma ODPOWIEDNIK, gdy co najmniej --prog (domyslnie 60%) jego tresci
(ciagi 8 slow, bez znakow interpunkcyjnych i wielkosci liter) znajduje sie w jednym pliku BEZ wzorca w nazwie. Odpowiednikiem
moze byc tez wiekszy plik (zbior, powiesc), w ktorym kandydat jest zawarty. Domyslnie TYLKO RAPORT; z --do-kosza pliki z
odpowiednikiem sa przenoszone do Kosza (Windows, mozna je odzyskac), a pliki bez odpowiednika zostaja.
Pomijane: pliki techniczne litert (scalenia, spis), tlumaczenia ' pl.txt', kopie _copy(N), czesci duzych plikow."""
import os, re, sys, argparse, collections


def dec(raw):
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def oryginaly(d):
    nazwa = os.path.basename(os.path.normpath(d)).lower()
    wszystkie = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and f.lower().endswith(".txt")]
    male = {f.lower() for f in wszystkie}
    wynik = []
    for f in wszystkie:
        fl = f.lower()
        if re.match(r"^%s_all(_\d+)?( pl)?\.txt$" % re.escape(nazwa), fl) or fl in (nazwa + "_spis_scalenia.txt", nazwa + "_raport_naprawy.txt"):
            continue
        if fl.endswith(" pl.txt") or "_copy(" in fl or fl.startswith("do_przetlumaczenia"):
            continue
        m = re.match(r"^(.*)_\d+\.txt$", f, re.I)
        if m and (m.group(1) + ".txt").lower() in male:      # czesc duzego pliku: istnieje oryginal bez numeru
            continue
        wynik.append(f)
    return sorted(wynik)


def do_kosza(path):
    """Przenosi plik do Kosza (Windows). Zwraca True, gdy plik zniknal z miejsca."""
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


def main():
    ap = argparse.ArgumentParser(description="Szukanie duplikatow wsrod oryginalow (domyslnie tylko raport)")
    ap.add_argument("katalog")
    ap.add_argument("--wzorzec", default="@", help="tekst w nazwie pliku-kandydata do usuniecia (domyslnie '@')")
    ap.add_argument("--prog", type=float, default=0.6, help="minimalne pokrycie tresci kandydata przez odpowiednik (0-1, domyslnie 0.6)")
    ap.add_argument("--do-kosza", action="store_true", help="przenies do Kosza pliki z odpowiednikiem (bez tego tylko raport)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    d = a.katalog
    if not os.path.isdir(d):
        print("BLAD: brak katalogu:", d)
        return 1
    pliki = oryginaly(d)
    kand = [f for f in pliki if a.wzorzec in f]
    pula = [f for f in pliki if a.wzorzec not in f]
    print("oryginalow: %d | kandydatow (nazwa zawiera '%s'): %d | pula odpowiednikow: %d" % (len(pliki), a.wzorzec, len(kand), len(pula)))
    if not kand:
        print("Brak plikow-kandydatow.")
        return 0

    def szing(f, k=8):
        w = re.findall(r"\w+", dec(open(os.path.join(d, f), "rb").read()).lower())
        return {hash(tuple(w[i:i + k])) for i in range(max(0, len(w) - k + 1))}, len(w)
    sz = {f: szing(f) for f in kand + pula}
    inv = collections.defaultdict(list)
    for f in pula:
        for h in sz[f][0]:
            inv[h].append(f)
    z_odp, bez_odp = [], []
    print("\n%-56s %7s  %-56s %6s %7s  %s" % ("kandydat", "slow", "najlepszy odpowiednik", "pokr.", "slow", "decyzja"))
    for f in kand:
        cnt = collections.Counter()
        for h in sz[f][0]:
            for g in inv.get(h, ()):
                cnt[g] += 1
        g, n = cnt.most_common(1)[0] if cnt else ("-", 0)
        pokr = n / max(1, len(sz[f][0]))
        slow_g = sz[g][1] if g in sz else 0
        decyzja = "ODPOWIEDNIK" if pokr >= a.prog else ("NIEPEWNE" if pokr >= 0.25 else "BRAK ODPOWIEDNIKA")
        (z_odp if pokr >= a.prog else bez_odp).append((f, g, pokr))
        print("%-56s %7d  %-56s %5.0f%% %7d  %s" % (f[:56], sz[f][1], g[:56], 100 * pokr, slow_g, decyzja))
    print("\nPODSUMOWANIE: z %d kandydatow odpowiednik ma %d, nie ma (lub niepewne) %d" % (len(kand), len(z_odp), len(bez_odp)))
    if a.do_kosza:
        if os.name != "nt":
            print("UWAGA: --do-kosza dziala tylko w Windows - nic nie przeniesiono")
            return 0
        ok = 0
        for f, g, pokr in z_odp:
            if do_kosza(os.path.join(d, f)):
                ok += 1
            else:
                print("UWAGA: nie udalo sie przeniesc do Kosza:", f)
        print("przeniesiono do Kosza: %d z %d plikow z odpowiednikiem. Powtorz scalanie (litert), bo pliki scalenia zawieraja stare teksty." % (ok, len(z_odp)))
    else:
        print("(tryb raportu: nic nie zmieniono; dodaj --do-kosza, aby przeniesc pliki z odpowiednikiem do Kosza)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

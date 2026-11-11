# -*- coding: utf-8 -*-
"""Rownoleglosc dla skilli litert (Windows, macOS, Linux: ten sam kod).

Uzycie (w skryptach):
    import rownolegle
    for wynik in rownolegle.uruchom(funkcja_na_poziomie_modulu, zadania, procesy):    # wyniki w KOLEJNOSCI zadan
        ...
Zasady, dzieki ktorym dziala jednakowo na XPS13, Alienware i Macu:
  * proces roboczy startuje metoda "spawn" (jedyna dostepna na Windowsie, domyslna na macOS), wiec funkcja robocza musi byc zwykla funkcja na poziomie modulu,
    a skrypt wywolujacy musi miec 'if __name__ == "__main__":' (czkawka_przeglad.py, rozdziel.py i poprawki_wstecz.py maja);
  * zadania i wyniki to zwykle dane (krotki, slowniki, listy, napisy): nic nie jest wspoldzielone, wiec wynik nie zalezy od liczby procesow;
  * gdy rownoleglosc nie wystartuje (brak uprawnien, tryb ograniczony, blad pamieci), skrypt sam przechodzi na tryb sekwencyjny i pisze o tym ostrzezenie.
Liczba procesow: argument --procesy N (N=1 wylacza rownoleglosc), zmienna srodowiskowa LITERT_PROCESY, a bez nich automatycznie: polowa watkow procesora, nie mniej niz 1 i nie wiecej niz 6
(XPS13: 4, Alienware: 6, typowy Mac: 4-6; hyper-threading i tak nie daje przy takim obciazeniu zysku).
Samotest na danym komputerze:  python rownolegle.py --samotest
"""
import os, sys


def domyslna_liczba_procesow():
    z = os.environ.get("LITERT_PROCESY", "").strip()
    if z.isdigit() and int(z) >= 1:
        return int(z)
    return max(1, min(6, (os.cpu_count() or 2) // 2))


PROG_ROZMIARU = int(os.environ.get("LITERT_PROG", "400000") or 400000)      # bajtow: ponizej tego rozmiaru zadania start procesow kosztuje wiecej, niz daje (tylko w trybie automatycznym)


def uruchom(funkcja, zadania, procesy=None, komunikaty=True, rozmiar=None):
    """Generator: wyniki funkcja(zadanie) w kolejnosci zadan. procesy: None/0 = automatycznie, 1 = bez rownoleglosci, N = dokladnie N procesow.
    rozmiar (bajty danych do przetworzenia, opcjonalnie): w trybie automatycznym male zadania (ponizej PROG_ROZMIARU) ida sekwencyjnie."""
    zadania = list(zadania)
    p = domyslna_liczba_procesow() if not procesy else int(procesy)
    if not procesy and rozmiar is not None and rozmiar < PROG_ROZMIARU:
        p = 1
    p = max(1, min(p, len(zadania)))
    zrobione = 0
    if p > 1:
        try:
            import multiprocessing
            from concurrent.futures import ProcessPoolExecutor
            ctx = multiprocessing.get_context("spawn")
            with ProcessPoolExecutor(max_workers=p, mp_context=ctx) as ex:
                for w in ex.map(funkcja, zadania, chunksize=max(1, len(zadania) // (p * 6))):
                    yield w
                    zrobione += 1
            return
        except (OSError, ImportError, PermissionError, NotImplementedError, RuntimeError) as e:        # BrokenProcessPool dziedziczy po RuntimeError
            if komunikaty:
                print("UWAGA: rownoleglosc niedostepna (%s: %s) - kontynuuje sekwencyjnie" % (type(e).__name__, str(e)[:90]), file=sys.stderr)
    for z in zadania[zrobione:]:
        yield funkcja(z)


def _kwadrat_z_pid(x):                       # funkcja robocza samotestu (musi byc na poziomie modulu)
    import time
    time.sleep(0.15)                          # krotka pauza: zadania nie sa wykonywane przez jeden proces, zanim wystartuja pozostale
    return (x * x, os.getpid())


def samotest():
    import platform, time
    print("system: %s %s | Python %s | procesor: %s watkow | automatycznie procesow: %d" % (platform.system(), platform.release(), platform.python_version(), os.cpu_count(), domyslna_liczba_procesow()))
    t = time.perf_counter(); wyn = list(uruchom(_kwadrat_z_pid, list(range(12)), 3)); dt = time.perf_counter() - t
    ok = [w[0] for w in wyn] == [x * x for x in range(12)]
    pidy = {w[1] for w in wyn}
    print("kolejnosc i wartosci poprawne: %s | uzytych procesow roboczych: %d | czas: %.2f s" % ("TAK" if ok else "NIE", len(pidy), dt))
    print("SAMOTEST: %s" % ("OK (rownoleglosc dziala)" if ok and len(pidy) >= 2 else ("OK, ale bez rownoleglosci (tryb sekwencyjny)" if ok else "BLAD")))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(samotest() if "--samotest" in sys.argv else 0)

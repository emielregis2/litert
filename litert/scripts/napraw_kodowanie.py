# -*- coding: utf-8 -*-
"""Naprawa plikow z uszkodzonym kodowaniem cudzyslowow i apostrofow (skill litert).

Uzycie:  python napraw_kodowanie.py "C:\\sciezka\\KATALOG" [--zapisz]

Znany przypadek (opowiadania w starym kodowaniu 8-bitowym): cudzyslow i apostrof sa zapisane osobnymi bajtami (D4 = cudzyslow,
D3 = apostrof), a BAJT NASTEPUJACY PO NICH jest uszkodzony (ustawiony bit 7, skasowany bit 6: litera 's' to B3, 'O' to 8F, spacja
to A0, LF to 8A). Odczytany jako cp1252 daje to smieci (O z akcentem, S z haczykiem) i bajty, ktorych cp1252 nie zna. Naprawa
odwraca uszkodzenie jednoznacznie. Domyslnie TYLKO RAPORT; z --zapisz plik jest naprawiany (po weryfikacji): stary oryginal trafia
do podkatalogu _zastapione, nowy jest zapisany w UTF-8 bez BOM z koncami linii LF (prawidlowe cudzyslowy i apostrofy typograficzne).
Pomijane: pliki poprawne w UTF-8 (chyba ze maja takie sekwencje i prawie zadnej zwyklej cyrylicy), pliki techniczne litert, tlumaczenia ' pl.txt', kopie _copy(N), czesci duzych plikow."""
import os, re, sys, argparse, shutil, collections

WZORZEC = re.compile(rb"[\xd3\xd4][\x80-\xbf]")


def uszkodzony(raw):
    """True, gdy plik wyglada na uszkodzony: min. 5 sekwencji D3/D4 + bajt 80-BF i (nie jest poprawnym UTF-8 albo, jako UTF-8, daje
    znaki z zakresu U+04C0-U+053F bez zwyklej cyrylicy: te sekwencje to tez poprawne dwubajtowe znaki UTF-8, wiec latwo je przeoczyc)."""
    if len(WZORZEC.findall(raw)) < 5:
        return False
    try:
        t = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return True
    ob = sum(1 for c in t if "\u04c0" <= c <= "\u053f")
    cyr = sum(1 for c in t if "\u0410" <= c <= "\u044f")
    return ob >= 5 and cyr <= ob


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


def napraw_tekst(raw):
    """Zwraca (tekst, statystyki, liczba_nieobjetych). Zwykle bajty czytane jako cp1252, sekwencje D3/D4 + uszkodzony bajt odtwarzane."""
    czesci, bufor, st, nieobjete, i = [], bytearray(), collections.Counter(), 0, 0

    def zrzut():
        if bufor:
            czesci.append(bytes(bufor).decode("cp1252"))
            bufor.clear()
    while i < len(raw):
        b = raw[i]
        if b in (0xD3, 0xD4) and i + 1 < len(raw) and 0x80 <= raw[i + 1] <= 0xBF:
            n = raw[i + 1]
            nn = raw[i + 2] if i + 2 < len(raw) else 0x0A
            wyn, k = None, None
            if b == 0xD3 and 0xA1 <= n <= 0xBF and chr(n - 0x40).isalpha():
                wyn, k = "\u2019" + chr(n - 0x40), "apostrof+litera"
            elif b == 0xD4:
                if n == 0x8A and nn in (0x0A, 0x0D, 0x20):
                    wyn, k = "\u201d\n", "zamykajacy cudzyslow+LF"
                elif n == 0xA0:
                    wyn, k = "\u201d ", "zamykajacy cudzyslow+spacja"
                elif 0x81 <= n <= 0x9A and n != 0x8A:
                    wyn, k = "\u201c" + chr(n - 0x40), "otwierajacy cudzyslow+wielka litera"
                elif n == 0x8A:
                    wyn, k = "\u201cJ", "otwierajacy cudzyslow+J"
                elif 0xA1 <= n <= 0xBF and chr(n - 0x40).isalpha():
                    wyn, k = "\u201c" + chr(n - 0x40), "otwierajacy cudzyslow+mala litera"
            if wyn is not None:
                zrzut()
                czesci.append(wyn)
                st[k] += 1
                i += 2
                continue
            nieobjete += 1
        bufor.append(b)
        i += 1
    zrzut()
    return "".join(czesci).replace("\r\n", "\n"), st, nieobjete


def main():
    ap = argparse.ArgumentParser(description="Naprawa uszkodzonych cudzyslowow i apostrofow (domyslnie tylko raport)")
    ap.add_argument("katalog")
    ap.add_argument("--zapisz", action="store_true", help="napraw pliki (stary oryginal do _zastapione); bez tego tylko raport")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    d = a.katalog
    if not os.path.isdir(d):
        print("BLAD: brak katalogu:", d)
        return 1
    kandydaci = []
    for f in oryginaly(d):
        raw = open(os.path.join(d, f), "rb").read()
        if not uszkodzony(raw):                        # poprawny UTF-8 lub zwykly plik: nie dotyczy
            continue
        kandydaci.append((f, raw, len(WZORZEC.findall(raw))))
    print("plikow z uszkodzonymi sekwencjami D3/D4 (min. 5): %d" % len(kandydaci))
    if not kandydaci:
        return 0
    gotowe = []
    for f, raw, n in kandydaci:
        try:
            tekst, st, nieobjete = napraw_tekst(raw)
        except UnicodeDecodeError as e:
            print("  %-70s sekwencji %4d | NIE: po naprawie zostaly bajty nieokreslone w cp1252 (%s)" % (f[:70], n, e))
            continue
        nap = sum(st.values())
        resztki = tekst.count("\u00d3") + tekst.count("\u00d4")
        ok = nieobjete == 0 and "\ufffd" not in tekst and resztki <= 0.05 * max(1, nap)
        print("  %-70s sekwencji %4d | naprawione %4d | nieobjete %d | U+FFFD %d | resztki znakow O/O z akcentem %d | %s"
              % (f[:70], n, nap, nieobjete, tekst.count("\ufffd"), resztki, "OK" if ok else "NIE (zostaje bez zmian)"))
        for k, v in st.most_common():
            print("        %-40s %d" % (k, v))
        if ok:
            gotowe.append((f, raw, tekst))
    if not a.zapisz:
        print("\n(tryb raportu: nic nie zmieniono; dodaj --zapisz, aby naprawic %d plik(ow): stary oryginal trafi do _zastapione)" % len(gotowe))
        return 0
    kat = os.path.join(d, "_zastapione")
    for f, raw, tekst in gotowe:
        cel = os.path.join(kat, f)
        if os.path.exists(cel):
            print("UWAGA: w _zastapione jest juz plik %s - pomijam (nic nie zmieniono)" % f)
            continue
        os.makedirs(kat, exist_ok=True)
        shutil.move(os.path.join(d, f), cel)
        with open(os.path.join(d, f), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(tekst)
        sprawdz = open(os.path.join(d, f), "rb").read().decode("utf-8") == tekst
        print("NAPRAWIONO: %s | nowy plik %d B (UTF-8 bez BOM), stary oryginal w _zastapione (%d B) | odczyt zgodny: %s"
              % (f, os.path.getsize(os.path.join(d, f)), os.path.getsize(cel), sprawdz))
    if gotowe:
        print("\nWAZNE: powtorz scalanie (litert), bo pliki scalenia zawieraja stary tekst. Jesli tlumaczenie tego katalogu juz sie zaczelo,")
        print("tlumaczenia starych czesci zawieraja smieci i trzeba je powtorzyc (stare archiwum .zip przenies do _zastapione).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

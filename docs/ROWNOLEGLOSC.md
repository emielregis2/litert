# Równoległość i wydajność: zasady

Dokument opisuje, kiedy skille `litert` i `litert-rozdziel` pracują na wielu rdzeniach, jak to ustawić na każdym komputerze (Windows, macOS) i jakie reguły gwarantują, że wynik jest ten sam co w trybie jednowątkowym. Skrót jest w [README.md](../README.md#wydajność-i-równoległość-zasady).

## Krótko

- **Największy zysk dała poprawa algorytmu słownika, a nie równoległość.** `zastosuj_poprawki` pomija reguły, których tekstu nie ma w pliku (wynik identyczny). `rozdziel` na katalogu 6,9 MB: **131,9 s → 11,7 s (11×)**.
- **Równoległość dokłada 2–4× tam, gdzie zostają ciężkie obliczenia na plik:** `czkawka_przeglad.py` (wyrównywanie tłumaczenia do oryginału) i `poprawki_wstecz.py` (skan wszystkich katalogów).
- **Wynik nie zależy od liczby procesów.** Zapisy plików, kopie zapasowe i raporty robi wyłącznie proces główny, w kolejności plików.
- **Wszystko ma awaryjny tryb jednowątkowy**: gdy równoległość nie wystartuje, skrypt sam przechodzi na tryb sekwencyjny i pisze o tym ostrzeżenie.

## Zasady (obowiązują wszystkie skrypty)

1. **Gdzie jest równoległość.** Tylko w skryptach, w których praca na pliku jest ciężka i niezależna od innych plików: `czkawka_przeglad.py` i `poprawki_wstecz.py`. `scal.py` i `rozdziel.py` są jednowątkowe (`rozdziel` przyspieszono algorytmicznie, patrz niżej).
2. **Liczba procesów (kolejność ważności):** `--procesy N` w wierszu poleceń, potem zmienna środowiskowa `LITERT_PROCESY`, a bez nich **automatycznie: połowa wątków procesora, nie mniej niż 1 i nie więcej niż 6**. `--procesy 1` całkowicie wyłącza równoległość.
3. **Jawna liczba wygrywa z progiem.** W trybie automatycznym zadania mniejsze niż ok. **400 KB** danych (zmienna `LITERT_PROG`, w bajtach) idą sekwencyjnie, bo start procesów kosztuje więcej, niż daje (w teście 14 małych plików: 0,3 s sekwencyjnie wobec 1,8 s w 4 procesach). Gdy podasz `--procesy N` (N większe od 1), skrypt używa dokładnie N procesów.
4. **Deterministyczny wynik.** Wyniki wracają **w kolejności zadań**, zadania i wyniki to zwykłe dane (nic nie jest współdzielone), a wszystkie zapisy (pliki, kopie zip, CSV, raporty) i wydruki robi proces główny. Testy porównują wyniki dla 1 i 4 procesów bajt w bajt.
5. **Ten sam kod na Windowsie, macOS i Linuksie.** Procesy startują metodą `spawn` (jedyna dostępna na Windowsie, domyślna na macOS; używamy jej wszędzie, więc zachowanie jest jednakowe). Konsekwencja dla kodu: funkcja robocza musi być zwykłą funkcją na poziomie modułu, a skrypt musi mieć `if __name__ == "__main__":`.
6. **Awaryjny powrót do trybu jednowątkowego.** Przy błędach uruchomienia równoległości (`OSError`, `PermissionError`, `ImportError`, `NotImplementedError`, `RuntimeError` w tym `BrokenProcessPool`) skrypt wypisuje na stderr ostrzeżenie `UWAGA: rownoleglosc niedostepna (...)` i **kończy pracę sekwencyjnie od pierwszego nieodebranego zadania**. Nic nie jest liczone dwa razy ani pomijane.
7. **Bezpieczeństwo zmian.** Narzędzia zmieniające pliki (`poprawki_wstecz.py`, `czkawka_przeglad.py --napraw`) robią kopię zip każdego zmienianego pliku **przed** zapisem, weryfikują wynik przed zapisem (ta sama liczba linii, zmienione tylko linie z dopasowaną frazą, drugi przebieg niczego nie zmienia) i po zapisie, a `poprawki_wstecz.py` ma dodatkowo bezpiecznik (`--limit-zamian`, `--limit-plikow`).
8. **Postęp widać na bieżąco.** Wyniki spływają w kolejności plików, więc `czkawka_przeglad.py` wypisuje podsumowanie każdego katalogu zaraz po jego zakończeniu.

## Gdzie jest równoległość (przegląd narzędzi)

| Skrypt | Równolegle? | Opcje | Uwagi |
|---|---|---|---|
| `litert-rozdziel/scripts/czkawka_przeglad.py` | **tak** | `--procesy N` | praca na pliku (wyrównanie do oryginału, klasyfikacja podwojeń) w procesach roboczych; zapis i `--kopia` w procesie głównym |
| `litert-rozdziel/scripts/poprawki_wstecz.py` | **tak** | `--procesy N` | skan i obliczenia na pliku w procesach roboczych; weryfikacja, kopia zip i zapis w procesie głównym |
| `litert-rozdziel/scripts/rozdziel.py` | nie | | przyspieszony algorytmicznie (prefiltr reguł), patrz niżej |
| `litert/scripts/scal.py` | nie | | zadanie lekkie (przepakowanie plików) |
| `litert-rozdziel/scripts/rownolegle.py` | moduł wspólny | `--samotest` | `uruchom()`, `domyslna_liczba_procesow()` |

### Dlaczego `rozdziel.py` nie jest równoległy

Profil pokazał, że **80% czasu `rozdziel` zjadał sam słownik** (216 reguł, każda przechodziła po całym tekście, nawet gdy reguły w pliku nie było). Po poprawce (prefiltr: reguła jest pomijana, gdy jej tekstu bez względu na wielkość liter nie ma w pliku) całość trwa ok. 2 s na 1,7 MB, a pozostałe kroki (czkawka w układzie 1:1, weryfikacja pętli) są lekkie. Równoległość dałaby tu niewielki zysk za cenę dużo trudniejszego utrzymania, więc nie została dodana. Wynik poprawki jest **identyczny**: test `tests/test_slownik_rownowaznosc.py` porównuje starą i nową implementację na 1 947 tekstach syntetycznych (każda reguła w trzech wielkościach liter) oraz na prawdziwych plikach z korpusu, a 40 plików wynikowych `rozdziel` jest bajt w bajt takich samych jak ze starą wersją. Przy znakach `İ ı ſ K` (które `re.I` łączy z ASCII) prefiltr wyłącza się dla pewności.

## Ustawianie liczby procesów

```
python litert-rozdziel/scripts/czkawka_przeglad.py KATALOG --procesy 4
python litert-rozdziel/scripts/poprawki_wstecz.py --procesy 4 --sucho
```

Na stałe dla danego komputera (zmienna środowiskowa, działa dla wszystkich skryptów):

| System | Jak ustawić |
|---|---|
| Windows, PowerShell (na bieżącą sesję) | `$env:LITERT_PROCESY = 4` |
| Windows, trwale | `setx LITERT_PROCESY 4` (obowiązuje w nowych oknach) |
| Windows, cmd (na bieżące okno) | `set LITERT_PROCESY=4` |
| macOS / Linux (bieżąca sesja) | `export LITERT_PROCESY=4` (na stałe dopisz do `~/.zshrc`) |

Wartości orientacyjne (automatyczne ustawienie robi to samo: połowa wątków, 1–6):

| Komputer | Procesor | Wątków | Automatycznie |
|---|---|---:|---:|
| `DELLXPS13` | Intel Core i7-8550U (4 rdzenie) | 8 | 4 |
| `ALIENWARE` | Intel Core i7-8750H (6 rdzeni) | 12 | 6 |
| Mac | zależnie od modelu | zależnie | połowa wątków (4–6) |

Przy hyper-threadingu 8 procesów nie jest szybsze niż 4–6 (na `XPS13` test na czystym Pythonie dał 2,1× przy 4 procesach i 2,6× przy 6 i 8). Na Macu (Apple Silicon: rdzenie zamiast wątków) automatyczne ustawienie jest ostrożne; wyższą wartość możesz sprawdzić, podając `--procesy N`, i porównać czasy. Każdy proces roboczy zajmuje zwykle 50–150 MB pamięci; przy mało wolnej pamięci użyj `--procesy 2`.

## Wyniki pomiarów

Komputer: `ALIENWARE` (Intel Core i7-8750H, 6 rdzeni / 12 wątków, Windows 11, Python 3.14.10, plan zasilania „Zrównoważony”). Porównanie **starej wersji z GitHuba (commit `2661846`) z nową** na tych samych danych.

| Zadanie | Stara | Nowa, 1 proces | Nowa, kilka procesów | Skąd zysk |
|---|---:|---:|---:|---|
| `rozdziel`, 195 oryginałów (6,9 MB) | 131,9 s | 11,7 s | (bez równoległości) | algorytm słownika, 11× |
| słownik wstecz, 2 850 tłumaczeń (410 MB) | ok. 54 min (szacunek z próbki 160 plików: 319,9 s na 40 MB) | 91,9 s | **21,7 s** (6 procesów) | algorytm ok. 35×, równoległość 4,2× |
| czkawka, 60 tłumaczeń (2,6 MB) | 8,6 s | 8,4 s | 5,5 s (2), **4,6 s (4)**, 4,7 s (6) | równoległość 1,9× |
| czkawka, 224 tłumaczenia | 305,6 s | | **127,5 s** (4 procesy) | równoległość 2,4× |

Zastrzeżenia: to **pojedyncze pomiary** (powtórzony był tylko `rozdziel`: 11,7 s i 11,7 s). Czas starej wersji słownika dla całych 410 MB jest szacunkiem z próbki (pełny pomiar trwałby godzinę). Przy czkawce zysk powyżej 4 procesów ogranicza start procesów (ok. 1–1,5 s) i nierówny rozkład pracy (kilka dużych plików). Pomiary z `DELLXPS13` (4 rdzenie, komputer zajęty) są w następnej podsekcji; tam zysk wyszedł **wyższy**, nie niższy.

### DELLXPS13 (pomiar z 2026-11-11, komputer zajęty)

Komputer: Intel Core i7-8550U (4 rdzenie / 8 wątków, 1,8 GHz bazowo), Windows 11, Python 3.14.10, plan zasilania „Wysoka wydajność”, zasilanie sieciowe, 15,8 GB RAM. **Warunki pomiaru:** obciążenie procesora ok. 100%, wolna pamięć tylko 0,9–1,6 GB, w tle m.in. Claude, ChatGPT, codex, IObit Uninstaller, Dropbox i antywirus Kaspersky (`avp`). Liczby opisują więc **praktyczne warunki pracy**, a nie czyste skalowanie, a szum pomiarowy był duży.

| Zadanie | 1 proces | 2 procesy | 4 procesy | 6 procesów |
|---|---:|---:|---:|---:|
| czkawka, 100 prawdziwych plików (4,1 MB), 2 przebiegi każdej konfiguracji | 111,0 s i 76,6 s | 36,0 s i 33,9 s (**2,3×**) | 22,8 s i 24,6 s (**3,4×**) | 26,3 s i 18,0 s (**4,2×**) |
| `poprawki_wstecz.py --sucho`, 2 850 plików (410 MB) | 234,9 s i 230,6 s | | 100,3 s, 113,4 s i 72,6 s (tryb automatyczny) (**2,1–3,2×**) | |

Wynik czkawki (plik CSV) był identyczny we wszystkich 8 przebiegach, a 8 miejsc znalezionych przez `poprawki_wstecz.py` (6 × `– okrzyknął`, 2 × `natrzymałem`) takie same dla każdej liczby procesów. Pełny `tests/test_rownoleglosc.py` przeszedł.

Jak czytać te liczby:

- **Szum:** ta sama konfiguracja dawała wyniki różniące się nawet o 45% (czkawka, 1 proces: 111 s i 77 s; poprawki, 4 procesy: 100 s i 73 s). Podane przyspieszenia czkawki liczono względem najlepszego przebiegu jednoprocesowego (76,6 s).
- **Zysk wyższy niż w teście na czystym Pythonie** (2,1× przy 4 i 2,6× przy 6 procesach). Prawdopodobne przyczyny: system przydziela więcej czasu zadaniu z wieloma procesami, gdy komputer jest obciążony innymi aplikacjami, a procesy nakładają oczekiwanie na dysk i antywirus.
- **6 procesów vs 4:** w czkawce średnio 22,2 s wobec 23,7 s, czyli różnica w granicach szumu. Ustawienie automatyczne (4) jest rozsądne, zwłaszcza przy małej wolnej pamięci.
- **Tempo bezwzględne było tu gorsze niż na `ALIENWARE`** (skan 410 MB 231–235 s wobec 92 s). Przy mało wolnej pamięci cache dysku się nie utrzymuje, a antywirus skanuje każdy odczyt; test na czystym Pythonie przy mniejszym obciążeniu pokazywał jeden wątek `XPS13` jako szybszy, więc różnica wynika z warunków, a nie z procesora.
- **Start procesów jest wolny:** samotest (12 krótkich zadań w 3 procesach) trwał 31,8 s zamiast ok. 1 s. Przy zadaniach trwających minuty nie ma to znaczenia, a małe zadania chroni próg ok. 400 KB (tryb automatyczny wybiera wtedy tryb sekwencyjny).

Zalecenia dla tego komputera: zostaw ustawienie automatyczne (4); przy ciężkich zadaniach zamknij zbędne aplikacje; przy braku pamięci użyj `--procesy 2` (nadal ok. 2,3×); rozważ dodanie katalogu repozytorium i Pythona do wyjątków antywirusa (ustawienie systemowe, które należy do użytkownika).

## Jak to działa

Moduł `litert-rozdziel/scripts/rownolegle.py`:

- `domyslna_liczba_procesow()`: `LITERT_PROCESY`, a gdy go brak, `max(1, min(6, cpu_count // 2))`.
- `uruchom(funkcja, zadania, procesy=None, komunikaty=True, rozmiar=None)`: generator zwracający `funkcja(zadanie)` **w kolejności zadań**. `procesy`: `None` lub `0` = automatycznie, `1` = bez równoległości, `N` = dokładnie N. `rozmiar` (opcjonalnie, w bajtach) włącza próg małych zadań w trybie automatycznym. Używa `ProcessPoolExecutor` z kontekstem `spawn`, a porcje zadań to `max(1, liczba_zadań // (procesy * 6))`.
- `samotest()` / `python rownolegle.py --samotest`: uruchamia kilka krótkich zadań w procesach roboczych, sprawdza kolejność i wartości, wypisuje system, wersję Pythona, liczbę wątków i liczbę użytych procesów.

### Wzorzec dla nowego skryptu

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rownolegle

def _praca(arg):                      # na poziomie modułu (wymóg spawn); bez print, bez zapisu na dysk
    sciezka, opcja = arg
    ...                               # czytanie i obliczenia
    return {"sciezka": sciezka, "wynik": ...}      # zwykłe dane (słowniki, listy, napisy, liczby)

def main():
    zadania = [(p, opcja) for p in pliki]
    rozmiar = sum(os.path.getsize(p) for p, _ in zadania)
    for wynik in rownolegle.uruchom(_praca, zadania, a.procesy, rozmiar=rozmiar):
        ...                           # tu drukuj, sumuj i zapisuj (wyniki są w kolejności zadań)

if __name__ == "__main__":            # wymagane na Windowsie i macOS
    sys.exit(main())
```

Reguły: funkcja robocza nie drukuje, nie zapisuje i nie zmienia stanu globalnego; wszystko, co wraca, musi dać się zserializować (pickle); zapisy robi proces główny.

## Testy i samotest

Na każdym komputerze (na Macu `python3`):

```
python litert-rozdziel/scripts/rownolegle.py --samotest
python tests/test_rownoleglosc.py
python tests/test_slownik_rownowaznosc.py
```

- `--samotest`: sprawdza, czy równoległość w ogóle działa. `SAMOTEST: OK (rownoleglosc dziala)` oznacza, że użyto co najmniej 2 procesów roboczych. `OK, ale bez rownoleglosci (tryb sekwencyjny)` oznacza, że skrypty będą działać poprawnie, tylko wolniej.
- `tests/test_rownoleglosc.py`: **nie wymaga korpusu `Wymina`** (buduje dane syntetyczne). Sprawdza samotest, czkawkę (CSV, wydruk i pliki po `--napraw` dla 1 i 4 procesów, zwykłe podwojenia usunięte, `Sam sam` zostaje, kopia zip zgodna z oryginałami) oraz `poprawki_wstecz.py` (1 vs 4 procesów, drugi przebieg bez zmian).
- `tests/test_slownik_rownowaznosc.py [N]`: porównuje starą i nową implementację słownika; część na prawdziwych plikach pomija się, gdy nie ma korpusu.

Przetestowano: Windows 11 + Python 3.14.10 (`ALIENWARE`: pełny zestaw testów i pomiary; `XPS13`: pełny zestaw testów i pomiary), Linux + Python 3.12 (samotest). **macOS: kod jest napisany pod macOS (ten sam `spawn`, brak zależności od Windowsa), ale testów jeszcze tam nie uruchomiono.**

## Rozwiązywanie problemów

| Objaw | Przyczyna i co zrobić |
|---|---|
| `SAMOTEST: OK, ale bez rownoleglosci` albo ostrzeżenie `UWAGA: rownoleglosc niedostepna (...)` | Równoległość nie wystartowała (ograniczone środowisko, brak uprawnień, brak pamięci), a skrypt pracuje sekwencyjnie. Wynik jest poprawny, tylko wolniejszy. Sprawdź uprawnienia i program antywirusowy, uruchom z innego terminala. |
| Start procesów trwa kilka sekund (samotest dziesiątki sekund) | Typowe na obciążonym komputerze z antywirusem i małą wolną pamięcią (na `XPS13` samotest: 31,8 s). Skrypty działają poprawnie; dla małych zadań tryb automatyczny sam wybiera tryb sekwencyjny. Pomaga zamknięcie zbędnych aplikacji i wyjątek antywirusa dla Pythona i repozytorium. |
| Wolniej niż sekwencyjnie przy małych zadaniach | Start procesów kosztuje 0,3–1,5 s. Tryb automatyczny sam wybiera tryb sekwencyjny dla zadań poniżej ok. 400 KB; przy jawnym `--procesy N` użyj `--procesy 1`. |
| Zawieszenie lub brak postępu | Pierwsze wyniki pojawiają się po zakończeniu pierwszego katalogu/pliku; przy bardzo dużych plikach to potrwa. Sprawdź obciążenie procesora w menedżerze zadań. |
| Brak pamięci | Zmniejsz liczbę procesów: `--procesy 2` albo `LITERT_PROCESY=2`. |
| Na Macu `git` zgłasza błąd | Zepsuta nakładka na narzędzia deweloperskie; użyj `/Library/Developer/CommandLineTools/usr/bin/git` albo `GitHub Desktop`. Skrypty Pythona działają bez `git`. |

## Historia

- **2026-11-11:** prefiltr słownika w `rozdziel.py` (identyczny wynik, `rozdziel` ok. 11× szybszy), moduł `rownolegle.py`, `--procesy` w `czkawka_przeglad.py`, nowe narzędzie `poprawki_wstecz.py`, testy w `tests/`, ten dokument.
- **2026-11-11 (wieczór):** pomiary na `DELLXPS13` (komputer zajęty): równoległość dała 2–4×; opis warunków i zastrzeżeń w podsekcji „DELLXPS13”.

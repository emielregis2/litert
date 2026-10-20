# litert

Dwa skille dla Claude do przygotowania angielskich plików `.txt` do tłumaczenia w DeepL i odtworzenia ich po tłumaczeniu.

```
angielskie pliki .txt
        │  litert            (scalanie, limit 900 kB, znaczniki granic, spis)
        ▼
NazwaKatalogu_all_N.txt  +  NazwaKatalogu_spis_scalenia.txt
        │  tłumaczenie ręczne w aplikacji DeepL (wynik: "... pl.txt")
        ▼
NazwaKatalogu_all_N pl.txt
        │  litert-rozdziel   (rozcięcie po znacznikach, nazwy ze spisu)
        ▼
Oryginalna Nazwa pl.txt
```

## litert

Scala pliki `.txt` z katalogu w jak najmniej plików zbiorczych o rozmiarze do 900 000 bajtów.

- pomija wersje przetłumaczone (`... pl.txt`) i kopie (`..._copy(1).txt`),
- pakuje pliki wg rozmiaru (First Fit Decreasing), w każdym pliku scalenia pliki idą alfabetycznie,
- przed każdym plikiem wstawia znacznik `=====[[N|Nazwa]]=====`,
- tworzy `NazwaKatalogu_spis_scalenia.txt` (numer i nazwa każdego pliku w danym scaleniu),
- pliki większe niż limit nie trafiają do scaleń, tylko są dzielone linia po linii na części `Nazwa_1.txt`, `Nazwa_2.txt`, ...,
- nigdy nie rusza oryginałów ani przetłumaczonych plików.

```
python litert/scripts/scal.py "C:\sciezka\KATALOG" [--limit 900000]
```

## litert-rozdziel

Rozdziela przetłumaczone pliki scalenia (`NazwaKatalogu_all_N pl.txt`) na pliki o oryginalnych angielskich nazwach z końcówką ` pl`.

- granice wyznacza wyłącznie numer ze znacznika (nazwa mogła zostać przetłumaczona),
- nazwy plików wynikowych pochodzą ze spisu,
- nie nadpisuje istniejących plików (flaga `--nadpisz`),
- zgłasza brakujące, zdublowane i nadmiarowe znaczniki; nie zapisuje pliku, który mógłby się skleić z sąsiednim.
- składa przetłumaczone części dużych plików (`Nazwa_1 pl.txt`, `Nazwa_2 pl.txt`, ...) w jeden `Nazwa pl.txt` według sekcji "Pliki podzielone" ze spisu; gdy brakuje którejś części, nie składa pliku i to zgłasza.

```
python litert-rozdziel/scripts/rozdziel.py "C:\sciezka\KATALOG" [--nadpisz]
```

## Kodowanie i polskie znaki

Oba skrypty czytają pliki z automatycznym wykrywaniem kodowania (UTF-16 z BOM, UTF-8 z BOM lub bez, awaryjnie cp1250), a zapisują zawsze UTF-8 bez BOM z końcami linii LF. Dzięki temu polskie znaki, typograficzne apostrofy i cudzysłowy nie giną po drodze. Skrypty ostrzegają (`UWAGA`), gdy plik nie jest UTF-8, ma uszkodzone znaki (np. `Å‚`, `Ä…`, U+FFFD) albo przetłumaczony plik nie zawiera żadnej polskiej litery.

## Użycie jako skill Claude

Każdy folder (`litert/`, `litert-rozdziel/`) zawiera `SKILL.md` i skrypt w `scripts/`. Skille wywołuje się, podając Claude ścieżkę katalogu, np. "scal C:\...\NAZWA" albo "rozdziel C:\...\NAZWA".

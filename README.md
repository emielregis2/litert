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

## Typowy przebieg

1. **Scalanie:** `scal C:\...\KATALOG`. Powstają `KATALOG_all_N.txt`, `KATALOG_spis_scalenia.txt` oraz ewentualnie części dużych plików (`Nazwa_N.txt`).
2. **Tłumaczenie ręcznie w DeepL:** wgrywasz pliki `KATALOG_all_N.txt` i części dużych plików (nie spis i nie duże oryginały), a wyniki zapisujesz w tym samym katalogu z końcówką ` pl`.
3. **Rozdzielanie:** `rozdziel C:\...\KATALOG`. Powstają pliki `Oryginalna Nazwa pl.txt`, oryginały trafiają do podkatalogu `org`, a pliki techniczne (scalenia, spis, części, archiwum `.zip`) są kasowane po kontroli kompletności. W katalogu głównym zostają same tłumaczenia.

## litert

Scala pliki `.txt` z katalogu w jak najmniej plików zbiorczych o rozmiarze do 900 000 bajtów.

- pomija wersje przetłumaczone (`... pl.txt`); kopie (`..._copy(1).txt`) nie są scalane, ale przed scaleniem są analizowane: nowsza i większa kopia zastępuje oryginał (oryginał trafia do `_zastapione`), pozostałe przypadki trafiają do raportu "do decyzji" (flagi `--tylko-analiza-kopii`, `--nie-zastepuj-kopii`),
- pakuje pliki wg rozmiaru (First Fit Decreasing), w każdym pliku scalenia pliki idą alfabetycznie,
- przed każdym plikiem wstawia znacznik `=====[[N|Nazwa]]=====`,
- tworzy `NazwaKatalogu_spis_scalenia.txt` (numer i nazwa każdego pliku w danym scaleniu),
- pliki większe niż limit nie trafiają do scaleń, tylko są dzielone linia po linii na części `Nazwa_1.txt`, `Nazwa_2.txt`, ...,
- niczego nie kasuje: oryginały i przetłumaczone pliki zostają nietknięte (jedyny wyjątek: nowsza i większa kopia `_copy` zastępuje oryginał, a oryginał trafia do `_zastapione`).

```
python litert/scripts/scal.py "C:\sciezka\KATALOG" [--limit 900000] [--nie-zastepuj-kopii] [--tylko-analiza-kopii] [--bez-skracania]
```

## litert-rozdziel

Rozdziela przetłumaczone pliki scalenia (`NazwaKatalogu_all_N pl.txt`) na pliki o oryginalnych angielskich nazwach z końcówką ` pl`.

- granice wyznacza wyłącznie numer ze znacznika (nazwa mogła zostać przetłumaczona),
- nazwy plików wynikowych pochodzą ze spisu,
- nie nadpisuje istniejących plików (flaga `--nadpisz`),
- zgłasza brakujące, zdublowane i nadmiarowe znaczniki; nie zapisuje pliku, który mógłby się skleić z sąsiednim,
- brakujące przetłumaczone pliki wypakowuje sam z archiwum `.zip` z DeepL leżącego w katalogu (tylko brakujące, bez nadpisywania; wyłączane flagą `--bez-zip`),
- pojedyncze uszkodzone znaki U+FFFD zwrócone przez DeepL usuwa z wyniku automatycznie, z raportem (sekcja `NAPRAWA U+FFFD` i plik `..._raport_naprawy.txt`); do `--max-fffd` na plik (domyślnie 10), więcej to ostrzeżenie,
- po udanym i kompletnym rozdzieleniu po kontroli kompletności (wyniki zapisane, niepuste, bez znaczników, bez pętli DeepL, nieucięte) przenosi oryginały do podkatalogu `org` i **kasuje pliki techniczne** (pliki scalenia i ich tłumaczenia, spis, części dużych plików i ich tłumaczenia, archiwum `.zip` zawierające wyłącznie tłumaczenia tej partii); wyłączane flagą `--bez-org`, a `--zachowaj-techniczne` przenosi je do `org` zamiast kasować,
- składa przetłumaczone części dużych plików (`Nazwa_1 pl.txt`, `Nazwa_2 pl.txt`, ...) w jeden `Nazwa pl.txt` według sekcji "Pliki podzielone" ze spisu; gdy brakuje którejś części, nie składa pliku i to zgłasza. Puste linie na granicach części są zapisywane w spisie (`przerwa N`) i przywracane przy składaniu, bo DeepL przycina puste linie na początku pliku.

```
python litert-rozdziel/scripts/rozdziel.py "C:\sciezka\KATALOG" [--nadpisz] [--bez-org] [--bez-zip] [--max-fffd 10] [--zachowaj-techniczne] [--tylko-sprzatanie] [--min-ciag 60]
```

## Pominięte akapity

DeepL czasem po cichu pomija akapit (w danych autora ok. 0,6% plików). `litert-rozdziel` porównuje liczbę linii z treścią w oryginale i wyniku, zgłasza numery pominiętych linii oryginału i wstrzymuje kasowanie plików technicznych (`--bez-kontroli-akapitow` wyłącza kontrolę). Procedura naprawy jest w `litert-rozdziel/SKILL.md`.

## Duplikaty

`litert/scripts/duplikaty.py KATALOG [--wzorzec @] [--prog 0.6] [--do-kosza]` wskazuje pliki z wzorcem w nazwie (domyślnie `@`), których treść w co najmniej 60% jest w innym pliku bez wzorca. Domyślnie tylko raport, a z `--do-kosza` takie pliki trafiają do Kosza (Windows). Po usunięciu duplikatów trzeba powtórzyć scalanie.

## Gdy DeepL wpadnie w pętlę

Przy przeciągniętych okrzykach w oryginale ("Daddddyyyy!!!") DeepL czasem generuje setki powtórzonych liter i gubi resztę linii. Kontrola w `litert-rozdziel` to wykrywa (próg `--min-ciag`) i wstrzymuje kasowanie. Procedura naprawy (plik pomocniczy z linii oryginału ze skróconymi przeciągnięciami, tłumaczony w DeepL, a potem podmiana całych linii) jest opisana w `litert-rozdziel/SKILL.md`. Pętlom zapobiega skracanie przeciągniętych liter w tekście wysyłanym do DeepL, które `litert` robi domyślnie (`--bez-skracania` je wyłącza; oryginały zostają bez zmian).

## Kodowanie i polskie znaki

Oba skrypty czytają pliki z automatycznym wykrywaniem kodowania (UTF-16 z BOM, UTF-8 z BOM lub bez; dla angielskich plików źródłowych dalej cp1252, a awaryjnie cp1250), a zapisują zawsze UTF-8 bez BOM z końcami linii LF. Dzięki temu polskie znaki, typograficzne apostrofy i cudzysłowy nie giną po drodze. Skrypty ostrzegają (`UWAGA`), gdy plik nie jest UTF-8, ma uszkodzone znaki (np. `Å‚`, `Ä…`, U+FFFD) albo przetłumaczony plik nie zawiera żadnej polskiej litery.

## Użycie jako skill Claude

Każdy folder (`litert/`, `litert-rozdziel/`) zawiera `SKILL.md` i skrypt w `scripts/`. Skille wywołuje się, podając Claude ścieżkę katalogu, np. "scal C:\...\NAZWA" albo "rozdziel C:\...\NAZWA".

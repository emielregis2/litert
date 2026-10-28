# litert

Dwa skille dla Claude do przygotowania angielskich plików `.txt` do tłumaczenia w DeepL i odtworzenia ich po tłumaczeniu.

```
angielskie pliki .txt
        │  litert            (scalanie, limit 900 kB, znaczniki granic, spis, cięcie długich linii)
        ▼
NazwaKatalogu_all_N.txt  +  NazwaKatalogu_spis_scalenia.txt
        │  tłumaczenie ręczne w aplikacji DeepL (wynik: "... pl.txt" albo zip z DeepL)
        ▼
NazwaKatalogu_all_N pl.txt
        │  litert-rozdziel   (rozcięcie po znacznikach, składanie linii, słownik, czkawka, kontrola, akapity, cięcie tur)
        ▼
Oryginalna Nazwa pl.txt
```

## Typowy przebieg

1. **Scalanie:** `scal C:\...\KATALOG`. Powstają `KATALOG_all_N.txt`, `KATALOG_spis_scalenia.txt` oraz ewentualnie części dużych plików (`Nazwa_N.txt`). Przed wysłaniem do DeepL długie linie są cięte (na zmianach mówcy i do 800 znaków), a przeciągnięte litery skracane.
2. **Tłumaczenie ręcznie w DeepL:** wgrywasz pliki `KATALOG_all_N.txt` i części dużych plików (nie spis i nie duże oryginały), a wyniki zapisujesz w tym samym katalogu z końcówką ` pl` (albo zostawiasz zip z DeepL).
3. **Rozdzielanie:** `rozdziel C:\...\KATALOG`. Powstają pliki `Oryginalna Nazwa pl.txt`: skrypt składa pocięte linie, stosuje słownik poprawek, sprawdza czkawkę DeepL, kontroluje kompletność, przenosi oryginały do podkatalogu `org`, kasuje pliki techniczne (scalenia, spis, części, archiwum `.zip`) i na końcu tnie linie na zmianach mówcy. W katalogu głównym zostają same tłumaczenia.

## litert

Scala pliki `.txt` z katalogu w jak najmniej plików zbiorczych o rozmiarze do 900 000 bajtów.

- **nigdy nie scala wersji przetłumaczonych** (twarda zasada: nazwa kończąca się na `pl`, np. `... pl.txt`, `..._pl.txt`, `... PL.txt`, `... pl (1).txt`; podwójna spacja też; ich kopie też są pomijane); kopie (`..._copy(1).txt`) nie są scalane, ale przed scaleniem są analizowane: nowsza i większa kopia zastępuje oryginał (oryginał trafia do `_zastapione`), pozostałe przypadki trafiają do raportu "do decyzji" (flagi `--tylko-analiza-kopii`, `--nie-zastepuj-kopii`),
- pakuje pliki wg rozmiaru (First Fit Decreasing), w każdym pliku scalenia pliki idą alfabetycznie,
- przed każdym plikiem wstawia znacznik `=====[[N|Nazwa]]=====`,
- tworzy `NazwaKatalogu_spis_scalenia.txt` (numer i nazwa każdego pliku w danym scaleniu oraz plan podziału długich linii),
- pliki większe niż limit nie trafiają do scaleń, tylko są dzielone linia po linii na części `Nazwa_1.txt`, `Nazwa_2.txt`, ...,
- domyślnie tnie linie na zmianach mówcy i na twardym limicie 800 znaków oraz skraca przeciągnięte litery (opis w sekcji "Cięcie linii"),
- niczego nie kasuje: oryginały i przetłumaczone pliki zostają nietknięte (jedyny wyjątek: nowsza i większa kopia `_copy` zastępuje oryginał, a oryginał trafia do `_zastapione`).

```
python litert/scripts/scal.py "C:\sciezka\KATALOG" [--limit 900000] [--nie-zastepuj-kopii] [--tylko-analiza-kopii]
                             [--bez-skracania] [--bez-dzielenia] [--bez-tur] [--bez-narracji] [--limit-linii 800]
```

## litert-rozdziel

Rozdziela przetłumaczone pliki scalenia (`NazwaKatalogu_all_N pl.txt`) na pliki o oryginalnych angielskich nazwach z końcówką ` pl`.

- granice wyznacza wyłącznie numer ze znacznika (nazwa mogła zostać przetłumaczona),
- nazwy plików wynikowych pochodzą ze spisu,
- **domyślnie nadpisuje istniejące pliki wynikowe** (od 2026-10-28), ale najpierw zapisuje ich stare wersje w zipie `Downloads\<Katalog>_przed_nadpisaniem_<data>.zip`; flaga `--nie-nadpisuj` przywraca dawne zachowanie (pomijanie i zgłaszanie),
- zgłasza brakujące, zdublowane i nadmiarowe znaczniki; nie zapisuje pliku, który mógłby się skleić z sąsiednim,
- brakujące przetłumaczone pliki wypakowuje sam z archiwum `.zip` z DeepL leżącego w katalogu (tylko brakujące, bez nadpisywania; wyłączane flagą `--bez-zip`),
- pojedyncze uszkodzone znaki U+FFFD zwrócone przez DeepL usuwa z wyniku automatycznie, z raportem (sekcja `NAPRAWA U+FFFD` i plik `..._raport_naprawy.txt`); do `--max-fffd` na plik (domyślnie 10), więcej to ostrzeżenie,
- składa z powrotem linie pocięte przy scalaniu, także gdy DeepL skleił końcówki zdań, rozdzielił linię albo dołożył puste linie (sekcje poniżej),
- stosuje słownik poprawek DeepL i krok czkawki (podwojone słowa, błędy na wielkich literach),
- składa twardo zawinięte linie w akapity (sekcja "Twardo zawinięte linie → akapity"),
- po udanym i kompletnym rozdzieleniu po kontroli kompletności (wyniki zapisane, niepuste, bez znaczników, bez pętli DeepL, nieucięte) przenosi oryginały do podkatalogu `org` i **kasuje pliki techniczne** (pliki scalenia i ich tłumaczenia, spis, części dużych plików i ich tłumaczenia, archiwum `.zip` zawierające wyłącznie tłumaczenia tej partii); wyłączane flagą `--bez-org`, a `--zachowaj-techniczne` przenosi je do `org` zamiast kasować,
- na samym końcu tnie linie tłumaczenia na zmianach mówcy (sekcja "Cięcie linii"),
- składa przetłumaczone części dużych plików (`Nazwa_1 pl.txt`, `Nazwa_2 pl.txt`, ...) w jeden `Nazwa pl.txt` według sekcji "Pliki podzielone" ze spisu; gdy brakuje którejś części, nie składa pliku i to zgłasza. Puste linie na granicach części są zapisywane w spisie (`przerwa N`) i przywracane przy składaniu, bo DeepL przycina puste linie na początku pliku.

```
python litert-rozdziel/scripts/rozdziel.py "C:\sciezka\KATALOG" [--nie-nadpisuj] [--bez-org] [--bez-zip] [--max-fffd 10] [--zachowaj-techniczne]
                                          [--tylko-sprzatanie] [--min-ciag 60] [--bez-poprawek] [--bez-czkawki] [--czkawka-raport]
                                          [--bez-tur-pl] [--bez-narracji-pl] [--tury-sep auto|pusta|nowa] [--tylko-tury-pl [--sucho] [--kopia plik.zip]]
                                          [--bez-akapitow] [--akapity-wymus] [--tylko-akapity [--sucho] [--kopia plik.zip]]
```

## Cięcie linii (przed i po tłumaczeniu)

DeepL traci jakość na bardzo długich liniach (podwojone słowa, rozsypane „się", pętle). Dlatego:

- **Przed tłumaczeniem** `litert` domyślnie tnie linie: na zmianach mówcy (granica między cudzysłowami `” “` oraz po `.` `!` `?` tuż przed cytatem otwierającym) i na twardym limicie 800 znaków (`--limit-linii`), a przeciągnięte litery (5 i więcej takich samych znaków) skraca do 4. Wyłączniki: `--bez-dzielenia`, `--bez-tur`, `--bez-narracji`, `--bez-skracania`. Pozostałe parametry: `--prog-linii`, `--min-odcinek`, `--prog-tury`, `--ciecie-po`.
- **Po tłumaczeniu** `litert-rozdziel` składa linie z powrotem według planu ze spisu, a na samym końcu (po kontroli i sprzątaniu) tnie je na zmianach mówcy, żeby w gotowych plikach wypowiedzi stały w osobnych liniach. Lista cięć trafia do `org\KATALOG_tury_pl.txt`. Flagi: `--bez-tur-pl`, `--bez-narracji-pl`, `--tury-sep` (separator: pusta linia albo nowa linia, domyślnie zależnie od pliku), `--tylko-tury-pl` (samo cięcie istniejących tłumaczeń, z `--sucho` i `--kopia`).
- Istniejące tłumaczenia z pętlami lub błędami w wybranych liniach naprawia `litert-rozdziel/scripts/dlugie_linie.py KATALOG --przygotuj | --zastosuj` (opcje `--petle`, `--linie`, `--pliki`). Naprawy trzeba robić **przed** cięciem tur, bo narzędzie mapuje linie 1:1 do oryginału.

## Czkawka DeepL: podwojone słowa i błędy na wielkich literach

Podwojone słowo (`się się`) bywa błędem DeepL, ale bywa też poprawne, więc `litert-rozdziel` klasyfikuje je po oryginale angielskim (`scripts/czkawka_przeglad.py`):

- **uzasadnione:** powtórzenie jest w oryginale (`yeah, yeah` → `tak tak`, onomatopeje, nazwy), polski idiom (`tuż tuż`), zaimek (`jej jej`, `na nie nie patrzeć`) albo poprawna konstrukcja (`i i tak`, `w w pełni`, `na na wpół`),
- **autopoprawka:** tylko gdy oryginał nie ma powtórzenia, słowo jest na krótkiej liście (`się`, `tak`, `że`, `do`, `jak`) i układ linii jest zgodny 1:1,
- **do przeglądu:** reszta podejrzanych oraz pętle 3 i więcej powtórzeń (tylko raport, bez autopoprawki).

Druga kontrola dotyczy linii oryginału pisanych wielkimi literami (krzyki), w których DeepL potrafi wygenerować nonsens, pętlę albo bardzo długą serię jednego znaku. Wynik to linia `CZKAWKA:` w konsoli z kontekstem PL i EN oraz pełna lista w `KATALOG_raport_naprawy.txt`. Krok niczego nie blokuje (`--czkawka-raport` tylko raportuje, `--bez-czkawki` go wyłącza).

Ten sam przegląd dla istniejących tłumaczeń: `python litert-rozdziel/scripts/czkawka_przeglad.py KATALOG [--korzen KORZEN [--wszystkie]] [--csv plik] [--md plik] [--napraw [--kopia plik.zip]]`. Dla katalogów po cięciu tur wyrównuje tłumaczenie do oryginału po długościach linii; katalogi bez `org` (`--wszystkie`) klasyfikuje tylko po słowie.

## Raport tłumaczeń katalogu

Na końcu pracy nad katalogiem `litert-rozdziel` zapisuje w nim plik `Raport tłumaczeń katalogu <NAZWA>.md` (`scripts/raport_katalogu.py`): podsumowanie wskaźników (liczba plików, zgodność układu linii z oryginałem, cięcia tur, akapity, podwojone słowa, resztki błędów słownika, linie możliwie nieprzetłumaczone), przebieg (słownik, czkawka, naprawy U+FFFD, kopia nadpisanych wyników, ostrzeżenia), sekcję poprawek ręcznych (z pliku `<Katalog>_poprawki_reczne.txt`), listę plików z flagami i tabelę wszystkich plików. Flagi: `--bez-raportu`, `--tylko-raport` (ponowne wygenerowanie dla istniejących tłumaczeń).

## Twardo zawinięte linie → akapity

Część tekstów źródłowych ma linie „twardo zawinięte" na ok. 60–90 znaków, a akapity oddzielone pustymi liniami. DeepL zachowuje ten układ 1:1, więc w tłumaczeniu zdania są porwane na krótkie linie, a czytnik (np. Speechify) robi pauzę na każdym końcu linii. `litert-rozdziel` składa je w akapity (`scripts/akapity.py`): po kontroli i sprzątaniu, **przed** cięciem tur.

- **Wykrywanie (per plik):** blok (ciąg niepustych linii) jest zawinięty, gdy ma co najmniej 2 linie, żadna nie jest dłuższa niż 140 znaków, większość ma co najmniej 35 znaków, przynajmniej jedna nie kończy się znakiem końca zdania, a co najmniej 1/3 zaczyna się od małej litery (odróżnia to zawinięty tekst od wierszy). Plik jest zawinięty, gdy takie bloki zawierają co najmniej **30%** niepustych linii. W plikach częściowo zawiniętych łączone są tylko zawinięte bloki.
- **Łączenie:** jedną spacją (bez spacji przed `, . ; : ! ? ) ” »` i po łączniku przed małą literą). Nie łączy po końcu zdania, gdy następna linia zaczyna się wypowiedzią (`„` lub pauzą dialogową), ani pełnych akapitów (linie powyżej 140 znaków). Akapit powyżej 4000 znaków jest dzielony na końcach zdań.
- **Weryfikacja:** tekst bez białych znaków musi pozostać identyczny, drugi przebieg niczego nie zmienia, a raport trafia do `org\KATALOG_akapity.txt`.
- **Flagi:** `--bez-akapitow` (wyłącza krok), `--akapity-wymus` (także pliki poniżej progu), `--tylko-akapity [--sucho] [--kopia plik.zip]` (istniejące tłumaczenia, także w katalogach bez `org`).
- Po łączeniu cięcie tur nadal dzieli akapity na wypowiedzi, więc dialogi zachowują naturalną pauzę.

W danych autora zawiniętych było 45 z 6 611 tłumaczeń (11 katalogów), np. `Another Lazy, Wasted Saturday Afternoon`: 926 → 220 niepustych linii, mediana długości linii 57 → 144 znaki.

## Pominięte akapity

DeepL czasem po cichu pomija akapit (w danych autora ok. 0,6% plików). `litert-rozdziel` porównuje liczbę linii z treścią w oryginale i wyniku, zgłasza numery pominiętych linii oryginału i wstrzymuje kasowanie plików technicznych (`--bez-kontroli-akapitow` wyłącza kontrolę). Procedura naprawy jest w `litert-rozdziel/SKILL.md`.

## Końcówki zdań, rozdzielone linie i puste linie

Autor czasem zawija zdanie w połowie, więc końcówka (`...fell asleep soon` / `after.`) stoi w osobnej krótkiej linii, a DeepL zwykle skleja ją z poprzednią linią. Treść zostaje, ubywa jednej linii. Bywa też odwrotnie: DeepL rozdziela jedną linię na dwie albo dokłada lub usuwa puste linie. `rozdziel` rozpoznaje te przypadki (dopasowanie po długościach kawałków z dokładnym podziałem jak w `scal.py` i z układem pustych linii), składa długie linie mimo nich, **przywraca układ pustych linii z oryginału** i traktuje doklejone końcówki jako informację, a nie blokadę. Prawdziwe braki (dłuższa linia lub poprzednia kończy się kropką) nadal wstrzymują sprzątanie.

## Uszkodzone kodowanie cudzysłowów

Niektóre stare pliki mają cudzysłowy i apostrofy zapisane osobnymi bajtami (`D4`, `D3`) z uszkodzonym następnym znakiem. `scal.py` to wykrywa i ostrzega, a `litert/scripts/napraw_kodowanie.py KATALOG [--zapisz]` naprawia (domyślnie tylko raport; stary oryginał trafia do `_zastapione`). Po naprawie trzeba powtórzyć scalanie.

## Słownik poprawek DeepL

`litert-rozdziel/poprawki_deepl.txt` (`błędna => poprawna`) zawiera systematyczne błędy DeepL (np. `polizaj` → `poliż`). `rozdziel` stosuje je automatycznie przy zapisie wyników, a `rozdziel KATALOG --tylko-poprawki [--sucho]` poprawia istniejące tłumaczenia. Reguły dotyczą błędów typu „nieistniejące słowo"; formy, które istnieją w języku, ale są złe w kontekście, dopisuje się dopiero na zgłoszenie. Kandydatów na nowe reguły znajduje `litert-rozdziel/scripts/kandydaci_slownika.py KATALOG` (słowa spoza słownika `pl_PL`, domyślnie tylko formy rozkazujące i `-zili`; pełny skan dużego zbioru trwa ok. 10 minut).

## Duplikaty

`litert/scripts/duplikaty.py KATALOG [--wzorzec @] [--prog 0.6] [--do-kosza]` wskazuje pliki z wzorcem w nazwie (domyślnie `@`), których treść w co najmniej 60% jest w innym pliku bez wzorca. Domyślnie tylko raport, a z `--do-kosza` takie pliki trafiają do Kosza (Windows). Po usunięciu duplikatów trzeba powtórzyć scalanie.

## Gdy DeepL wpadnie w pętlę

Przy przeciągniętych okrzykach w oryginale ("Daddddyyyy!!!") DeepL czasem generuje setki powtórzonych liter i gubi resztę linii. Kontrola w `litert-rozdziel` to wykrywa (próg `--min-ciag`; wykrywa też pętle całych słów) i wstrzymuje kasowanie. Krótkie linie poprawia się ręcznie na podstawie oryginału (z kopią zapasową i sprawdzeniem, że zmienia się tylko ta linia), a dłuższe przez plik pomocniczy z linii oryginału ze skróconymi przeciągnięciami, tłumaczony w DeepL, i podmianę całych linii (`dlugie_linie.py --petle`). Po naprawie `rozdziel KATALOG --tylko-sprzatanie` kończy kontrolę, sprzątanie i cięcie tur. Procedura jest opisana w `litert-rozdziel/SKILL.md`. Pętlom zapobiega skracanie przeciągniętych liter w tekście wysyłanym do DeepL, które `litert` robi domyślnie (`--bez-skracania` je wyłącza; oryginały zostają bez zmian).

## Kodowanie i polskie znaki

Oba skrypty czytają pliki z automatycznym wykrywaniem kodowania (UTF-16 z BOM, UTF-8 z BOM lub bez; dla angielskich plików źródłowych dalej cp1252, a awaryjnie cp1250), a zapisują zawsze UTF-8 bez BOM z końcami linii LF. Dzięki temu polskie znaki, typograficzne apostrofy i cudzysłowy nie giną po drodze. Skrypty ostrzegają (`UWAGA`), gdy plik nie jest UTF-8, ma uszkodzone znaki (np. `Å‚`, `Ä…`, U+FFFD) albo przetłumaczony plik nie zawiera żadnej polskiej litery.

## Użycie jako skill Claude

Każdy folder (`litert/`, `litert-rozdziel/`) zawiera `SKILL.md` i skrypty w `scripts/`. Skille wywołuje się, podając Claude ścieżkę katalogu, np. "scal C:\...\NAZWA" albo "rozdziel C:\...\NAZWA". Po zmianie kodu trzeba przebudować paczki `.skill` i zapisać je w Claude (Save skill); nowa wersja pojawia się w następnej sesji.

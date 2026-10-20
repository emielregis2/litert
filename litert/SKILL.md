---
name: litert
description: Scalanie plików .txt z katalogu użytkownika (Darka) w pliki zbiorcze NazwaKatalogu_all_1.txt, _2.txt itd. z limitem 900 kB, w kolejności alfabetycznej, ze znacznikami granic [[numer|nazwa]] przed każdym plikiem, z pominięciem wersji "pl" i kopii "_copy"; pliki większe niż 900 kB są dzielone linia po linii na części Nazwa_1.txt, Nazwa_2.txt i nie trafiają do scaleń. Używaj ZAWSZE, gdy Darek podaje ścieżkę katalogu (np. C:\Users\dariu\Dropbox\Wymina\NAZWA) i prosi o "scal", "scalenie", "zrób to samo dla katalogu", "powtórz scalanie", "zmieniłem jeden z plików", albo wspomina skill "litert" — nawet jeśli nie wymienia wszystkich zasad.
---

# litert — scalanie plików .txt z katalogu

Skill powtarza dokładnie procedurę ustaloną z Darkiem na katalogach `WALTER18`, `AverageBobby`, `True_Motherfucker`, `LOVINGFEELING23` (katalogi w `C:\Users\dariu\Dropbox\Wymina\`).

## Zasady (ustalone, nie pytaj o nie ponownie)

1. **Które pliki:** tylko oryginały `.txt` z katalogu (bez podkatalogów). Pomijamy:
   - pliki, których nazwa (przed `.txt`) kończy się na ` pl` (wersje tłumaczone, np. `Dad's Request pl.txt`; uwaga na podwójną spację, np. `Eric's Mom  pl.txt`),
   - kopie z `_copy(` w nazwie (np. `..._copy(1).txt`, powstają przy zapisie przez Dropbox/edytor),
   - własne pliki scalenia (`NazwaKatalogu_all*.txt`) i plik spisu (`NazwaKatalogu_spis_scalenia.txt`).
2. **Kolejność:** wewnątrz każdego pliku scalenia pliki idą alfabetycznie (bez rozróżniania wielkości liter). O przydziale do konkretnego pliku scalenia decyduje jednak rozmiar, nie alfabet (patrz pkt 4).
3. **Znaczniki granic (po to, by po tłumaczeniu w DeepL dało się rozdzielić tekst z powrotem na oryginały):** przed treścią każdego pliku stoi linia `=====[[N|Nazwa]]=====` i pusta linia. N to numer pliku w alfabetycznej liście wszystkich scalanych oryginałów w katalogu (numeracja ciągła przez wszystkie pliki scalenia), Nazwa to nazwa oryginału bez `.txt` (znaki `[ ] |` zamieniane na spację). **Rozdzielanie opiera się wyłącznie na numerze**, bo DeepL może przetłumaczyć nazwę. Znacznik wlicza się do rozmiaru pliku scalenia. Między plikami jest jedna pusta linia.
4. **Limit i minimalizacja liczby plików:** plik scalenia ≤ **900 000 bajtów** (UTF-8). Cel: jak najmniej plików scalenia i jak największe wypełnienie limitu. Skrypt pakuje pliki wg rozmiaru (First Fit Decreasing, w razie potrzeby ulepszane losowymi permutacjami, aż do dolnej granicy: suma rozmiarów / limit). Alfabet NIE decyduje o przydziale do pliku scalenia. **Nigdy nie przecinamy pojedynczego pliku** między plikami scalenia. Pliki scalenia są numerowane wg pierwszej (alfabetycznie) nazwy w nich zawartej.
5. **Nazwy wyników:** `<NazwaKatalogu>_all_1.txt`, `_all_2.txt`, … zapisywane w tym samym katalogu. Jeśli całość mieści się w limicie, jeden plik bez numeru: `<NazwaKatalogu>_all.txt`.
6. **Spis scalenia (ZAWSZE):** oprócz plików scalenia powstaje `NazwaKatalogu_spis_scalenia.txt` w tym samym katalogu. Zawiera, pod nazwą każdego pliku scalenia, listę oryginalnych nazw plików w nim zawartych w formacie `    N. Nazwa.txt` (alfabetycznie, tak jak w pliku scalenia, z numerem N ze znacznika). Spis NIE jest tłumaczony i jest podstawą do rozdzielania po tłumaczeniu (skill litert-rozdziel). Przy powtórnym scalaniu spis jest nadpisywany, a sam nie jest nigdy scalany.
7. **Pliki większe niż limit (> 900 000 bajtów):** NIE trafiają do plików scalenia. Są dzielone **linia po linii** (żadna linia nie jest przecinana) na części o zbliżonej wielkości, każda ≤ 900 000 bajtów. Części zapisywane są w tym samym katalogu jako `OryginalnaNazwa_1.txt`, `OryginalnaNazwa_2.txt` itd. (nazwa oryginału bez `.txt` + `_N.txt`). Liczba części to minimum potrzebne, a ich rozmiary są wyrównywane. Oryginał zostaje nietknięty. Dotyczy tylko oryginałów, więc plików `pl` i `_copy` nie dzielimy. Części nie są scalane, a są wymienione w spisie w sekcji "Pliki podzielone (nie scalane)". Przy powtórnym uruchomieniu skrypt rozpoznaje własne części (`Nazwa_N.txt`, gdy istnieje `Nazwa.txt`), nie traktuje ich jak oryginałów i nadpisuje je. Jeśli oryginał przestał być duży, stare części zostają i skrypt tylko ostrzega. Części wgrywasz do DeepL osobno, a po tłumaczeniu skleja je skill `litert-rozdziel` w `OryginalnaNazwa pl.txt`.
8. **Kodowanie:** wejście UTF-8 (z BOM lub bez), awaryjnie cp1250; wyjście UTF-8, końce linii `\n`.
9. **Oryginałów nie ruszamy ani nie kasujemy.** Skrypt kasuje i nadpisuje tylko własne pliki `NazwaKatalogu_all.txt` / `NazwaKatalogu_all_N.txt`, spis i własne części dużych plików. **Przetłumaczonych plików `NazwaKatalogu_all_N pl.txt` nigdy nie rusza.** Nie usuwaj kopii `_copy(1)` użytkownika bez wyraźnego polecenia.

## Procedura

1. Wylistuj katalog (`mcp__Desktop_Commander__list_directory`), aby zobaczyć pliki. Jeśli trzeba, najpierw `tool_search` po "Desktop Commander start_process".
2. Uruchom skrypt `scripts/scal.py` na komputerze Darka przez `start_process`:
   - zapisz treść `scripts/scal.py` do pliku tymczasowego na dysku Darka (np. `write_file` do `%TEMP%\litert_scal.py`) i wywołaj:
     `python "%TEMP%\litert_scal.py" "C:\Users\dariu\Dropbox\Wymina\NAZWA"`
   - albo wklej ten sam kod jako `python -c "..."` (tak robiono dotąd).
3. **Treści plików nie czytaj ani nie analizuj.** To operacja mechaniczna, skrypt wypisuje tylko nazwy i rozmiary.
4. Podsumuj w tabeli (i wspomnij o pliku spisu): nazwa pliku scalenia, rozmiar (kB) i wypełnienie limitu, liczba plików i ich nazwy. Podaj też, ile plików scalenia wynosi dolna granica (suma/limit). Osobno wymień pliki podzielone i ich części. Zaznacz, które pliki pominięto (`pl`, `_copy`).

## Powtórne scalanie ("zmieniłem jeden z plików")

Uruchom skrypt jeszcze raz na tym samym katalogu. W podsumowaniu wskaż, który plik się zmienił, porównując rozmiary z poprzednim uruchomieniem. Jeśli w katalogu pojawił się nowy plik (np. `_copy(1)`), napisz o tym wprost.

## Uwagi

- Gdy w katalogu są dwie podobne wersje tego samego tytułu (np. `X.txt` i `X by autor.txt`), scal obie i tylko wspomnij o tym; nie decyduj za Darka, która jest zbędna.
- Język komunikacji: polski.

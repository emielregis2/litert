---
name: litert-rozdziel
description: Rozdziela przetłumaczone w DeepL pliki scalenia (NazwaKatalogu_all_1 pl.txt itd.) z powrotem na osobne pliki o oryginalnych angielskich nazwach z końcówką " pl" (np. Dad's Request pl.txt), na podstawie znaczników [[numer|nazwa]] i pliku spisu NazwaKatalogu_spis_scalenia.txt utworzonych przez skill litert. Używaj ZAWSZE, gdy Darek prosi o "rozdziel", "rozetnij", "podziel przetłumaczone pliki", "odtwórz pliki po tłumaczeniu", "pliki pl po DeepL", albo podaje katalog z przetłumaczonymi plikami scalenia — nawet jeśli nie wspomina o skillu.
---

# litert-rozdziel — rozdzielanie przetłumaczonych plików scalenia

Dopełnienie skilla `litert`. Cały proces Darka: angielskie pliki → scalenie (`litert`, limit 900 kB) → tłumaczenie w DeepL na polski (wyniki z końcówką ` pl`) → **rozdzielenie z powrotem na oryginalne pliki (ten skill)**.

## Wymagania wejściowe (w katalogu, np. `C:\Users\dariu\Dropbox\Wymina\NAZWA`)

- `NazwaKatalogu_spis_scalenia.txt` — spis z `litert` (NIE tłumaczony), z liniami `    N. Nazwa.txt` pod nazwami plików scalenia.
- Przetłumaczone pliki scalenia: `NazwaKatalogu_all_1 pl.txt`, `_all_2 pl.txt`, … (lub `NazwaKatalogu_all pl.txt`, gdy scalenie było jedno). Nazwa = nazwa pliku scalenia + ` pl` przed `.txt`.
- Jeśli w katalogu były pliki > 900 kB, w spisie jest sekcja "Pliki podzielone (nie scalane)", a do DeepL wgrywasz też ich części `Nazwa_1.txt`, `Nazwa_2.txt`, … Przetłumaczone części mają nazwy `Nazwa_1 pl.txt`, `Nazwa_2 pl.txt`, …
- W przetłumaczonych plikach scalenia znaczniki `=====[[N|Nazwa]]=====`. **Liczy się tylko numer N**; nazwa w znaczniku mogła zostać przetłumaczona i jest ignorowana.

## Zasady

1. Każdy plik wynikowy dostaje **oryginalną angielską nazwę ze spisu + ` pl`**, np. spis: `7. Dad's Request.txt` → `Dad's Request pl.txt`. Zapis: UTF-8, końce linii `\n`, treść bez znacznika.
2. **Nie nadpisujemy istniejących plików.** Jeśli `X pl.txt` już istnieje, pomijamy go i zgłaszamy; nadpisanie tylko na wyraźne polecenie Darka (flaga `--nadpisz`).
3. Skrypt **weryfikuje**: czy istnieją wszystkie przetłumaczone pliki scalenia, czy każdy numer ze spisu ma znacznik, czy nie ma nadmiarowych lub zdublowanych znaczników i czy przed pierwszym znacznikiem nie ma tekstu. Pliku, którego znacznika brakuje, NIE zgadujemy: zgłaszamy go w podsumowaniu.
4. Niczego nie kasujemy i nie ruszamy plików scalenia, spisu ani oryginałów. Treści tłumaczeń nie czytaj ani nie analizuj, to operacja mechaniczna.
5. **Składanie części dużych plików:** dla każdego pliku z sekcji "Pliki podzielone" skrypt skleja przetłumaczone części (`Nazwa_1 pl.txt` + `Nazwa_2 pl.txt` + …, w kolejności ze spisu) w jeden plik `Nazwa pl.txt`. Jeśli brakuje którejkolwiek przetłumaczonej części, pliku NIE składa i zgłasza, których części brakuje. Przetłumaczone części zostają na dysku (niczego nie kasujemy). Istniejącego `Nazwa pl.txt` nie nadpisuje bez `--nadpisz`.
6. **Porządkowanie do `org` (po udanym rozdzieleniu):** gdy wszystko jest kompletne, czyli każdy numer ze spisu ma plik wynikowy `... pl.txt`, wszystkie przetłumaczone pliki scalenia istnieją i skrypt nie zgłosił żadnych ostrzeżeń, skrypt tworzy podkatalog `org` i **przenosi do niego wszystko poza wynikami**: angielskie oryginały, pliki scalenia (`NazwaKatalogu_all_N.txt`) i ich tłumaczenia (`..._all_N pl.txt`), części dużych plików (z ich tłumaczeniami i oryginałem) oraz spis. W katalogu zostają tylko wyniki `Oryginalna Nazwa pl.txt` (i pliki niezwiązane ze scaleniem, np. kopie `_copy`). Przy jakimkolwiek ostrzeżeniu albo brakującym wyniku NIE przenosi niczego i mówi dlaczego. Pliki są tylko przenoszone (nic nie kasujemy), a jeśli taki plik już jest w `org`, nie nadpisujemy go i zgłaszamy to. Wyłączenie: flaga `--bez-org`. Po przeniesieniu spis jest w `org`, więc ponowne rozdzielenie lub scalenie wymaga przeniesienia plików z powrotem do katalogu (skrypt podpowiada to w komunikacie).
7. Pliki z końcówką ` pl` są pomijane przez skill `litert` przy kolejnym scalaniu, więc wyniki nie wejdą w pętlę.

## Procedura

1. Wylistuj katalog (`mcp__Desktop_Commander__list_directory`) i sprawdź, czy są spis oraz pliki `... pl.txt`. Jeśli czegoś brakuje, powiedz czego.
2. Uruchom skrypt `scripts/rozdziel.py` na komputerze Darka przez `start_process` (zapisz go np. do `%TEMP%\litert_rozdziel.py`):
   `python "%TEMP%\litert_rozdziel.py" "C:\Users\dariu\Dropbox\Wymina\NAZWA"`
3. Podsumuj: czy pliki zostały przeniesione do `org` (i ilu), ile plików utworzono (osobno: rozdzielone ze scaleń i złożone z części), które pominięto i wszystkie linie `UWAGA`. Przy brakach wyjaśnij, co zrobić (np. ponownie przetłumaczyć dany plik scalenia albo sprawdzić, czy DeepL nie zmienił znaczników).

## Kodowanie i polskie znaki

Przetłumaczone pliki zawierają polskie znaki diakrytyczne (ą ć ę ł ń ó ś ź ż). Skrypt czyta pliki `pl` z automatycznym wykrywaniem kodowania (UTF-16 z BOM → UTF-8 z BOM lub bez → awaryjnie cp1250), a wyniki zapisuje zawsze jako **UTF-8 bez BOM**, końce linii `\n`. Wypisuje `UWAGA`, gdy:
- plik `pl` nie jest UTF-8 (odczytano jako cp1250),
- wykryto typowe ślady zepsutych znaków (np. `Å‚`, `Ä…`, `Ăł`, znak zastępczy U+FFFD),
- w pliku nie ma żadnego polskiego znaku (tłumaczenie mogło się nie udać albo znaki zostały wycięte).

Przy takim ostrzeżeniu NIE naprawiaj tekstu "na oko". Poproś Darka o ponowne zapisanie/pobranie tłumaczenia z DeepL jako UTF-8 i powtórz rozdzielanie z `--nadpisz`.

## Gdy DeepL uszkodzi znacznik

Wyrażenie rozpoznające tolerancyjnie traktuje różne znaki `=`, spacje i kreski wokół `[[N|...]]`. Jeśli numeru nie da się odczytać, skrypt zgłasza brak znacznika dla konkretnego numeru i nazwy. Nie próbuj wtedy dzielić po tytułach, bo po tłumaczeniu są po polsku.

## Uwagi

- Język komunikacji: polski.

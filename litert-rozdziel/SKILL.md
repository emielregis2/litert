---
name: litert-rozdziel
description: Rozdziela przetłumaczone w DeepL pliki scalenia (NazwaKatalogu_all_1 pl.txt itd.) z powrotem na osobne pliki o oryginalnych angielskich nazwach z końcówką " pl" (np. Dad's Request pl.txt), na podstawie znaczników [[numer|nazwa]] i pliku spisu NazwaKatalogu_spis_scalenia.txt utworzonych przez skill litert. Używaj ZAWSZE, gdy Darek prosi o "rozdziel", "rozetnij", "podziel przetłumaczone pliki", "odtwórz pliki po tłumaczeniu", "pliki pl po DeepL", albo podaje katalog z przetłumaczonymi plikami scalenia — nawet jeśli nie wspomina o skillu.
---

# litert-rozdziel — rozdzielanie przetłumaczonych plików scalenia

Dopełnienie skilla `litert`. Cały proces Darka: angielskie pliki → scalenie (`litert`, limit 900 kB) → tłumaczenie w DeepL na polski (wyniki z końcówką ` pl`) → **rozdzielenie z powrotem na oryginalne pliki (ten skill)**.

## Wymagania wejściowe (w katalogu, np. `C:\Users\dariu\Dropbox\Wymina\NAZWA`)

- `NazwaKatalogu_spis_scalenia.txt` — spis z `litert` (NIE tłumaczony), z liniami `    N. Nazwa.txt` pod nazwami plików scalenia.
- Przetłumaczone pliki scalenia: `NazwaKatalogu_all_1 pl.txt`, `_all_2 pl.txt`, … (lub `NazwaKatalogu_all pl.txt`, gdy scalenie było jedno). Nazwa = nazwa pliku scalenia + ` pl` przed `.txt`. Jeśli któregoś brakuje, a w katalogu leży archiwum `.zip` z DeepL (np. `DeepL Translations 2026-10-21.zip`), skrypt sam go wypakuje (zasada 7).
- Jeśli w katalogu były pliki > 900 kB, w spisie jest sekcja "Pliki podzielone (nie scalane)", a do DeepL wgrywasz też ich części `Nazwa_1.txt`, `Nazwa_2.txt`, … Przetłumaczone części mają nazwy `Nazwa_1 pl.txt`, `Nazwa_2 pl.txt`, …
- W przetłumaczonych plikach scalenia znaczniki `=====[[N|Nazwa]]=====`. **Liczy się tylko numer N**; nazwa w znaczniku mogła zostać przetłumaczona i jest ignorowana.

## Zasady

1. Każdy plik wynikowy dostaje **oryginalną angielską nazwę ze spisu + ` pl`**, np. spis: `7. Dad's Request.txt` → `Dad's Request pl.txt`. Zapis: UTF-8, końce linii `\n`, treść bez znacznika.
2. **Nie nadpisujemy istniejących plików.** Jeśli `X pl.txt` już istnieje, pomijamy go i zgłaszamy; nadpisanie tylko na wyraźne polecenie Darka (flaga `--nadpisz`).
3. Skrypt **weryfikuje**: czy istnieją wszystkie przetłumaczone pliki scalenia, czy każdy numer ze spisu ma znacznik, czy nie ma nadmiarowych lub zdublowanych znaczników i czy przed pierwszym znacznikiem nie ma tekstu. Pliku, którego znacznika brakuje, NIE zgadujemy: zgłaszamy go w podsumowaniu.
4. Oryginałów nigdy nie kasujemy. Pliki techniczne kasuje wyłącznie sprzątanie po pozytywnej kontroli kompletności (zasada 6). Treści tłumaczeń nie czytaj ani nie analizuj, to operacja mechaniczna.
5. **Składanie części dużych plików:** dla każdego pliku z sekcji "Pliki podzielone" skrypt skleja przetłumaczone części (`Nazwa_1 pl.txt` + `Nazwa_2 pl.txt` + …, w kolejności ze spisu) w jeden plik `Nazwa pl.txt`. Jeśli brakuje którejkolwiek przetłumaczonej części, pliku NIE składa i zgłasza, których części brakuje. Przetłumaczone części są plikami technicznymi i znikają w sprzątaniu (zasada 6). Istniejącego `Nazwa pl.txt` nie nadpisuje bez `--nadpisz`. Liczbę pustych linii między częściami (`przerwa N`) skrypt bierze ze spisu i wstawia ją przy składaniu, więc przerwy między akapitami na granicach części nie giną (starszy spis bez `przerwa` jest składany jak dotąd, bez zmian).
6. **Kontrola kompletności i sprzątanie (po rozdzieleniu):** skrypt najpierw kontroluje, czy WSZYSTKO jest zapisane i przetłumaczone: każdy oryginał ze spisu (także duży, złożony z części) ma wynik `... pl.txt`, który istnieje, nie jest pusty, jest poprawnym UTF-8, nie zawiera znaczników granic, nie ma "pętli" DeepL (podejrzanie długiego ciągu tego samego znaku, którego brak w oryginale, np. setki liter `K`; próg `--min-ciag`, domyślnie 60: w danych Darka przeciągnięte okrzyki mają do ok. 52 znaków, a pętle DeepL zaczynają się od ok. 90 i sięgają ponad tysiąca; ciąg musi być ponad 2 razy dłuższy niż najdłuższy ciąg tego znaku w oryginale) i nie jest podejrzanie mały (poniżej 0,85 rozmiaru oryginału, dla oryginałów ≥ 2 kB, co wskazuje na ucięte tłumaczenie), a skrypt nie zgłosił żadnych ostrzeżeń. Dopiero wtedy: (a) przenosi do `org` angielskie oryginały (z weryfikacją rozmiaru po przeniesieniu), (b) **kasuje pliki techniczne**: pliki scalenia (`NazwaKatalogu_all_N.txt`) i ich tłumaczenia (`..._all_N pl.txt`), części dużych plików i ich tłumaczenia, spis oraz archiwa `.zip` (archiwum tylko wtedy, gdy zawiera wyłącznie tłumaczenia z tej partii; inne zostaje i jest zgłoszone). Plik `NazwaKatalogu_raport_naprawy.txt` (jeśli powstał) trafia do `org`. Kasowania nie wykonuje, jeśli któregokolwiek oryginału nie ma w `org`. Efekt końcowy: **w katalogu głównym wszystkie przetłumaczone pliki, w `org` ich oryginały**. Przy jakimkolwiek ostrzeżeniu, braku wyniku lub nieudanej kontroli NIE przenosi ani nie kasuje niczego i mówi dlaczego. Kasowanie jest po stronie skryptu nieodwracalne (w Dropboksie pliki da się odzyskać z usuniętych), więc o każdym skasowanym pliku wspomnij w podsumowaniu (skrypt wypisuje listę w sekcji `SPRZATANIE`). Flagi: `--zachowaj-techniczne` (pliki techniczne trafiają do `org` zamiast być kasowane), `--bez-org` (wyłącza całe przenoszenie i kasowanie), `--min-ciag N` (próg kontroli pętli, 0 wyłącza ją), `--tylko-sprzatanie` (sama kontrola i sprzątanie katalogu rozdzielonego wcześniej, np. gdy pliki techniczne leżą jeszcze w `org`). Pliki spoza listy technicznej (np. kopie `_copy`, katalog `_zastapione`) nigdy nie są kasowane. Po sprzątaniu ponowne scalenie wymaga przeniesienia oryginałów z `org` z powrotem do katalogu.
7. **Brakujące tłumaczenia z archiwum `.zip` (automatycznie):** przed rozdzielaniem skrypt sprawdza, czy istnieją wszystkie oczekiwane przetłumaczone pliki (pliki scalenia i części dużych plików). Jeśli któregoś brakuje, a w katalogu jest archiwum `.zip` (typowo pobrane z DeepL, które bywa rozpakowane tylko częściowo), wypakowuje **tylko brakujące pliki** o oczekiwanych nazwach (dopasowanie po nazwie, ścieżki z archiwum są ignorowane). Nigdy nie nadpisuje istniejących plików; samo wypakowanie niczego nie kasuje (archiwum usuwa dopiero sprzątanie, zasada 6). Przy kilku archiwach z tym samym plikiem bierze najnowsze. Każde wypakowanie jest wypisane (`ZIP: wypakowano ...`) i trzeba o nim wspomnieć w podsumowaniu. Jeśli pliku nie ma w żadnym archiwum, skrypt to zgłasza i działa dalej jak dotąd (ostrzeżenie o braku). Wyłączenie: `--bez-zip`.
8. **Automatyczne usuwanie pojedynczych znaków U+FFFD z wyniku (z raportem):** DeepL czasem zostawia w tłumaczeniu uszkodzony znak zastępczy U+FFFD (typowo po ciągu powtórzonych liter w okrzykach). Skrypt usuwa takie znaki z tekstu wyniku **w pamięci, przed zapisem**; przetłumaczone pliki źródłowe (`..._all_N pl.txt`, części) pozostają nietknięte jako wierny zapis tego, co zwrócił DeepL. Usuwa je tylko wtedy, gdy w jednym przetłumaczonym pliku jest ich **najwyżej `--max-fffd` (domyślnie 10)**; więcej to prawdopodobnie systemowe uszkodzenie kodowania, więc nic nie usuwa, zgłasza ostrzeżenie i wstrzymuje przenoszenie do `org`. `--max-fffd 0` wyłącza usuwanie. Każde usunięcie jest wypisane w sekcji `NAPRAWA U+FFFD` (plik, linia, numer i nazwa oryginalnego pliku, linia w wyniku, liczba znaków) i dopisane do pliku `NazwaKatalogu_raport_naprawy.txt`, który razem ze źródłami trafia do `org`. Zawsze wspomnij o naprawach w podsumowaniu dla Darka, podając pliki i linie.
9. Pliki z końcówką ` pl` są pomijane przez skill `litert` przy kolejnym scalaniu, więc wyniki nie wejdą w pętlę.

## Procedura

1. Wylistuj katalog (`mcp__Desktop_Commander__list_directory`) i sprawdź, czy są spis oraz pliki `... pl.txt`. Jeśli czegoś brakuje, powiedz czego.
2. Uruchom skrypt `scripts/rozdziel.py` na komputerze Darka przez `start_process` (zapisz go np. do `%TEMP%\litert_rozdziel.py`):
   `python "%TEMP%\litert_rozdziel.py" "C:\Users\dariu\Dropbox\Wymina\NAZWA"`
3. Podsumuj: czy pliki zostały przeniesione do `org` (i ilu), ile plików utworzono (osobno: rozdzielone ze scaleń i złożone z części), które pominięto i wszystkie linie `UWAGA`. Przy brakach wyjaśnij, co zrobić (np. ponownie przetłumaczyć dany plik scalenia albo sprawdzić, czy DeepL nie zmienił znaczników).

## Kodowanie i polskie znaki

Przetłumaczone pliki zawierają polskie znaki diakrytyczne (ą ć ę ł ń ó ś ź ż). Skrypt czyta pliki `pl` z automatycznym wykrywaniem kodowania (UTF-16 z BOM → UTF-8 z BOM lub bez → awaryjnie cp1250), a wyniki zapisuje zawsze jako **UTF-8 bez BOM**, końce linii `\n`. Wypisuje `UWAGA`, gdy:
- plik `pl` nie jest UTF-8 (odczytano jako cp1250),
- wykryto typowe ślady zepsutych znaków (np. `Å‚`, `Ä…`, `Ăł`, znak zastępczy U+FFFD; pojedyncze U+FFFD są jednak najpierw usuwane automatycznie, zasada 8),
- w pliku nie ma żadnego polskiego znaku (tłumaczenie mogło się nie udać albo znaki zostały wycięte).

Przy takim ostrzeżeniu NIE naprawiaj tekstu "na oko". Poproś Darka o ponowne zapisanie/pobranie tłumaczenia z DeepL jako UTF-8 i powtórz rozdzielanie z `--nadpisz`.

## Gdy kontrola zgłasza pętle DeepL (długi ciąg tego samego znaku)

Skrypt zatrzymuje wtedy przenoszenie i kasowanie (pliki techniczne i oryginały zostają na miejscu). Procedura zaakceptowana przez Darka:

1. **Zbadaj każdą pętlę** (tylko liczby i bardzo krótki kontekst, kilkadziesiąt znaków w ascii): plik, linia, znak, długość, czy pętla stoi na końcu linii, ile znaków zostało po niej, jak długa jest linia wyniku bez pętli względem odpowiedniej linii oryginału. Pętla na końcu linii oznacza zwykle, że DeepL **zgubił resztę linii** (stosunek wyraźnie poniżej typowych 1,1–1,2). Pliki o podobnych tytułach bywają dwiema wersjami tego samego tekstu i wtedy pętle powtarzają się w obu.
2. **Zapytaj Darka jednym pytaniem z opcjami:** (a) naprawa pełna, (b) naprawa minimalna, (c) zostawić (`--min-ciag 0`).
   - **(a) pełna:** przygotuj plik pomocniczy `DO_PRZETLUMACZENIA_<Katalog>_linie.txt` w katalogu: oryginalne linie z miejsc pętli, w których ciągi 5 i więcej takich samych znaków są skrócone do 4 (to przeciągnięcia wywołują pętlę), oddzielone pustymi liniami. Darek tłumaczy plik w DeepL (wynik `... pl.txt`), a Ty podmieniasz w wynikach **całe linie** (spacje na początku i końcu linii bierz z oryginału).
   - **(b) minimalna:** zamień pętlę na krótkie przeciągnięcie (5–6 liter) z domkniętym zdaniem lub cudzysłowem, tak jak w oryginale. Zgubionego tekstu nie odtwarzasz.
3. **Przed zapisem sprawdź:** liczba niepustych linii tłumaczenia równa liczbie celów, brak U+FFFD i ciągów 20+ znaków w nowych liniach, stosunek długości tłumaczenia do skróconego oryginału w zakresie 0,8–1,6 (dla krótkich linii mniej niż 1,0 jest normalne, bo ". . ." staje się „…"), a w każdym pliku wyniku zmienia się dokładnie wskazana linia (liczba linii bez zmian). Zapis: UTF-8 bez BOM, końce linii LF. Przy niespełnieniu którejkolwiek kontroli nic nie zapisuj.
4. **Po udanej podmianie** usuń pliki pomocnicze (`DO_PRZETLUMACZENIA_*`) i uruchom `rozdziel` ponownie: wyniki istnieją, więc zostaną pominięte, a kontrola i sprzątanie przejdą.
5. **Zgubionych fragmentów nie tłumacz sam.** Brakujący tekst tłumaczy DeepL przez plik pomocniczy (opcja a).

## Gdy DeepL uszkodzi znacznik

Wyrażenie rozpoznające tolerancyjnie traktuje różne znaki `=`, spacje i kreski wokół `[[N|...]]`. Jeśli numeru nie da się odczytać, skrypt zgłasza brak znacznika dla konkretnego numeru i nazwy. Nie próbuj wtedy dzielić po tytułach, bo po tłumaczeniu są po polsku.

## Uwagi

- Język komunikacji: polski.

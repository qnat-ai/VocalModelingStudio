# Zasady paczek ZIP

Ten plik wyjaśnia, jak traktować paczki projektu.

## Full snapshot
Paczka z dopiskiem `full` zawiera całą strukturę projektu i może być rozpakowana jako nowy projekt PyCharm.

## Patch
Paczka z dopiskiem `patch` zawiera tylko zmienione pliki. Należy ją skopiować na istniejący projekt tej samej wersji bazowej.

## Zalecenie
Przy większej zmianie używaj full snapshot. Przy małej zmianie modułu używaj patch.

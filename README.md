# BLENDER_MCP
Wersja Bendera pod multi channel painting
Multi Painter Channel
Instrukcja użytkownika dla grafika 2D / 3D
Dedykowana kompilacja silnika Blender (Windows)
Ważna informacja na start
Używaj wyłacznie
 ̨
dołaczonej
 ̨
do tej instrukcji, specjalnej wersji Blendera dla systemu
Windows.
Została ona wyposażona w modyfikacje ̨ silnika C++, która umożliwia
jednoczesne nakładanie wielu tekstur (kolor, normalna, roughness itp.) za pomoca ̨ jednego
pociagni
 ̨ ecia
 ̨
pedzla.
 ̨
1. Instalacja wtyczki w Blenderze
Dodatek instalujemy dokładnie tak samo, jak każda ̨ standardowa ̨ wtyczk ̨e:
• Otwórz zmodyfikowana ̨ wersje ̨ Blendera.
• W górnym menu wybierz: Edycja (Edit) → Preferencje (Preferences).
• Przejdź do zakładki Dodatki (Add-ons) i kliknij przycisk Zainstaluj... (Install...) w prawym
górnym rogu.
• Wskaż plik .zip z wtyczka ̨ Multi Painter Channel na dysku i zatwierdź.
• Zaznacz checkbox przy nazwie wtyczki, aby ja ̨ aktywować.
2. Przygotowanie materiału (Shading)
Zanim zaczniesz malować po obiekcie 3D, Twój materiał musi wiedzieć, gdzie zapisywać wyniki:
• Przejdź do zakładki Shading.
• W shaderze obiektu (np. Principled BSDF ) stwórz i podłacz
 ̨ puste tekstury docelowe (np.
teksture ̨ na Kolor, Normalna,
 ̨ Roughness, Metallic).
• Uwaga: Wszystkie docelowe tekstury na obiekcie powinny mieć te same wymiary (np. wszystkie
2048 × 2048 px).
3. Konfiguracja wtyczki i Kanałów
Otwórz widok 3D (3D Viewport) i naciśnij klawisz N na klawiaturze, aby wysunać
 ̨ boczny panel.
Znajdziesz tam zakładk ̨e Multi Channel Painter.
Jak skonfigurować kanały materiałowe?
1. Dodawanie Kanału: Kliknij przycisk dodawania nowego kanału.
nazwe ̨ na własna ̨ – np. "Śruba" lub "Kora".
Zmień domyślna ̨
2. Przypisywanie tekstur źródłowych: W ramach wybranego kanału wskaż pliki tekstur
wzorcowych (np. kolor śruby, mape ̨ normalnych, metaliczność).
3. Kolejne zestawy: Dodaj kolejny kanał (np.
1
odpowiedni komplet tekstur.
"Rdzawa plama") i wskaż dla niego

Złote zasady pracy:
• Ujednolicony rozmiar: Ddbaj o to, aby tekstury źródłowe w kanale oraz tekstury
docelowe na obiekcie miały te same proporcje i rozdzielczość.
• Czytelne nazwy: Nazywaj kanały zgodnie z ich przeznaczeniem – ułatwi to prace ̨ przy
złożonych projektach.

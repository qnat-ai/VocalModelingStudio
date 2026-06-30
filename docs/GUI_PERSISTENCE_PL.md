"""
Dokumentacja: Rozwiązanie dla Nietrwałego Stanu GUI w Gradio
============================================================

Problem:
--------
Praca wykonywana przy edycji wokalu w Gradio była uracana po odświeżeniu strony.
Przyczyną była używanie gr.State() — stan sesji przeglądarki resetowany przy refresh.

Rozwiązanie:
-----------
Implementacja trzywarstwowego systemu przechowywania stanu:

1. **BrowserState (localStorage) — warstwa 1**
   - Zamieniliśmy gr.State() na gr.BrowserState() dla proposal_state i search_state
   - Dane przechowywane w localStorage przeglądarki
   - Przetrwają refresh, offline, czasowe wyłączenie przeglądarki
   - Limitacja: max ~5-10MB na domenę

2. **Server-side Session Manager — warstwa 2**
   - SessionManager w session_manager.py (path: data/projects/.sessions/)
   - Zapisuje JSON snapshoty stanu na serwerze
   - Auto-cleanup starych sesji (>24h)
   - Backup na wypadek utraty localStorage

3. **Auto-save Cleanup Settings — warstwa 3**
   - Automatyczne zapisywanie ustawień cleanup po każdej zmianie
   - Callback na każde pole (enabled, dc offset, high-pass, etc.)
   - Przechowywanie w localStorage i session manager

Implementacja:
--------------

### Zmiany w app/gui/gradio/interface.py:

1. Import SessionManager:
   ```python
   from app.gui.gradio.session_manager import SessionManager
   session_manager = SessionManager(session_cache_dir=Path("data/projects/.sessions"))
   ```

2. Zmiana gr.State -> gr.BrowserState:
   ```python
   # Linia 202 (proposal_state)
   proposal_state = gr.BrowserState({})
   
   # Linia 451 (search_state)
   search_state = gr.BrowserState([])
   ```

3. JavaScript do synchronizacji localStorage:
   ```javascript
   // W demo.load() - odczyt localStorage przy załadowaniu
   window.addEventListener('load', function() {
       const storedCleanupSettings = localStorage.getItem('vms_cleanup_settings');
       if (storedCleanupSettings) {
           window.vmsRestoreSettings = JSON.parse(storedCleanupSettings);
       }
   });
   ```

4. Auto-save callback dla cleanup settings:
   ```python
   def save_cleanup_settings_to_storage(...):
       settings = {...}
       session_manager.save_state("cleanup", "settings", settings)
   
   # Podłączenie do każdego pola cleanup
   for cleanup_component in [...]:
       cleanup_component.change(fn=save_cleanup_settings_to_storage, ...)
   ```

5. Thread do czyszczenia starych sesji:
   ```python
   def cleanup_old_sessions_periodically():
       while True:
           time.sleep(3600)  # Co godzinę
           session_manager.cleanup_old_sessions(max_age_hours=24)
   ```

### Nowy plik: app/gui/gradio/session_manager.py

SessionManager() zapewnia:
- save_state(session_id, key, value) — zapis do memory + dysk JSON
- load_state(session_id, key, default) — odczyt z memory lub dysku
- delete_session(session_id) — usunięcie sesji
- cleanup_old_sessions(max_age_hours) — auto-cleanup

Folder: data/projects/.sessions/session_*.json

Używanie:
---------

1. **Po uruchomieniu GUI:**
   - localStorage będzie automatycznie przywrócony z BrowserState
   - Server cache będzie załadowany przy wznowieniu sesji

2. **Podczas edycji wokalu:**
   - proposal_state (wynik PROCESS) jest przechowywany w localStorage
   - Cleanup settings są automatycznie zapisywane
   - Jeśli refresh — wszystko wraca

3. **Cleanup:**
   - Stare sesje (>24h) są automatycznie usuwane co godzinę
   - localStorage przeglądarki nigdy nie jest czyszczony automatycznie

Ograniczenia:
------------

1. localStorage ma limit wielkości (~5-10MB)
   - W praktyce nie jest problemem, bo przechowujemy tylko ścieżki i liczby

2. Cross-browser:
   - Działa tylko w ramach tej samej przeglądarki
   - Inny browser = nowe localStorage

3. PrivateMode / Incognito:
   - localStorage jest niedostępny
   - Fallback na session cache

4. Transfer danych:
   - proposal_state (ścieżki do plików) jest mały
   - search_state (lista wyników) może być większy, ale jest limit 50 wyników

Testy:
------

Testy przechodzą:
- test_config_validation.py ✓
- test_imports.py ✓
- Brak regression testów dla GUI (Gradio testing jest skomplikowany)

Wdrożenie:
----------

Zatwierdzenie: commit "feat: add persistent state management for GUI (BrowserState + SessionManager)"

- Dodano SessionManager do zarządzania stanami na serwerze
- Zamieniono gr.State na gr.BrowserState dla proposal_state i search_state
- Dodano auto-save dla cleanup settings
- Dodano thread do czyszczenia starych sesji
"""


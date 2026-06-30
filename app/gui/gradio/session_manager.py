"""
Session manager dla GUI Gradio — przechowywanie i przywracanie stanu użytkownika.
Unika utraty pracy z powodu odświeżenia przeglądarki lub rozłączenia.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("vms.gui.session")


class SessionManager:
    """
    Zarządza stanem sesji użytkownika (proposal_state, cleanup settings, search results).
    Przechowuje dane w `.json` na serwerze (backup) i localStorage przeglądarki (speed).
    """

    def __init__(self, session_cache_dir: Path = Path("data/projects/.sessions")):
        """
        Args:
            session_cache_dir: Katalog do przechowywania sesji na serwerze.
        """
        self.session_cache_dir = Path(session_cache_dir)
        self.session_cache_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def get_session_id(self, user_key: Optional[str] = None) -> str:
        """Unika ID sesji (na podstawie user_key lub losowego uniqid)."""
        if user_key:
            return f"session_{user_key}"
        import uuid
        return f"session_{uuid.uuid4().hex[:12]}"

    def save_state(self, session_id: str, key: str, value: Any) -> None:
        """
        Zapisuje stan w sesji (memory) i na dysku (.json).

        Args:
            session_id: ID sesji użytkownika.
            key: Klucz stanu (np. 'proposal_state', 'cleanup_settings').
            value: Wartość do zapisania.
        """
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = {}
            self.sessions[session_id][key] = value

            # Zapis na dysk
            session_file = self.session_cache_dir / f"{session_id}.json"
            try:
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(self.sessions[session_id], f, indent=2, default=str)
                logger.debug(f"Session {session_id} saved to {session_file}")
            except Exception as exc:
                logger.error(f"Failed to save session {session_id}: {exc}")

    def load_state(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Ładuje stan z sesji (memory) lub z dysku.

        Args:
            session_id: ID sesji użytkownika.
            key: Klucz stanu.
            default: Wartość domyślna, jeśli nie znaleziono.

        Returns:
            Wartość stanu lub default.
        """
        with self.lock:
            # Próba z memory
            if session_id in self.sessions and key in self.sessions[session_id]:
                return self.sessions[session_id][key]

            # Próba z dysku
            session_file = self.session_cache_dir / f"{session_id}.json"
            if session_file.exists():
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.sessions[session_id] = data
                    return data.get(key, default)
                except Exception as exc:
                    logger.error(f"Failed to load session {session_id}: {exc}")
            return default

    def delete_session(self, session_id: str) -> None:
        """Usuwa sesję (memory + dysk)."""
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]

            session_file = self.session_cache_dir / f"{session_id}.json"
            if session_file.exists():
                try:
                    session_file.unlink()
                    logger.debug(f"Session {session_id} deleted")
                except Exception as exc:
                    logger.error(f"Failed to delete session {session_id}: {exc}")

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> None:
        """Usuwa sesje starsze niż max_age_hours."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        with self.lock:
            for session_file in self.session_cache_dir.glob("session_*.json"):
                if session_file.stat().st_mtime < cutoff_time:
                    try:
                        session_file.unlink()
                        logger.debug(f"Deleted old session: {session_file.name}")
                    except Exception as exc:
                        logger.error(f"Failed to delete old session: {exc}")


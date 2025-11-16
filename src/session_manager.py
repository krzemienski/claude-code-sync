"""Session Lifecycle Manager for Claude Code"""

import hashlib
import base64
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from src.jsonl_writer import JSONLWriter
from src.jsonl_parser import parse_jsonl_stream


class SessionManager:
    """Manages Claude Code session lifecycle"""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.session_id = str(uuid.uuid4())
        self.project_hash = self._calculate_project_hash()
        self.session_dir = self._get_session_dir()

    def _calculate_project_hash(self) -> str:
        """
        Calculate project hash: base64url(sha256(absolute_path))[:20]

        Returns:
            20-character base64url-encoded hash
        """
        path_bytes = str(self.project_path).encode('utf-8')
        hash_bytes = hashlib.sha256(path_bytes).digest()
        hash_b64 = base64.urlsafe_b64encode(hash_bytes).decode('ascii')
        return hash_b64[:20]

    def _get_session_dir(self) -> Path:
        """
        Get session storage directory: ~/.config/claude/projects/<hash>/

        Returns:
            Path to session directory (created if doesn't exist)
        """
        home = Path.home()
        session_dir = home / '.config' / 'claude' / 'projects' / self.project_hash
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def get_session_file(self, date: datetime | None = None) -> Path:
        """
        Get session JSONL file path for given date.

        Args:
            date: Date for session file (default: today)

        Returns:
            Path to session file: <session_dir>/<YYYY-MM-DD>.jsonl
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime('%Y-%m-%d')
        return self.session_dir / f"{date_str}.jsonl"

    def create_session(self) -> JSONLWriter:
        """
        Create new session and return writer.

        Returns:
            JSONLWriter for session file
        """
        session_file = self.get_session_file()
        writer = JSONLWriter(str(session_file))

        print(f"Session created: {self.session_id}")
        print(f"Project: {self.project_path}")
        print(f"Project hash: {self.project_hash}")
        print(f"Session file: {session_file}")

        return writer

    def resume_session(self, date: datetime | None = None) -> List[Dict[str, Any]]:
        """
        Resume session from JSONL file.

        Args:
            date: Date of session to resume (default: today)

        Returns:
            List of all messages from session
        """
        session_file = self.get_session_file(date)

        if not session_file.exists():
            raise FileNotFoundError(f"No session file found: {session_file}")

        messages = list(parse_jsonl_stream(str(session_file)))
        print(f"Resumed session from: {session_file}")
        print(f"Messages loaded: {len(messages)}")

        return messages

    def list_sessions(self) -> List[Path]:
        """
        List all session files for this project.

        Returns:
            List of session file paths sorted by date (newest first)
        """
        if not self.session_dir.exists():
            return []

        sessions = sorted(
            self.session_dir.glob('*.jsonl'),
            key=lambda p: p.stem,  # Sort by YYYY-MM-DD
            reverse=True  # Newest first
        )

        return sessions

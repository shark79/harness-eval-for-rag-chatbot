"""Central runtime configuration; environment variables override local .env."""
from dataclasses import dataclass
from pathlib import Path
import os

from scripts.dify_api import DifyError, validate_base_url


@dataclass(frozen=True)
class Settings:
    root: Path
    mode: str = 'extractive'
    dify_api_key: str = ''
    dify_base_url: str = 'http://localhost/v1'
    dify_input_name: str = 'ticket_text'
    eval_mode: str = 'offline'
    openai_api_key: str = ''
    port: int = 8080
    host: str = '127.0.0.1'

    @classmethod
    def load(cls, root: Path) -> 'Settings':
        """Load plain key=value configuration without executing shell syntax."""
        values: dict[str, str] = {}
        path = root / '.env'
        if path.is_file():
            for line in path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")
        values.update(os.environ)
        mode = values.get('RAG_MODE', 'extractive')
        eval_mode = values.get('EVAL_MODE', 'offline')
        try:
            base = validate_base_url(values.get('DIFY_API_BASE_URL', 'http://localhost/v1'))
        except DifyError as error:
            raise ValueError(str(error)) from None
        if mode not in {'extractive', 'dify'}:
            raise ValueError('RAG_MODE must be extractive or dify.')
        if eval_mode not in {'offline', 'decisions'}:
            raise ValueError('EVAL_MODE must be offline or decisions.')
        host = values.get('HOST', '127.0.0.1')
        if host not in {'127.0.0.1', '0.0.0.0'}:
            raise ValueError('HOST must be 127.0.0.1 or 0.0.0.0.')
        port = int(values.get('PORT', '8080'))
        if not 1 <= port <= 65535:
            raise ValueError('PORT must be between 1 and 65535.')
        return cls(root, mode, values.get('DIFY_APP_API_KEY', ''), base,
                   values.get('DIFY_INPUT_NAME', 'ticket_text'), eval_mode,
                   values.get('OPENAI_API_KEY', ''), port, host)

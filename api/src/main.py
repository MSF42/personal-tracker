import sys
from pathlib import Path

if __name__ == "__main__":
    # Allow running as `python src/main.py` from any directory
    sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

from src.app import create_app
from src.config.settings import get_settings

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)

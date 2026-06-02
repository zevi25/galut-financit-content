import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from backend.app import create_app
from backend.config import FLASK_PORT

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", FLASK_PORT))
    print(f"\n🚀 השרת עולה על http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

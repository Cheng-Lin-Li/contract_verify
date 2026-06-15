"""Start the contract_verify API server (uvicorn) for the demo.

Run from the repo root:

    python backend/scripts/run_api.py            # http://localhost:8000

Honours HOST / PORT / API_RELOAD env vars. Equivalent to:
    uvicorn app.api.app:create_app --factory --host 0.0.0.0 --port 8000
Requires backend/requirements-3month.txt (fastapi, uvicorn).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
# Ensure the uvicorn auto-reload subprocess can import ``app.*`` too, even if the
# caller didn't set PYTHONPATH=backend.
_pp = os.environ.get("PYTHONPATH", "")
if str(BACKEND) not in _pp.split(os.pathsep):
    os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (str(BACKEND), _pp) if p)


def main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("API_RELOAD", "1") == "1"
    uvicorn.run("app.api.app:create_app", factory=True, host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()

"""Local demo API: force GEORANK_ALLOW_ANONYMOUS_AI and bind 127.0.0.1:8000."""
from __future__ import annotations

import os

os.environ["GEORANK_ALLOW_ANONYMOUS_AI"] = "true"

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)

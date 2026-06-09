#!/bin/bash
set -e
cd /home/hermes/micro-army
source .venv/bin/activate
uv pip install --python .venv/bin/python fastapi uvicorn httpx pydantic prometheus-client pytest 2>&1 | tail -2
PYTHONPATH="$PWD/services/youtube-svc/src:$PWD/shared" python -m pytest services/youtube-svc/tests/ -v 2>&1

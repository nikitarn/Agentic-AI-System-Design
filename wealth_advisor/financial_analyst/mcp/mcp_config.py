import os
import re
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Local Python-based MCP servers (e.g. broker_mock) must be spawned with this
# exact interpreter — a bare "python" on PATH may resolve to one without our
# dependencies installed. mcp_servers.json references it as ${PYTHON_EXECUTABLE}.
os.environ.setdefault("PYTHON_EXECUTABLE", sys.executable)

_CONFIG_PATH = Path(__file__).parent.parent / "mcp_servers.json"


def load_mcp_configs() -> dict:
    """Return mcp_servers dict from mcp_servers.json with ${VAR} env vars resolved."""
    raw = json.loads(_CONFIG_PATH.read_text())
    resolved = re.sub(r"\$\{(\w+)\}", lambda m: os.getenv(m.group(1), ""), json.dumps(raw))
    return json.loads(resolved).get("mcp_servers", {})

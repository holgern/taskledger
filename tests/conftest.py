from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tests create many short-lived Markdown/YAML records under tmp_path.
# Production durability still fsyncs; pytest opts into faster temporary IO.
os.environ.setdefault("TASKLEDGER_TEST_FAST_IO", "1")

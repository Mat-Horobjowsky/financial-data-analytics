import sys
from pathlib import Path

# Ensure the project root (containing report_engine/) is at the front of
# sys.path so it takes precedence over tests/report_engine/ (which has an
# __init__.py and would otherwise shadow the real package).
_root = str(Path(__file__).parent.parent)
if _root in sys.path:
    sys.path.remove(_root)
sys.path.insert(0, _root)

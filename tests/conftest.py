import sys

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `import tewee`
# resolve correctly when running pytest from any directory.
# ---------------------------------------------------------------------------
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sys
from pathlib import Path

# Add backend root to Python path for imports
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

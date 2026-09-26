"""Shared tools resolve the active maintenance directory at runtime."""
from pathlib import Path
import sys
CODE = Path(__file__).resolve().parent
sys.path.insert(0,str(CODE.parent/'maintenance'))
from context import load
REPO, ACTIVE, META = load(writable=True)
VERSION = META['version']
ROOT = ACTIVE/'产物/mac'

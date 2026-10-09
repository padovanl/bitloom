"""Reject missing/duplicate command coverage in the manual testbook."""
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bitloom.commands import ACTIONS

text=(ROOT/'README.testbook.md').read_text()
covered=re.findall(r'\| CMD\d+ / `([^`]+)` \|',text)
expected={action.id for action in ACTIONS}
if set(covered)!=expected or len(covered)!=len(expected):
    raise SystemExit(f'Invalid action coverage. Missing: {expected-set(covered)}; extra: {set(covered)-expected}; duplicates: {len(covered)-len(set(covered))}')
print(f'PASS: all {len(expected)} command-center actions have manual test cases')

import os

# Tests use the default keys, never the keys customised on the machine running them.
os.environ.setdefault("BITLOOM_KEYS", "default")

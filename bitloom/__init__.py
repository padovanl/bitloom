"""Bitloom — a local-first Yocto development cockpit."""
__version__ = "0.0.3"


def archive():
    """The bitloom.pyz this code runs from, or None for a normal installation."""
    from pathlib import Path
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.suffix == ".pyz" and parent.is_file():
            return str(parent)
    return None


def module_command(module: str, *args: str) -> list[str]:
    """The command that runs one of Bitloom's modules in a new process (the build service, a job helper),
    from an installation (python -m) or from the single-file bitloom.pyz alike."""
    import sys
    from pathlib import Path
    packed = archive()
    if packed:
        return [sys.executable, packed, "--run-module", module, *args]
    # The folder Bitloom is imported from, passed explicitly: the Debian package keeps it in /opt/bitloom/lib,
    # outside the interpreter's own path, where "python -m" would not find it.
    root = str(Path(__file__).resolve().parent.parent)
    code = f"import sys,runpy;sys.path.insert(0,{root!r});runpy.run_module({module!r},run_name='__main__',alter_sys=True)"
    return [sys.executable, "-c", code, *args]

"""Release versions must be safe as tags, paths and Debian versions."""
import argparse

import pytest

from tools.build_release import release_version, set_version


@pytest.mark.parametrize('value', ['v1.2.3', '1.2', '01.2.3', '1.2.3rc1', '../evil', '1.2.3;echo x'])
def test_reject_invalid_release_versions(value):
    with pytest.raises(argparse.ArgumentTypeError):
        release_version(value)


def test_version_applied_to_distribution_and_runtime(tmp_path):
    (tmp_path / 'yoctotui').mkdir()
    project = tmp_path / 'pyproject.toml'
    runtime = tmp_path / 'yoctotui/__init__.py'
    project.write_text('[project]\nversion = "0.1.0"\n')
    runtime.write_text('__version__ = "0.1.0"\n')
    set_version(tmp_path, release_version('1.2.3'))
    assert project.read_text() == '[project]\nversion = "1.2.3"\n'
    assert runtime.read_text() == '__version__ = "1.2.3"\n'

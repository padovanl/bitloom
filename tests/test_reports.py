from yoctotui.reports import build_summary, dependencies, download_audit, env_diff, environment


def test_environment_and_diff(tmp_path):
    log = tmp_path / 'env'
    log.write_text('# metadata\nexport CC="gcc"\nMACHINE="qemuarm"\nfunc() {\nignored\n}\n')
    values = environment(log)
    assert values == {'CC': 'gcc', 'MACHINE': 'qemuarm'}
    diff = env_diff(values, {'CC': 'gcc', 'MACHINE': 'qemux86-64'})
    assert 'MACHINE' in diff and 'CC' not in diff


def test_dependency_edges(tmp_path):
    dot = tmp_path / 'tasks.dot'
    dot.write_text('digraph {\n"busybox.do_compile" -> "busybox.do_configure";\n}\n')
    assert dependencies(dot) == [('busybox.do_compile', 'busybox.do_configure')]


def test_build_summary_uses_real_log(tmp_path):
    log = tmp_path / 'build.log'
    log.write_text('Sstate summary: Wanted 12 Local 10\nWARNING: foo\nERROR: Task busybox failed with exit code 1\n')
    summary = build_summary(log)
    assert 'Errors: 1' in summary and 'Warnings: 1' in summary
    assert 'Wanted 12' in summary

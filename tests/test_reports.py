from bitloom.reports import build_summary, dependencies, download_audit, env_diff, environment


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


def test_dependency_context_cycles_and_reverse():
    from bitloom.reports import dependency_context
    result = dependency_context([('image', 'busybox'), ('busybox', 'libc'), ('libc', 'busybox'), ('sdk', 'libc')], 'busybox')
    forward, reverse = result.split('REQUIRED BY')
    assert 'libc' in forward and 'image' in reverse and 'sdk' in reverse
    assert result.count('  libc') == 2


def test_rootfs_inventory_never_extracts_links(tmp_path):
    import io
    import tarfile
    from bitloom.reports import image_contents
    path = tmp_path / 'rootfs.tar.bz2'
    with tarfile.open(path, 'w:bz2') as archive:
        file = tarfile.TarInfo('etc/os-release')
        file.size = 4
        archive.addfile(file, io.BytesIO(b'test'))
        link = tarfile.TarInfo('bin/sh')
        link.type = tarfile.SYMTYPE
        link.linkname = '../../outside'
        archive.addfile(link)
    result = image_contents(path)
    assert 'etc/os-release' in result and 'bin/sh -> ../../outside' in result
    assert not (tmp_path / 'etc').exists()


def test_task_timings_requires_real_timestamp_pairs(tmp_path):
    from bitloom.reports import task_timings
    path = tmp_path / 'kas.log'
    path.write_text('2026-10-10 12:00:00 - NOTE: recipe busybox-1.0-r0: task do_compile: Started\n2026-10-10 12:00:12 - NOTE: recipe busybox-1.0-r0: task do_compile: Succeeded\nNOTE: recipe fake-1.0: task do_compile: Started\nNOTE: recipe fake-1.0: task do_compile: Succeeded\n')
    report = task_timings(path)
    assert '12s' in report and 'Completed pairs: 1' in report and 'fake' not in report

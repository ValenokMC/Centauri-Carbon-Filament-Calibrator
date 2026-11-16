"""The release tooling: the public-safety scanner and the archive check.

These run on any supported Python, without the plugin's mesh libraries.
"""
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import build_release  # noqa: E402
import check_public_safety as safety  # noqa: E402

# Built at run time so this file itself never contains a private address.
PRIVATE_IP = '.'.join(['10', '0', '0', '42'])
PRINT_HOST = '"print' + '_host": "' + PRIVATE_IP + '"'


def rules(findings):
    return {f.rule for f in findings}


def test_scanner_flags_a_private_address_and_passes_clean_text():
    assert 'private-ipv4' in rules(safety.scan_text('host ' + PRIVATE_IP, 'a.md', set()))
    assert safety.scan_text('nozzle 0.4, bed 256 x 256', 'a.md', set()) == []


def test_scanner_reads_inside_a_3mf(tmp_path):
    plate = tmp_path / 'plate.3mf'
    with zipfile.ZipFile(plate, 'w') as z:
        z.writestr('Metadata/project_settings.config', '{' + PRINT_HOST + '}')
    found = safety.scan_file(str(plate), 'plate.3mf', {})
    assert 'print-host' in rules(found)


def make_archive(tmp_path, plugin_text, extra=None):
    name = 'Filament-Lab-vtest-windows'
    archive = tmp_path / (name + '.zip')
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr(name + '/kalibrovka.py', plugin_text)
        for doc in ('README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md'):
            z.writestr(name + '/' + doc, 'text')
        z.writestr(name + '/VERSION', 'test\n')
        for path, text in (extra or {}).items():
            z.writestr(name + '/' + path, text)
    return str(archive)


BUILT = '# [tool.orcaslicer.plugin]\nPAGE = "<html></html>"\n'


def test_verify_accepts_a_built_plugin(tmp_path):
    assert build_release.verify(make_archive(tmp_path, BUILT)) == 0


def test_verify_rejects_an_unbuilt_plugin(tmp_path):
    unbuilt = '# [tool.orcaslicer.plugin]\nPAGE = "@@PAGE@@"\n'
    assert build_release.verify(make_archive(tmp_path, unbuilt)) == 1


def test_verify_rejects_a_private_journal(tmp_path):
    archive = make_archive(tmp_path, BUILT, {'Журнал.csv': 'дата;материал\n'})
    assert build_release.verify(archive) == 1


def test_release_documents_exist():
    missing = [p for p in build_release.INCLUDE_FILES if not os.path.exists(ROOT / p)]
    assert missing == []

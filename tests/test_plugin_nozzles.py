"""Nozzle variants must follow confirmed printer profiles and factor origin."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugin'))
import kalibrovka as plugin


def test_variants_only_for_confirmed_family(tmp_path, monkeypatch):
    data, users = tmp_path / 'data', tmp_path / 'user'
    machines = users / 'default' / 'machine'
    machines.mkdir(parents=True)
    for diameter in ('0.2', '0.4', '0.6', '0.8'):
        (machines / (diameter + '.json')).write_text(json.dumps({
            'name': 'My printer ' + diameter,
            'inherits': 'Example printer ' + diameter + ' nozzle',
        }), encoding='utf-8')
    scales = json.loads((Path(plugin.__file__).parent / 'шкалы.json').read_text(encoding='utf-8'))
    scales.update({'принтер': 'Example printer 0.4 nozzle', 'сопло': 0.4,
                   'сопла': {d: {'pressure_advance': m} for d, m in
                             [('0.2', 3.3), ('0.6', 0.6), ('0.8', 0.42)]}})
    monkeypatch.setattr(plugin, 'ДАННЫЕ', str(data))
    monkeypatch.setattr(plugin, 'ПРЕСЕТЫ', str(users))
    monkeypatch.setattr(plugin, 'DEFAULT_SCALES', scales)
    plugin.записать_базы({'Generic ABS': {'filament_flow_ratio': '0.98'}})
    created = plugin.новая('ABS', 'Example', 'test', база='Generic ABS', принтер='My printer 0.4')
    assert created['сопел'] == 3
    variant = json.loads(Path(plugin._пути_набора('Example test @0.6 nozzle')[0]).read_text(encoding='utf-8'))
    assert variant['compatible_printers'] == ['Example printer 0.6 nozzle', 'My printer 0.6']
    assert plugin.пересчитать_сопла(['Example test'])['сопел'] == 3

    scales['принтер'] = 'Unrelated printer 0.4 nozzle'
    other = plugin.новая('ABS', 'Example', 'other', база='Generic ABS', принтер='My printer 0.4')
    assert other['сопел'] == 0
    assert not Path(plugin._пути_набора('Example other @0.6 nozzle')[0]).exists()

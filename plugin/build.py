"""Сборка одного файла для команды OrcaSlicer «Установить локальный плагин»."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def build(output):
    source = (ROOT / 'kalibrovka.py').read_text(encoding='utf-8')
    page = (ROOT / 'страница.html').read_text(encoding='utf-8')
    scales = json.loads((ROOT / 'шкалы.json').read_text(encoding='utf-8'))
    source = source.replace('PAGE = "@@PAGE@@"', 'PAGE = ' + repr(page))
    source = source.replace('DEFAULT_SCALES = None  # @@ШКАЛЫ@@', 'DEFAULT_SCALES = ' + repr(scales))
    modules = {'МОДЕЛИ': 'модели.py', 'ПОТОК': 'native_flow.py', 'БАШНИ': 'native_towers.py'}
    modules['ОТКАТ'] = 'retraction_gcode.py'
    lines = []
    for line in source.splitlines():
        marker = line.rsplit('# @@', 1)[-1].removesuffix('@@')
        if marker not in modules:
            lines.append(line)
            continue
        module = (ROOT / modules.pop(marker)).read_text(encoding='utf-8-sig')
        lines.extend(line for line in module.splitlines() if '# @@ИМПОРТ_ПОТОКА@@' not in line)
    if modules:
        raise ValueError('Отсутствуют метки сборки: ' + ', '.join(modules))
    source = '\n'.join(lines) + '\n'
    compile(source, str(output), 'exec')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)

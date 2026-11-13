"""Загрузка и подрезка штатных башен из установленной OrcaSlicer."""

import os
from pathlib import Path
import subprocess
import tempfile

import trimesh

БАШНИ_ORCA = {
    'температура': ('temperature_tower', 'temperature_tower.drc'),
    'pa': ('pressure_advance', 'tower_with_seam.drc'),
    'макс_расход': ('volumetric_speed', 'SpeedTestStructure.drc'),
}


def штатная_башня(исполняемый, ресурсы, рабочая, ключ, низ, верх, ширина=None):
    модель = ресурсы.joinpath('calib', *БАШНИ_ORCA[ключ])
    if not модель.is_file():
        raise FileNotFoundError('Штатная модель OrcaSlicer не найдена: ' + модель.name)
    with tempfile.TemporaryDirectory(prefix='orca-mesh-', dir=рабочая) as временная:
        результат = subprocess.run(
            [str(исполняемый), '--export-stl', '--outputdir', временная, str(модель)],
            cwd=временная, capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        выход = list(Path(временная).rglob('*.stl'))
        if результат.returncode or len(выход) != 1:
            raise ValueError('OrcaSlicer не смогла экспортировать штатную модель ' + модель.name)
        сетка = trimesh.load_mesh(выход[0])

    if not сетка.is_watertight or not 0 <= низ < верх <= сетка.bounds[1, 2]:
        raise ValueError('Неподдерживаемая сетка или диапазон высоты башни ' + модель.name)
    if верх < сетка.bounds[1, 2]:
        сетка = сетка.slice_plane((0, 0, верх), (0, 0, -1), cap=True, engine='earcut')
    if низ > 0:
        сетка = сетка.slice_plane((0, 0, низ), (0, 0, 1), cap=True, engine='earcut')
    if not сетка.is_watertight:
        raise ValueError('Не удалось замкнуть срез башни ' + модель.name)
    сетка.apply_translation((0, 0, -сетка.bounds[0, 2]))
    if ширина is not None and ширина < сетка.extents[0]:
        сетка.apply_scale((ширина / сетка.extents[0], 1, 1))
    return сетка.vertices.tolist(), сетка.faces.tolist()

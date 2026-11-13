"""Загрузка и подрезка штатных башен из установленной OrcaSlicer."""

import DracoPy
import mapbox_earcut
import scipy.sparse
import shapely
import trimesh

# Подготовить ленивые импорты геометрии до обработки сообщений WebView.
def _подготовить_подрезку():
    trimesh.creation.box().slice_plane((0, 0, 0), (0, 0, 1), cap=True, engine='earcut')


_подготовить_подрезку()

БАШНИ_ORCA = {
    'температура': ('temperature_tower', 'temperature_tower.drc'),
    'pa': ('pressure_advance', 'tower_with_seam.drc'),
    'макс_расход': ('volumetric_speed', 'SpeedTestStructure.drc'),
}


def штатная_башня(ресурсы, ключ, низ, верх, ширина=None):
    модель = ресурсы.joinpath('calib', *БАШНИ_ORCA[ключ])
    if not модель.is_file():
        raise FileNotFoundError('Штатная модель OrcaSlicer не найдена: ' + модель.name)
    данные = DracoPy.decode(модель.read_bytes())
    сетка = trimesh.Trimesh(данные.points, данные.faces)

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

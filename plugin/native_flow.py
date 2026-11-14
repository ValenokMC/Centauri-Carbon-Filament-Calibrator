# -*- coding: utf-8 -*-
"""Подготовка пробной плиты потока из штатной геометрии OrcaSlicer 2.5."""

import math
import xml.etree.ElementTree as ET
import zipfile

from модели import габарит  # @@ИМПОРТ_ПОТОКА@@


def плита_потока(ресурсы, центр, поток_филамента, поток_процесса):
    """Взять плитки Orca с исходными подписями и настроить расход каждой."""
    for коэффициент in (поток_филамента, поток_процесса):
        if not math.isfinite(коэффициент) or коэффициент <= 0:
            raise ValueError('Коэффициенты потока должны быть положительными числами')

    if поток_филамента <= 0.05:
        raise ValueError('Поток филамента должен быть больше максимального сдвига')

    источник = ресурсы / 'calib' / 'filament_flow' / 'Orca-LinearFlow.3mf'
    with zipfile.ZipFile(источник) as архив:
        модель = ET.fromstring(архив.read('3D/3dmodel.model'))

    объекты = {узел.attrib['id']: узел for узел in модель.findall('{*}resources/{*}object')}
    плитки = []
    for элемент in модель.findall('{*}build/{*}item'):
        if 'transform' in элемент.attrib:
            raise ValueError('Неизвестная раскладка плиток OrcaSlicer')
        объект = объекты[элемент.attrib['objectid']]
        имя = объект.attrib['name']
        сдвиг = float(имя.removeprefix('flowrate_').replace('m', '-'))
        вершины = [
            tuple(float(v.attrib[ось]) for ось in 'xyz')
            for v in объект.findall('{*}mesh/{*}vertices/{*}vertex')
        ]
        треугольники = [
            tuple(int(t.attrib[индекс]) for индекс in ('v1', 'v2', 'v3'))
            for t in объект.findall('{*}mesh/{*}triangles/{*}triangle')
        ]
        if not вершины or not треугольники:
            raise ValueError('Пустая плитка OrcaSlicer: ' + имя)
        плитки.append({
            'имя': имя,
            'сетка': (вершины, треугольники),
            'сдвиг': сдвиг,
            'настройки': {
                'print_flow_ratio': format(
                    поток_процесса * (поток_филамента + сдвиг) / поток_филамента, '.6f'
                ),
                'wall_loops': '1',
                'top_shell_layers': '5',
                'bottom_shell_layers': '2',
                'sparse_infill_density': '35%',
                'top_surface_pattern': 'archimedeanchords',
                'center_of_surface_pattern': 'each_surface',
                'top_surface_fill_order': 'default',
                'calib_flowrate_topinfill_special_order': '1',
                'separated_infills': '0',
                'align_infill_direction_to_model': '1',
                'gap_fill_target': 'nowhere',
                'ironing_type': 'no ironing',
                'top_solid_infill_flow_ratio': '1',
                'enable_support': '0',
                'brim_type': 'no_brim',
            },
        })

    if sorted(плитка['сдвиг'] for плитка in плитки) != [шаг / 100 for шаг in range(-5, 6)]:
        raise ValueError('Неизвестная шкала плиток OrcaSlicer')

    границы = [габарит(плитка['сетка']) for плитка in плитки]
    место = tuple(
        центр[ось] - (min(г[ось] for г in границы) + max(г[ось + 3] for г in границы)) / 2
        for ось in range(2)
    )
    for плитка in плитки:
        плитка['место'] = место
    return {'объекты': плитки, 'плита': {}, 'команды': []}

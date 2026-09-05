# -*- coding: utf-8 -*-
"""Ручные правки в слайсере и накопление сдвигов теста потока."""
import json
import os

import pytest

from centauri_calibrator import formulas, presets, scales


# ---------------------------------------------------------------- поток

def test_odin_progon_kak_i_ranshe():
    assert formulas.flow_by_offset(0.98, [0.02]) == 1.0


def test_povtornyy_progon_skladyvaetsya():
    """Ноль на второй плите значит «попал», а не «вернуть базовое»."""
    assert formulas.flow_by_offset(0.98, [0.02, 0]) == 1.0
    assert formulas.flow_by_offset(0.98, [0.02, 0, -0.01]) == 0.99


def test_staryy_zhurnal_s_odnim_chislom_chitaetsya():
    assert formulas.flow_by_offset(0.98, 0.02) == 1.0


def test_bred_vsyo_ravno_otklonyaetsya():
    with pytest.raises(formulas.MeasurementOutOfRange):
        formulas.flow_by_offset(0.98, [0.5])


def test_poyasnenie_pokazyvaet_vsyu_tsepochku():
    тест = {"key": "flow", "input": "offset", "params": {},
            "fields": ["filament_flow_ratio"]}
    _, why = scales.compute(тест, [0.02, 0], {"filament_flow_ratio": 0.98})
    assert why == "0.98 + 0.02 + 0"


# --------------------------------------------------------- чтение пресета

def сделать_пресет(tmp_path, **поля):
    путь = tmp_path / "Spool.json"
    узел = {"name": "Spool", "inherits": "Elegoo PETG @ECC"}
    узел.update({k: [v] for k, v in поля.items()})
    путь.write_text(json.dumps(узел), encoding="utf-8")
    return str(путь)


ПОЛЯ = {"filament_retraction_length", "nozzle_temperature", "filament_flow_ratio"}


def test_chitaem_tolko_svoi_polya(tmp_path):
    путь = сделать_пресет(tmp_path, filament_retraction_length="0.6",
                          nozzle_temperature="240", compatible_printers="whatever")
    текущее = presets.read_current([путь], ПОЛЯ)
    assert текущее == {"filament_retraction_length": "0.6",
                       "nozzle_temperature": "240"}


def test_net_faila_net_znacheniy(tmp_path):
    assert presets.read_current([str(tmp_path / "нет.json")], ПОЛЯ) == {}


def test_bityy_preset_ne_ronyaet(tmp_path):
    путь = tmp_path / "Spool.json"
    путь.write_text("{это не json", encoding="utf-8")
    assert presets.read_current([str(путь)], ПОЛЯ) == {}


def test_beryom_pervyy_suschestvuyuschiy(tmp_path):
    второй = сделать_пресет(tmp_path, nozzle_temperature="245")
    текущее = presets.read_current([str(tmp_path / "нет.json"), второй], ПОЛЯ)
    assert текущее == {"nozzle_temperature": "245"}


# ------------------------------------------------------------ расхождения

def test_rashozhdenie_nahoditsya():
    разница = presets.differences({"filament_retraction_length": 0.40},
                                  {"filament_retraction_length": "0.6"})
    assert разница == {"filament_retraction_length": ("0.6", "0.40")}


def test_sovpadenie_ne_schitaetsya_rashozhdeniem():
    """Сравнивать надо в том виде, в каком значение лежит в пресете."""
    assert presets.differences({"filament_retraction_length": 0.4},
                               {"filament_retraction_length": "0.40"}) == {}


def test_polya_kotorogo_net_v_presete_ne_trogaem():
    """Поле, которого в пресете ещё нет, не расхождение, а просто новое."""
    assert presets.differences({"pressure_advance": 0.04}, {}) == {}


def test_zakryeplyonnaya_stroka_prohodit_naskvoz():
    """Ручное значение уже в форме пресета, округлять его нечем."""
    assert formulas.format_field("filament_retraction_length", "0.6") == "0.6"
    assert formulas.format_field("nozzle_temperature", "250") == "250"
    assert formulas.format_field("filament_retraction_length", 0.4) == "0.40"


# ---------------------------------------------------------------- сессия

class ФейкСессия(object):
    """Только то, что нужно для проверки наложения и снятия закреплений."""

    from centauri_calibrator.session import Session
    with_manual = Session.with_manual
    owned_fields = Session.owned_fields
    manual_path = Session.manual_path
    load_manual = Session.load_manual
    save_manual = Session.save_manual

    def __init__(self, folder, tests, manual=None):
        self.folder = folder
        self.tests = tests
        self.manual = dict(manual or {})
        self.dry_run = False


ТЕСТЫ = [{"key": "temperature", "fields": ["nozzle_temperature"]},
         {"key": "retraction", "fields": ["filament_retraction_length"]}]


def test_ruchnoe_perekryvaet_raschyotnoe(tmp_path):
    сессия = ФейкСессия(str(tmp_path), ТЕСТЫ,
                        {"filament_retraction_length": "0.6"})
    итог = сессия.with_manual({"filament_retraction_length": 0.40,
                               "nozzle_temperature": 240})
    assert итог["filament_retraction_length"] == "0.6"
    assert итог["nozzle_temperature"] == 240


def test_pervyy_sloy_temperatury_tozhe_nash(tmp_path):
    сессия = ФейкСессия(str(tmp_path), ТЕСТЫ)
    assert "nozzle_temperature_initial_layer" in сессия.owned_fields()


def test_zakreplenia_perezhivayut_perezapusk(tmp_path):
    сессия = ФейкСессия(str(tmp_path), ТЕСТЫ,
                        {"filament_retraction_length": "0.6"})
    сессия.save_manual()
    заново = ФейкСессия(str(tmp_path), ТЕСТЫ)
    заново.load_manual()
    assert заново.manual == {"filament_retraction_length": "0.6"}


def test_pustye_zakreplenia_udalyayut_fail(tmp_path):
    сессия = ФейкСессия(str(tmp_path), ТЕСТЫ, {"nozzle_temperature": "250"})
    сессия.save_manual()
    assert os.path.exists(сессия.manual_path())
    сессия.manual = {}
    сессия.save_manual()
    assert not os.path.exists(сессия.manual_path())


def test_suhoy_progon_nichego_ne_pishet(tmp_path):
    сессия = ФейкСессия(str(tmp_path), ТЕСТЫ, {"nozzle_temperature": "250"})
    сессия.dry_run = True
    сессия.save_manual()
    assert not os.path.exists(сессия.manual_path())

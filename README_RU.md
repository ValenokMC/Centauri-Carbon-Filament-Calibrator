<div align="center">

# Filament Lab

**Калибровка пластика прямо в OrcaSlicer. Выбрал катушку, открыл плиту теста, нарезал, напечатал, ввёл замер — пресет катушки обновился сам.**

[![CI](https://img.shields.io/github/actions/workflow/status/ValenokMC/Centauri-Carbon-Filament-Calibrator/ci.yml?branch=main&style=flat-square)](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/actions)
[![OrcaSlicer](https://img.shields.io/badge/OrcaSlicer-2.5-F08A2A?style=flat-square)](#совместимость)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=flat-square&logo=windows&logoColor=white)](#совместимость)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

[English](README.md) · **Русский**

[Изменения](CHANGELOG.md) · [Поддержка](SUPPORT.md) · [Telegram](https://t.me/SupporBiBot?start=centauri_calibrator) · [Поддержать автора](https://pay.cloudtips.ru/p/5440d07c)

</div>

---

Filament Lab — плагин для **OrcaSlicer 2.5**. Он добавляет в слайсер вкладку
калибровки и ведёт по пресету на каждую катушку. Плагин заменяет консольный
калибратор версии 1.x; тот остаётся доступен в
[теге `v1.0.0`](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/releases/tag/v1.0.0).

> **Состояние: предварительная версия.** Используется для настоящих калибровок на
> Windows с Elegoo Centauri Carbon. Другие принтеры, установка с нуля на чистом
> профиле и откат ещё не проверены — см. [Совместимость](#совместимость).

## Что калибрует

| № | Тест | Что вводишь | Поле пресета |
|---|---|---|---|
| 1 | **Температура** | Температуру лучшего блока башни | `nozzle_temperature` |
| 2 | **Поток** | Подпись самой ровной плитки | `filament_flow_ratio` |
| 3 | **Усадка** | Длину бруска 100 мм | `filament_shrink` |
| 4 | **Pressure Advance** | Высоту пояса башни с самыми чёткими углами | `pressure_advance` |
| 5 | **Макс. расход** | Высоту, где стенка начала рваться | `filament_max_volumetric_speed` |
| + | **Откат** (необязательно) | Высоту самой чистой ступени | `filament_retraction_length` |

Шкалы есть для **PLA · PETG · PETG-CF · PETG-GF · ABS · ASA · PA · TPU**.

## Как устроено

- **Тест открывается готовой плитой.** Вкладка пишет 3MF с моделью теста и
  нужными ему настройками поверх принтера и процесса, выбранных в Orca. Модели
  температуры, потока, PA и расхода берутся из установленной OrcaSlicer, брусок
  усадки — свой.
- **Вводится сырой замер**, а не итоговое число. Шкала материала превращает его в
  значение пресета и отказывает, если число физически не имеет смысла.
- **Пресет — надстройка.** Пишутся только измеренные поля, остальное наследуется
  от базового профиля, поэтому обновление профилей производителя калибровку не стирает.
- **Другие сопла.** Варианты `@0.2`, `@0.6` и `@0.8 nozzle` пересчитываются из
  результата на 0.4. Это оценка, она так и подписана, и её можно перемерить.
- **Новая катушка без перезапуска.** Катушки лежат в локальном наборе пресетов,
  который Orca перечитывает на лету.
- Откат идёт через штатное «Калибровка → Откат» в Orca; вкладка показывает, что
  ввести, и сохраняет замер.

## Установка

Архива выпуска 2.x пока нет. Плагин собирается в один файл из исходников:

```powershell
git clone https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator.git
cd Centauri-Carbon-Filament-Calibrator
python plugin/build.py dist/kalibrovka.py
```

Дальше в OrcaSlicer: **Плагины → Установить локальный плагин** → `dist/kalibrovka.py`.
Orca сама поставит библиотеки, которые объявляет плагин (`trimesh`, `numpy`,
`shapely`, `mapbox-earcut`, `DracoPy`, `scipy`). После замены установленной
версии Orca нужно перезапустить.

Совет: в настройках Orca поставить «Поведение при загрузке → Загружать всё», чтобы
плиты открывались без вопроса «проект или только геометрия».

## Совместимость

| | Состояние |
|---|---|
| OrcaSlicer 2.5.0, Windows 10 / 11 | ✅ Используется каждый день |
| Elegoo Centauri Carbon, сопло 0.4 | ✅ Катушка откалибрована полностью |
| Другие принтеры в Orca | ⚠️ Плиты следуют выбранному принтеру и размеру стола; профиль Prusa MINI нарезался верно, остальное не проверялось |
| Установка с нуля на чистом профиле Orca | ⚠️ Ещё не проверена |
| macOS, Linux | ❌ Не поддерживаются — загрузка плиты использует вызов Windows |
| OrcaSlicer 2.4 и старше | ❌ Нет API плагинов — нужна [консольная v1.0.0](https://github.com/ValenokMC/Centauri-Carbon-Filament-Calibrator/releases/tag/v1.0.0) |

## Где данные

```
%APPDATA%\OrcaSlicer\kalibrovka\
├── шкалы.json      шкалы тестов по материалам
├── Журнал.csv      строка на каждую калибровку
├── базы.json       снимок значений базовых профилей
└── Катушки\        замеры и плиты по катушкам
```

Пресеты катушек — в `%APPDATA%\OrcaSlicer\user\<аккаунт>\_local\kalibrovka\`.
Данные лежат в папке самой Orca: на каждый файл плагина вне её Orca спрашивает
разрешение.

## Разработка

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install trimesh numpy shapely mapbox-earcut DracoPy scipy
python -m pytest
python tools/check_public_safety.py
python tools/build_release.py --version 0.0.0-dev
```

Устройство кода и план работ: [plugin/README.md](plugin/README.md),
[plugin/СОСТОЯНИЕ.md](plugin/СОСТОЯНИЕ.md). См. также [CONTRIBUTING.md](CONTRIBUTING.md).

## Поддержать автора

Если плагин пригодился: [☕ CloudTips](https://pay.cloudtips.ru/p/5440d07c)
· иностранной картой: [Tribute](https://web.tribute.tg/d/P54). Ничего не платное и не закрыто.

## Лицензия

[MIT](LICENSE) © ValenokMC. Сторонние компоненты и что (не) распространяется:
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Проект не связан с Elegoo и OrcaSlicer; названия использованы, чтобы сказать, с чем он работает.

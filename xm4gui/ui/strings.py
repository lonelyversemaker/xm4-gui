"""UI text in Russian and English, picked from the system locale (XM4GUI_LANG overrides)."""

from __future__ import annotations

import os

from PySide6.QtCore import QLocale

EN = {
    "app_title": "XM4 Firmware Tool",
    "headset": "Headphones",
    "refresh": "Find",
    "searching": "Searching for connected headphones…",
    "no_devices": "No connected headphones found. Turn the WH-1000XM4 on, connect it in the system Bluetooth settings and press “Find”.",
    "not_xm4": "The selected device does not look like a WH-1000XM4.",
    "firmware": "Firmware",
    "battery": "Battery",
    "charging": "charging",
    "unknown": "—",
    "status_failed": "Could not read the headphone status: {error}",
    "update": "Firmware update",
    "backup": "Back up calibration (NVDM)…",
    "backup_tip": "Saves the 512 KB calibration store of this headset. The file contains pairing keys: keep it private.",
    "backup_save_title": "Save NVDM backup",
    "backup_done": "Backup saved: {path}",
    "backup_bad_magic": "Backup saved, but its header is not NVDM. Do not rely on it.",
    "backup_failed": "Backup failed: {error}",
    "choose_fw": "Choose firmware file…",
    "choose_fw_title": "Choose a WH-1000XM4 firmware file",
    "fw_filter": "Firmware (*.bin);;All files (*)",
    "drop_hint": "or drop a .bin file onto this window",
    "where_fw": "Where to get the firmware?",
    "where_fw_url": "https://github.com/lonelyversemaker/xm4-gui#where-to-get-the-firmware",
    "fw_none": "No file selected",
    "fw_known": "Official {model} firmware {version} ✓",
    "fw_unknown": "Unknown file ✗ (not an official WH-1000XM4 image)",
    "fw_read_failed": "Could not read the file: {error}",
    "allow_unknown": "Allow unknown images (dangerous)",
    "allow_unknown_confirm": "Flashing a file that is not a known official image can brick the headphones. Enable anyway?",
    "check_connected": "Headphones connected",
    "check_battery": "Battery at least {min}%",
    "check_backup": "Calibration backup made (recommended)",
    "check_version": "Selected version differs from the installed one",
    "check_same_version": "This version is already installed",
    "check_file": "Official firmware file selected",
    "flash": "Install firmware",
    "flash_confirm_title": "Install firmware?",
    "flash_confirm": "Install firmware {version} on the headphones?\n\nIt takes about {minutes} minutes. Keep the headphones on and close to the computer, do not turn them off and do not close the laptop lid. The headphones reboot at the end.",
    "flash_same": "\n\nThis version is already installed.",
    "flash_no_backup": "\n\nYou have not made a calibration backup in this session.",
    "cancel": "Cancel",
    "cancel_confirm": "Stop the update? The installed firmware stays as it is.",
    "stage_connect": "Connecting",
    "stage_erase": "Erasing the update area",
    "stage_program": "Writing firmware",
    "stage_verify": "Checking integrity",
    "stage_commit": "Applying update",
    "stage_reconnect": "Waiting for the headphones to reboot…",
    "stage_backup": "Reading calibration",
    "step": "Step {n}/{total}: {name}",
    "eta": "{speed:.1f} KB/s, about {left} left",
    "flash_done": "Done. The headphones now run firmware {version}.",
    "flash_done_no_status": "Firmware was committed, but the headphones did not reconnect yet ({error}). Turn them on and press “Find”.",
    "flash_failed": "Firmware update failed: {error}\n\nThe update was not applied, the headphones keep the installed firmware. Reconnect them and try again.",
    "cancelled": "Cancelled. Nothing was changed on the headphones.",
    "busy_close": "An operation is in progress. Wait until it finishes before closing the window.",
    "log": "Log",
    "save_log": "Save log…",
    "save_log_title": "Save log",
    "error": "Error",
    "done": "Done",
    "warning": "Warning",
}

RU = {
    "app_title": "XM4 Firmware Tool",
    "headset": "Наушники",
    "refresh": "Найти",
    "searching": "Ищу подключённые наушники…",
    "no_devices": "Подключённые наушники не найдены. Включите WH-1000XM4, подключите их в системных настройках Bluetooth и нажмите «Найти».",
    "not_xm4": "Выбранное устройство не похоже на WH-1000XM4.",
    "firmware": "Прошивка",
    "battery": "Батарея",
    "charging": "заряжается",
    "unknown": "—",
    "status_failed": "Не удалось прочитать состояние наушников: {error}",
    "update": "Обновление прошивки",
    "backup": "Резервная копия калибровки (NVDM)…",
    "backup_tip": "Сохраняет 512 КБ калибровочных данных этих наушников. В файле есть ключи сопряжения, никому его не отправляйте.",
    "backup_save_title": "Сохранить резервную копию NVDM",
    "backup_done": "Резервная копия сохранена: {path}",
    "backup_bad_magic": "Копия сохранена, но её заголовок не NVDM. Не полагайтесь на неё.",
    "backup_failed": "Не удалось сделать резервную копию: {error}",
    "choose_fw": "Выбрать файл прошивки…",
    "choose_fw_title": "Выберите файл прошивки WH-1000XM4",
    "fw_filter": "Прошивка (*.bin);;Все файлы (*)",
    "drop_hint": "или перетащите .bin файл в это окно",
    "where_fw": "Где взять прошивку?",
    "where_fw_url": "https://github.com/lonelyversemaker/xm4-gui#где-взять-прошивку",
    "fw_none": "Файл не выбран",
    "fw_known": "Официальная прошивка {model} {version} ✓",
    "fw_unknown": "Неизвестный файл ✗ (не официальный образ WH-1000XM4)",
    "fw_read_failed": "Не удалось прочитать файл: {error}",
    "allow_unknown": "Разрешить неизвестные образы (опасно)",
    "allow_unknown_confirm": "Прошивка файла, который не является известным официальным образом, может превратить наушники в кирпич. Всё равно включить?",
    "check_connected": "Наушники подключены",
    "check_battery": "Заряд не меньше {min}%",
    "check_backup": "Сделана резервная копия калибровки (рекомендуется)",
    "check_version": "Выбранная версия отличается от установленной",
    "check_same_version": "Эта версия уже установлена",
    "check_file": "Выбран официальный файл прошивки",
    "flash": "Установить прошивку",
    "flash_confirm_title": "Установить прошивку?",
    "flash_confirm": "Установить прошивку {version} на наушники?\n\nЭто займёт около {minutes} минут. Держите наушники включёнными и рядом с компьютером, не выключайте их и не закрывайте крышку ноутбука. В конце наушники перезагрузятся.",
    "flash_same": "\n\nЭта версия уже установлена.",
    "flash_no_backup": "\n\nВ этой сессии не сделана резервная копия калибровки.",
    "cancel": "Отмена",
    "cancel_confirm": "Остановить обновление? Установленная прошивка останется прежней.",
    "stage_connect": "Подключение",
    "stage_erase": "Очистка области обновления",
    "stage_program": "Запись прошивки",
    "stage_verify": "Проверка целостности",
    "stage_commit": "Применение обновления",
    "stage_reconnect": "Ждём перезагрузку наушников…",
    "stage_backup": "Чтение калибровки",
    "step": "Шаг {n}/{total}: {name}",
    "eta": "{speed:.1f} КБ/с, осталось около {left}",
    "flash_done": "Готово. На наушниках прошивка {version}.",
    "flash_done_no_status": "Прошивка применена, но наушники ещё не переподключились ({error}). Включите их и нажмите «Найти».",
    "flash_failed": "Не удалось обновить прошивку: {error}\n\nОбновление не применено, на наушниках осталась прежняя прошивка. Переподключите их и попробуйте снова.",
    "cancelled": "Отменено. На наушниках ничего не изменилось.",
    "busy_close": "Идёт операция. Дождитесь её окончания, прежде чем закрывать окно.",
    "log": "Журнал",
    "save_log": "Сохранить журнал…",
    "save_log_title": "Сохранить журнал",
    "error": "Ошибка",
    "done": "Готово",
    "warning": "Внимание",
}

assert EN.keys() == RU.keys()


def _pick() -> dict:
    lang = os.environ.get("XM4GUI_LANG")
    if lang:
        return RU if lang.lower().startswith("ru") else EN
    return RU if QLocale.system().language() == QLocale.Language.Russian else EN


_TABLE = _pick()


def t(key: str, **kwargs: object) -> str:
    text = _TABLE[key]
    return text.format(**kwargs) if kwargs else text


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    if _TABLE is RU:
        return f"{minutes} мин {sec:02d} с" if minutes else f"{sec} с"
    return f"{minutes} min {sec:02d} s" if minutes else f"{sec} s"

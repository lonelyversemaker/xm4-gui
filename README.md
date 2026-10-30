# XM4 Firmware Tool

A desktop app for the Sony WH-1000XM4. Pick a firmware file and install it with a few clicks, back up the headphones' calibration and switch noise control modes. You don't need a terminal. It works on macOS and Linux.

Русская версия ниже.

It is a graphical front end for [wh1000xm4-anc-optimizer](https://github.com/randwardatake/wh1000xm4-anc-optimizer) by randwardatake, used through [our fork with macOS support](https://github.com/lonelyversemaker/wh1000xm4-anc-optimizer) (tag `v0.1.0-macos`). That project handles the Bluetooth transport, the official firmware table and the Sony control protocol. The firmware flasher and the NVDM backup are ported from its `tools/` scripts and now report progress and support cancelling (see `NOTICE`).

> Not affiliated with Sony. Flashing firmware always carries some risk. The app installs only images whose SHA-256 matches a known official WH-1000XM4 release, unless you explicitly override that.

## What it does

- **Headphones:** finds the connected WH-1000XM4 and shows firmware version, battery and noise control mode.
- **Noise control:** Noise cancelling / Ambient (level 1–20, focus on voice) / Wind / Off.
- **Calibration backup:** saves the 512 KB NVDM store with a `.sha256` file next to it. The file contains pairing keys, so keep it private.
- **Firmware update:**
  - Choose or drop a `.bin` file and the app identifies it straight away.
  - A pre-flight checklist runs first: connected, battery ≥ 50%, official image, version, backup.
  - Progress is shown per stage with speed and time left.
  - You can cancel until the commit. Up to that point only the update area is written and the running firmware stays untouched.
  - After the commit the app waits for the headphones to reboot and shows the new version.
- **System sleep:** blocked while a backup or update is running (`caffeinate` / `systemd-inhibit`).
- **Log:** shown in the app and can be saved. MAC addresses are masked.

## Run from source

```sh
git clone <this repo> && cd xm4-gui
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m xm4gui
```

- **macOS:** needs the Xcode Command Line Tools (`xcode-select --install`). The Bluetooth helper is compiled on first use. macOS may ask to allow Bluetooth access for your terminal.
- **Linux:** needs BlueZ (`bluetoothctl`).

Pair and connect the headphones in the system Bluetooth settings first.

## Build an app

```sh
.venv/bin/pip install -e '.[build]'
./packaging/build_macos.sh    # -> dist/XM4 Firmware Tool.app (helper prebuilt inside, no Xcode needed to run)
./packaging/build_linux.sh    # -> dist/xm4gui/ and, with appimagetool, an AppImage
```

The macOS app is signed ad-hoc and not notarized. On first launch, right-click it, choose *Open*, then allow Bluetooth access.

## Tests

```sh
.venv/bin/python -m pytest
```

The flasher and backup run against fake RFCOMM sockets, and the window is tested with pytest-qt offscreen.

## Firmware files

Official images are listed by SHA-256 in `xm4_optimizer/firmware.py` of the upstream project, which also links to where to download them.

---

## По-русски

Десктопное приложение для Sony WH-1000XM4. Работает на macOS и Linux, терминал не нужен. Что умеет:
- выбрать файл прошивки и установить его в несколько кликов;
- сделать резервную копию калибровки;
- переключать режимы шумоподавления.

Это графическая оболочка над [wh1000xm4-anc-optimizer](https://github.com/randwardatake/wh1000xm4-anc-optimizer), через [наш форк с поддержкой macOS](https://github.com/lonelyversemaker/wh1000xm4-anc-optimizer). Прошивальщик и бэкап перенесены из его скриптов: добавлены прогресс и отмена.

**Запуск из исходников:** см. команды выше. На macOS нужны Xcode Command Line Tools, на Linux нужен BlueZ. Сначала подключите наушники в системных настройках Bluetooth.

**Как обновить прошивку:**
1. Нажмите «Найти» и проверьте, что наушники определились.
2. Сделайте «Резервную копию калибровки». Храните файл у себя: в нём ключи сопряжения.
3. Нажмите «Выбрать файл прошивки…» или перетащите `.bin` в окно. Приложение покажет, официальный ли это образ и какой версии.
4. Когда все обязательные пункты отмечены ✓, нажмите «Установить прошивку». Это займёт около 9 минут.
5. Отменить можно до этапа применения обновления. До этого момента текущая прошивка не затрагивается.
6. После перезагрузки наушников приложение покажет новую версию.

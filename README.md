# XM4 Firmware Tool

A desktop app to install official firmware on the **Sony WH-1000XM4**, including downgrading (for example 3.0.1 → 2.5.0). You pick a file and click a button. No terminal needed. It runs on macOS and Linux.

**[Русская версия ниже](#по-русски)**

> Not affiliated with Sony. Flashing firmware always carries some risk. The app installs only files whose SHA-256 matches a known official WH-1000XM4 release.

## Where to get the firmware

This project does not host Sony firmware. The official files are mirrored from Sony's update server (`info.update.sony.net`) in the community archive [lzghzr/MDR_Proxy](https://github.com/lzghzr/MDR_Proxy/tree/master/firmware/2943/MDRID294300). `MDRID294300` is the WH-1000XM4 model code.

Click a link to download the file:

| Version | Download | Size |
|---|---|---|
| **2.5.0** | [UPG_2.5.0_20210413_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.5.0_20210413_enc.97529f0f6630238e77ce76bfc6766aa5616e78e7.bin) | 1.4 MB |
| 2.6.0 | [UPG_2.6.0_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.6.0_enc.b05cfdecc230c3dda652591c5c9f9ab0785dbb37.bin) | 4.2 MB |
| 2.7.1 | [UPG_2.7.1_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.7.1_enc.d30f546e4a57111263afc2a013c58dd783ee7d21.bin) | 4.2 MB |
| 2.9.0 | [UPG_2.9.0_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.9.0_enc.e4decc6b3015d1450c3fb56ab7b5d96780d184b5.bin) | 4.2 MB |
| 3.0.1 | [UPG_3.0.1_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_3.0.1_enc.51b88a0dd729e7bc6da4d7e9c8af1c98e975ba1e.bin) | 4.2 MB |

- **Which version to pick:** 2.5.0 is the version people downgrade to. Owners report stronger noise cancelling and no hiss with it. That is a listening report, not a measurement. 3.0.1 is the latest version and the one to go back to.
- **No need to rename or unpack the file.** Choose the downloaded `.bin` as it is.
- **The file is checked automatically.** After you choose it, the app shows "Official WH-1000XM4 firmware X.Y.Z ✓". If you see "Unknown file ✗", the file is damaged or it is not WH-1000XM4 firmware. Do not use it.
- **Do not install these files on any other model,** such as the WH-1000XM5 or WF-1000XM4.

## How to update

1. Charge the headphones to **at least 50%**, better 60% or more, and unplug the cable. The headphones turn Bluetooth off while charging.
2. Connect the headphones to the computer in the system Bluetooth settings.
3. Open **XM4 Firmware Tool** and press **Find**. You should see the firmware version and battery level.
4. Optional but recommended: press **Back up calibration (NVDM)…** and save the file. It holds your headset's calibration and pairing keys. Keep it private.
5. Press **Choose firmware file…**, or drop the `.bin` onto the window.
6. When every required line is ✓, press **Install firmware** and confirm. It takes **about 9 minutes**. Keep the headphones on and close to the computer, and do not close the laptop lid. The app keeps the computer awake.
7. At the end the headphones reboot and reconnect on their own, and the app shows the new version.

**Cancel** works until the "Applying update" step. Up to that point only the update area is written, and the headphones keep their current firmware.

## Install

**macOS 12 or newer, Apple Silicon or Intel:** download `XM4-Firmware-Tool-macOS-universal.zip` from [Releases](https://github.com/lonelyversemaker/xm4-gui/releases), unzip it and move the app to Applications. The app is not notarized. On first launch, right-click it, choose *Open*, then allow Bluetooth access when macOS asks.

**From source (macOS and Linux):**

```sh
git clone https://github.com/lonelyversemaker/xm4-gui && cd xm4-gui
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m xm4gui
```

- On macOS this needs the Xcode Command Line Tools (`xcode-select --install`).
- On Linux it needs BlueZ (`bluetoothctl`).

## For developers

- **Backend:** Bluetooth, the official firmware table and the Sony protocol come from [wh1000xm4-anc-optimizer](https://github.com/randwardatake/wh1000xm4-anc-optimizer) by randwardatake. The app uses [our fork with macOS support](https://github.com/lonelyversemaker/wh1000xm4-anc-optimizer) (tag `v0.1.0-macos`).
- **Ported code:** the flasher and backup are ported from its `tools/` scripts, with progress reporting and cancellation added (see `NOTICE`).
- **Build (Linux):** `.venv/bin/pip install -e '.[build]'`, then `./packaging/build_linux.sh`.
- **Build (macOS release, universal2, macOS 12+):** install the universal2 Python 3.13 from [python.org](https://www.python.org/downloads/macos/), then:

  ```sh
  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m venv .venv-universal
  .venv-universal/bin/pip install "PySide6-Essentials==6.9.2" pyinstaller pillow
  .venv-universal/bin/pip install --no-deps "xm4_optimizer @ git+https://github.com/lonelyversemaker/wh1000xm4-anc-optimizer@v0.1.1-macos"
  .venv-universal/bin/pip install --no-deps -e .
  PYTHON=.venv-universal/bin/python ./packaging/build_macos.sh
  ```

  `--no-deps` keeps numpy out: it has no universal2 wheel, and the app does not need it. PySide6 6.9 is the last series that supports macOS 12. With Homebrew Python the script makes a build for this Mac only.
- **Tests:** `.venv/bin/python -m pytest`. They use fake RFCOMM sockets, and the window runs offscreen with pytest-qt.

---

## По-русски

Приложение для установки официальной прошивки на **Sony WH-1000XM4**, в том числе для отката, например с 3.0.1 на 2.5.0. Выбираете файл и нажимаете кнопку, терминал не нужен. Работает на macOS и Linux.

### Где взять прошивку

Мы не храним прошивки Sony у себя. Официальные файлы с сервера обновлений Sony собраны в архиве [lzghzr/MDR_Proxy](https://github.com/lzghzr/MDR_Proxy/tree/master/firmware/2943/MDRID294300). `MDRID294300` — код модели WH-1000XM4.

Нажмите на ссылку, файл скачается:

| Версия | Скачать | Размер |
|---|---|---|
| **2.5.0** | [UPG_2.5.0_20210413_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.5.0_20210413_enc.97529f0f6630238e77ce76bfc6766aa5616e78e7.bin) | 1,4 МБ |
| 2.6.0 | [UPG_2.6.0_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.6.0_enc.b05cfdecc230c3dda652591c5c9f9ab0785dbb37.bin) | 4,2 МБ |
| 2.7.1 | [UPG_2.7.1_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.7.1_enc.d30f546e4a57111263afc2a013c58dd783ee7d21.bin) | 4,2 МБ |
| 2.9.0 | [UPG_2.9.0_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_2.9.0_enc.e4decc6b3015d1450c3fb56ab7b5d96780d184b5.bin) | 4,2 МБ |
| 3.0.1 | [UPG_3.0.1_enc….bin](https://raw.githubusercontent.com/lzghzr/MDR_Proxy/2e80d32/firmware/2943/MDRID294300/UPG_3.0.1_enc.51b88a0dd729e7bc6da4d7e9c8af1c98e975ba1e.bin) | 4,2 МБ |

- **Какую версию выбрать.** На 2.5.0 обычно откатываются: владельцы пишут, что шумоподавление сильнее и нет шипения. Это впечатления на слух, а не измерения. 3.0.1 — последняя версия, на неё можно вернуться.
- **Файл не нужно переименовывать или распаковывать.** Выбирайте скачанный `.bin` как есть.
- **Приложение само проверяет файл.** После выбора оно покажет «Официальная прошивка WH-1000XM4 X.Y.Z ✓». Если видите «Неизвестный файл ✗», файл повреждён или это не прошивка WH-1000XM4. Не используйте его.
- **Не ставьте эти файлы на другие модели,** например WH-1000XM5 или WF-1000XM4.

### Как обновить

1. Зарядите наушники **минимум до 50%**, лучше до 60% и выше, и отключите кабель. Пока наушники заряжаются, Bluetooth у них выключен.
2. Подключите наушники к компьютеру в системных настройках Bluetooth.
3. Откройте **XM4 Firmware Tool** и нажмите **«Найти»**. Должны появиться версия прошивки и заряд.
4. Желательно: нажмите **«Резервная копия калибровки (NVDM)…»** и сохраните файл. В нём калибровка ваших наушников и ключи сопряжения, никому его не отправляйте.
5. Нажмите **«Выбрать файл прошивки…»** или перетащите `.bin` в окно.
6. Когда все обязательные пункты отмечены ✓, нажмите **«Установить прошивку»** и подтвердите. Это займёт **около 9 минут**. Держите наушники включёнными и рядом с компьютером, не закрывайте крышку ноутбука. Приложение само не даёт компьютеру уснуть.
7. В конце наушники перезагрузятся и сами подключатся снова, а приложение покажет новую версию.

**«Отмена»** работает до шага «Применение обновления». До этого момента записывается только область обновления, а на наушниках остаётся прежняя прошивка.

### Установка

**macOS 12 и новее, Apple Silicon или Intel:** скачайте `XM4-Firmware-Tool-macOS-universal.zip` в [Releases](https://github.com/lonelyversemaker/xm4-gui/releases), распакуйте и перенесите приложение в «Программы». Приложение не нотаризовано. При первом запуске нажмите на него правой кнопкой, выберите «Открыть», затем разрешите доступ к Bluetooth, когда macOS спросит.

**Из исходников:** см. команды в разделе [Install](#install). На macOS нужны Xcode Command Line Tools, на Linux нужен BlueZ.

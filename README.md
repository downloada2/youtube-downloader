# YouTube Downloader

Простая программа для скачивания аудио (MP3) и видео (MP4) с YouTube. Windows, macOS, Android и расширение для Chrome.
A simple desktop/mobile downloader for YouTube audio (MP3) and video (MP4), plus a Chrome extension.

- Два режима: **Аудио MP3** (128–320 kbps) и **Видео MP4** (до максимального качества), плейлисты, отмена, история.
- Тёмная и светлая темы, без рекламы и аккаунтов, всё работает локально.
- Движок: [yt-dlp](https://github.com/yt-dlp/yt-dlp) + ffmpeg.

## Скачать

Готовые файлы — в разделе **Releases**:

| Платформа | Файл |
|---|---|
| Windows 10/11 | `YouTube Downloader Setup (Windows).exe` |
| macOS (Apple Silicon) | `YouTube-Downloader-AppleSilicon.dmg` |
| macOS (Intel) | `YouTube-Downloader-Intel.dmg` |
| Android 8+ (arm64) | `YouTube Downloader (Android).apk` |
| Chrome | `YouTube-Downloader-Chrome-extension.zip` |

### Предупреждения при установке
Приложения не подписаны сертификатом разработчика, поэтому системы предупреждают:
- **Windows:** «Windows защитила ваш компьютер» → *Подробнее* → *Выполнить в любом случае*.
- **macOS:** правый клик по приложению → *Открыть* → *Открыть*.
- **Android:** разрешите установку из неизвестных источников для браузера/файлового менеджера.

## Расширение для Chrome
Добавляет кнопки «MP3 / MP4» на страницы видео YouTube и отправляет ссылку в программу на вашем компьютере (программа должна быть запущена).
Установка: распакуйте архив → `chrome://extensions` → «Режим разработчика» → «Загрузить распакованное расширение».
Связь идёт только через `127.0.0.1:47653`, принимаются лишь запросы от расширений Chrome и только ссылки YouTube.

## Веб-версия
Тот же интерфейс в браузере: `web/server.py` (только стандартная библиотека + yt-dlp + ffmpeg).
```
pip install yt-dlp imageio-ffmpeg
python web/server.py --port 8080        # http://127.0.0.1:8080
```
или Docker: `docker build -f web/Dockerfile -t ytdl-web . && docker run -p 8080:8080 ytdl-web`.
У каждого посетителя своя сессия, файлы живут на сервере 30 минут и удаляются. Принимаются только ссылки YouTube, без плейлистов, не длиннее 3 часов, не больше 3 загрузок одновременно на сервере и 20 в час с одного IP.
Учтите: YouTube часто блокирует IP дата-центров, на домашнем интернете работает стабильнее.

## Сборка из исходников
- Windows: `pip install yt-dlp imageio-ffmpeg pyinstaller pywebview`, затем `pyinstaller "windows/YouTube Downloader.spec"` и Inno Setup (`windows/ytdl.iss`).
- macOS: `./build_macos.sh` (в репозитории настроен GitHub Actions).

## Важно
Скачивайте только то, на что у вас есть права. Использование программы нарушает условия сервиса YouTube, если вы скачиваете защищённый авторским правом контент без разрешения. Ответственность за использование лежит на пользователе. Проект не связан с YouTube/Google.

Лицензия: MIT.

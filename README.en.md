# Kindle Weather Calendar

[中文](README.md)

Turn an idle, jailbroken Kindle into a low-power e-ink calendar that stays on. **The server runs in the cloud.** The Kindle pulls grayscale PNG regions over Wi‑Fi. **No always-on PC.** A [web admin](#web-admin) in the browser controls which pages appear, the city, carousel timing, and the footer quote. The device picks the new settings up on its next fetch.

Five pages cycle: **Today** (date, a minute-by-minute clock, current weather, sunrise/sunset and air quality, a scene strip) → **Week** → **Month** (holiday marks, other months) → **Detail** (hourly temperature and daily indices) → **Almanac**. The footer is a daily quote. With no touch input the pages advance on a timer. With the optional touch helper you can tap or swipe.

## How it works

```
  Cloud (Render / Docker)                  Kindle (jailbreak + Wi‑Fi + fbink)
 ┌──────────────────────┐  env + PNG     ┌────────────────────────────┐
 │ Flask                 │ ◄───────────── │ dash.sh                    │
 │ ├ /api/v1/dashboard  │  pull on demand│ ├ Clock: local glyphs,     │
 │ │  weather, lunar,   │                │ │  A2 refresh each minute, │
 │ │  AQI, quote,       │                │ │  no network              │
 │ │  holidays          │                │ ├ Regions: fetch only when │
 │ ├ /r/<page>/*.png    │                │ │  the ETag changes (GC16) │
 │ ├ /admin             │                │ └ Full refresh at 03:00    │
 │ └ /dashboard.png     │                │    and once per carousel   │
 │   (v1 full-page)     │                │ (no fbink → eips full page)│
 └──────────────────────┘                └────────────────────────────┘
```

The server renders weather, calendar data, and holidays into grayscale regions, and publishes page order, coordinates, ETags, and dwell times in `/api/v1/dashboard.env`. The Kindle downloads a region only when its content changed.

## Web admin

Open `https://your-host/admin`. You can set:

- Which of Week / Month / Detail / Almanac are enabled, and their order (Today stays first)
- Carousel on/off, dwell seconds per enabled page, and how long a touch pauses the carousel
- City: search by name (Open-Meteo) to fill coordinates and timezone, or type them
- Footer quote: online Hitokoto, the built-in offline poems, or your own list
- Page previews, import / export, restore defaults, and whether the device has fetched the latest settings

The password is the `ADMIN_PASSWORD` environment variable. If it is unset, `/admin` only says the admin is disabled. `SECRET_KEY` signs the session; set a stable random value or every container recreate logs you out. Settings are stored in `data/settings.json`. Mount `./data:/app/data` or they disappear when the container is recreated. Keep both values in the server `.env` only — not in the image and not in GitHub. See [DEPLOY.md](DEPLOY.md).

After you save, the Kindle applies the change on its next fetch (at most about 15 minutes by default, or immediately if you tap the top-right corner on the device). A successful fetch wins over `config.sh`. The dwell times in `config.sh` are only a fallback when the fetch fails. Per-page dwell times and a carousel that ends on the last enabled page need the current `dash.sh` on the device.

## Deploy the server, then let the Kindle pull

### 1. Render (free tier)

1. Push this repo to GitHub
2. [Render](https://render.com) → New → Blueprint → connect the repo
3. Set city, screen size, and the admin password:

| Variable | Example (PW2) | Role |
|----------|----------------|------|
| `LOCATION_NAME` | Beijing | Default city until you save one in the admin |
| `LATITUDE` | 39.9042 | Same |
| `LONGITUDE` | 116.4074 | Same |
| `TIMEZONE` | Asia/Shanghai | Same |
| `SCREEN_WIDTH` | 758 | Must match the Kindle |
| `SCREEN_HEIGHT` | 1024 | Same |
| `ADMIN_PASSWORD` | (you choose) | Admin login. Empty disables `/admin` |
| `SECRET_KEY` | `openssl rand -hex 32` | Session signing |

4. You get a host such as `https://kindle-calendar-xxxx.onrender.com/dashboard.png`. The admin is `/admin` on the same host.

> The free instance sleeps after about 15 minutes idle, and it has no persistent disk. A restart drops admin settings back to the environment defaults. Use Docker with a `data/` volume if the settings should survive.

### 2. Docker

**Local or a VPS:**

```bash
docker compose up -d
# Picture:  http://SERVER:8080/dashboard.png
# Admin:    http://SERVER:8080/admin
```

A `.env` next to the compose file (see `.env.example`) overrides city, resolution, `ADMIN_PASSWORD`, and `SECRET_KEY`.

**One-shot VPS install:**

```bash
bash deploy.sh
```

That builds the image and starts it with `docker-compose.image.yml`.

**Baota (宝塔) panel:**

1. Put the project in `/www/wwwroot/kindle-calendar`
2. Docker → Compose → new, using `docker-compose.baota.yml`
3. Fill city, resolution, and the admin password in `.env` in that directory
4. Open `http://SERVER:8080/dashboard.png`

If the panel build fails, run `bash deploy.sh` in the Baota terminal.

**CI/CD (recommended once it is set up):**

A push to `master` builds an image in GitHub Actions, pushes it to Alibaba Cloud Container Registry, then SSHs to the server to pull and restart. The server never talks to GitHub or Docker Hub. First-time setup, the password, and the `data/` volume are in [DEPLOY.md](DEPLOY.md). Without CI, `./deploy-remote.sh root@SERVER` does a one-shot deploy.

### 3. Kindle

**Copy the files:**

```bash
cp kindle/config.sh.example kindle/config.sh
# Set API_URL="https://your-host/api/v1/dashboard.env"

scp kindle/config.sh kindle/dash.sh root@<KINDLE_IP>:/mnt/us/kindle-calendar/
scp -r kindle/lib kindle/bin root@<KINDLE_IP>:/mnt/us/kindle-calendar/
ssh root@<KINDLE_IP> "chmod +x /mnt/us/kindle-calendar/*.sh /mnt/us/kindle-calendar/lib/*.sh"
```

Region mode needs [FBInk](https://github.com/NiLuJe/FBInk) (see `kindle/bin/README.md`) at `/mnt/us/kindle-calendar/bin/fbink`. Without it, `dash.sh` falls back to pulling a single `/dashboard.png` on a timer.

**`config.sh`:**

| Variable | Default | Meaning |
|----------|---------|---------|
| `API_URL` | — | Cloud env URL. This is the region-mode entry point |
| `CLOCK_ENABLED` | 1 | Minute clock drawn locally, no network |
| `ROTATE_ENABLED` | 1 | Carousel. Overridden by the cloud env after a successful fetch |
| `ROTATE_TODAY_S` / `ROTATE_OTHER_S` | 120 / 30 | Dwell fallback used only when the env fetch fails |
| `ROTATE_SUPPRESS_S` | 120 | Touch-pause fallback, same rule |
| `TOUCH_MODE` | force | `force`: immersive as soon as tapread exists. `auto`: wait for a real touch. `off`: carousel only |
| `SERVER_URL` | — | v1 full-page URL (fallback mode) |
| `INTERVAL` | 900 | Fetch interval in seconds. Suggested minimum 900. The clock ignores it |
| `FULL_REFRESH_EVERY` | 6 | v1 only: full refresh every N partial updates |
| `WIFI_ON_DEMAND` | false | `false` leaves Wi‑Fi on. `true` turns it off after each fetch |
| `BOOK_FULLSCREEN` | false | Launcher script: `false` returns to the library with Home. `true` is immersive until reboot |
| `WIFI_WAIT` | 15 | Seconds to wait after enabling Wi‑Fi |

**Touch (optional):** build or copy `tapread` as described in `kindle/bin/README.md`. Left/right edges or a horizontal swipe change pages. On the month page a swipe changes the month. A tap on the top-right refreshes now; a ~2s press leaves immersive mode. Bottom center toggles night invert. Startup begins with a full-screen clear.

**A. Background daemon**

```bash
ssh root@<KINDLE_IP> "nohup /mnt/us/kindle-calendar/dash.sh &"
```

**B. Library launcher**

1. Copy `kindle/documents/天气台历.sh` into the Kindle `documents/` folder
2. Upload `/mnt/us/kindle-calendar/lib/display.sh`
3. Open 「天气台历」 for the Chinese screen. `WeatherCalendar.sh` in the same folder is the English screen. `Weather Calendar.sh` (with a space) still opens the Chinese launcher.

With `BOOK_FULLSCREEN=false`, Home returns to the library. `true` can only be left by rebooting.

**C. KUAL**

Copy `kindle/kual-extension/` to `extensions/kindle-calendar/` on the device. The menu can start, stop, refresh, and show the log.

Wi‑Fi must already be configured on the Kindle.

## Requirements

| Item | Notes |
|------|--------|
| Models | Paperwhite 2/3/5, Kindle 11, and similar. Jailbreak required |
| Firmware | Follow [KindleModding](https://kindlemodding.org/) for your version |
| After jailbreak | **KUAL** and **USBNetwork** (SSH) |
| A computer | Only for development and preview |

### Jailbreak (short)

1. Turn on airplane mode so the firmware does not update itself
2. Settings → Device Options → Device Info, note the firmware version
3. Pick the method for that version:
   - 5.16.3 – 5.18.0 → [WinterBreak](https://kindlemodding.org/jailbreaking/WinterBreak/)
   - 5.18.1 – 5.18.5 → [AdBreak](https://kindlemodding.org/jailbreaking/AdBreak/)
   - 5.16.4 – 5.18.6 (PW5/KT5/KOA3) → [Nosebleed](https://kindlemodding.org/jailbreaking/Nosebleed/)
4. Install Block OTA Updates, then **MRPI**, **KUAL**, and **USBNetwork**

Jailbreaking can brick a device or void expectations of official support. Back up first and read the upstream docs.

## Local development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `config.example.yaml` to `config.yaml` and set the city and resolution. On a jailbroken Kindle, `eips -i` prints `xres` / `yres`.

| Model | Resolution |
|-------|------------|
| Kindle 4 | 600 × 800 |
| Paperwhite 2 | 758 × 1024 |
| Paperwhite 3 / 7th gen | 1072 × 1448 |
| Paperwhite 5 / Kindle 11 | 1236 × 1648 |

```bash
python scripts/preview.py     # writes preview.png
# Admin, PowerShell example:
$env:ADMIN_PASSWORD = "local-password"
python -m server.app          # http://localhost:8080/dashboard.png and /admin
```

Cloud deploys use environment variables instead of `config.yaml`. The yaml file does not need to be in the image.

## API

| Path | Description |
|------|-------------|
| `GET /api/v1/dashboard.json` | Calendar payload: weather, lunar data, solar terms, almanac, air quality, quote, holidays, enabled page order |
| `GET /api/v1/dashboard.env` | POSIX env for the device: region box, URL, ETag, page order, per-page dwell |
| `GET /r/<page>/<region>.png` | Grayscale region. `page` is today, week, month, detail, or almanac |
| `GET /r/today/clock/<g>.png` | Clock glyph (`0`–`9` and `:`) |
| `GET /dashboard.png?page=` | Full-page composite. Default page is today |
| `GET /admin` | Web admin |
| `GET /weather` | Current weather JSON |
| `GET /health` | Health check |

## Screen and power

- Keep the fetch interval at 15 minutes or more (`INTERVAL=900`). The clock refreshes locally every minute and does not use the network
- A full refresh runs at 03:00, and again each time the carousel returns to Today, to clear ghosting
- Do not leave it plugged in forever; cycle the battery
- Keep OTA updates blocked so a firmware upgrade does not remove the jailbreak

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Blank or corrupted screen | PNG size must match `eips -i`, 8-bit grayscale |
| Image never updates | `config.sh` URL, Wi‑Fi, and `/mnt/us/kindle-calendar/dash.log` |
| First fetch is slow | Render free tier cold start is about 30 seconds |
| Chinese text is missing | The Docker image includes Noto fonts. Locally, set `font_path` in `config.yaml` |
| `/admin` says it is disabled | Set `ADMIN_PASSWORD` and recreate the container |
| Admin settings vanish after restart | Mount `./data:/app/data`. Render's free tier has no disk, so a restart returns to env defaults |
| Carousel timing ignores the admin | Update `dash.sh` on the device, then tap the top-right corner or wait one `INTERVAL` |
| Launcher script will not exit | With `BOOK_FULLSCREEN=false`, press Home. In immersive mode, press the top-right corner for about 2 seconds |
| Several copies running | The launcher stops the previous process. Do not start `dash.sh` more than once in the background |
| `eips: not found` | Jailbreak is required. The binary is `/usr/sbin/eips` |
| SSH fails | USBNetwork must be on, and the IP must be right |

## Layout

```
kindle-calendar/
├── Dockerfile
├── docker-compose.yml          # generic compose (data volume + admin env)
├── docker-compose.acr.yml      # GitHub Actions → Alibaba Cloud ACR
├── docker-compose.baota.yml    # Baota compose
├── docker-compose.image.yml    # start an image that is already built
├── deploy.sh / deploy-remote.sh
├── DEPLOY.md                   # CI/CD and the server .env
├── render.yaml
├── config.example.yaml
├── server/
│   ├── app.py                  # routes
│   ├── admin.py                # admin API
│   ├── settings.py             # validation and settings.json
│   ├── templates/admin.html
│   ├── service.py              # cache, region render, env
│   ├── data.py / weather.py / aqi.py
│   ├── almanac.py / astro.py / holidays.py / quotes.py
│   └── render/                 # five-page region renderer
├── kindle/
│   ├── dash.sh
│   ├── config.sh.example
│   ├── lib/display.sh
│   ├── bin/                    # fbink, tapread (see bin/README.md)
│   ├── documents/天气台历.sh   # library launcher
│   └── kual-extension/
├── tests/test_web_admin.py
└── scripts/preview.py
```

## Status

Done: partial refresh, minute clock, five pages, touch and carousel, month browsing, startup clear, air quality, web admin.

Not in this repo: ICS calendar subscriptions, switching among several saved cities, changing the device fetch interval from the admin.

Design notes live under `profiles/kindle-calendar/workspace/`.

## License

This project is released under the [GNU General Public License v3.0](LICENSE). You may use, modify, and redistribute it, provided that redistributions include the complete corresponding source and that derivative works stay under GPL-3.0. Copyright © 2026 Xinyi Zhang.

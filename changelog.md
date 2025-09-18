# 📜 Changelog – Reef Doser Project

All notable changes to this project will be documented here.  
This project follows **semantic versioning**: `MAJOR.MINOR.PATCH`.

---

## [Unreleased]
- (placeholder for upcoming changes)

---

## [v1.0.0] – 2025-09-18
### Added
- Initial baseline release of **2-pump reef doser**
- Hardware: Pimoroni Automation 2040 W, 2x 12 V peristaltic pumps
- Firmware (`main.py`):
  - Non-blocking pump control (UI stays responsive)
  - Multi-WiFi support (from `secrets.py`)
  - RTC + NTP time sync with timezone offset
  - Manual dosing schedules (pump/time/ml)
  - Auto split dosing (ml/day spread across splits)
  - Calibration (ml/min per pump)
  - Web UI with:
    - Calibration form
    - Auto dosing form
    - Manual schedule editor
    - Quick prime/dose/stop buttons
- Config persistence in `doser_cfg.json`
- MicroPython-safe helpers:
  - `format_time()` (replaces `time.strftime`)
  - `unquote_plus()` (replaces `urllib.parse.unquote_plus`)

---

## Legend
- **Added** – new features
- **Changed** – modifications to existing functionality
- **Fixed** – bug fixes
- **Removed** – features removed or deprecated

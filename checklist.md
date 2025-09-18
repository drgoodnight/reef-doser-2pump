# 🧑‍💻 Reef Doser Developer’s Cheat Sheet

Quick checklist to stay consistent when modifying or extending the project.

---

## 🔌 Hardware Assumptions
- Board: Pimoroni Automation 2040 W (Pico W inside)
- Pump relays: **GPIO 9 & 10**
- PSU: **12 V / ≥2 A**
- Low-side switching (relay breaks ground)
- Flyback diodes (1N5819) across each pump
- Optional: 470–1000 µF electrolytic capacitor across 12 V input

---

## ⚙️ Firmware Rules
- **Non-blocking pump control** (never freeze the web server during dosing)
- **Multi-WiFi support** from `secrets.py`
- **Config persistence** in `doser_cfg.json`
- **MicroPython compatibility** (no CPython-only modules)
- Use project helpers:
  - `format_time()` (instead of `time.strftime`)
  - `unquote_plus()` (instead of `urllib.parse.unquote_plus`)
- Always provide a complete `main.py` if making core changes

---

## 🧪 Before Commit Checklist
- [ ] Code runs through `mpy-cross` (syntax OK)
- [ ] Pumps stop on reboot (no stuck relays)
- [ ] Manual schedule works (triggered at set hh:mm)
- [ ] Auto dosing works (ml/day split correctly)
- [ ] Web UI responsive during long doses
- [ ] Config saved and reloaded after reboot
- [ ] Tested in **Firefox + Chrome + Brave** (disable shields if needed)

---

## 📦 Repo Hygiene
- Version/tag stable milestones (`v1.0.0`, `v1.1.0`, etc.)
- Maintain `README.md` and `CHANGELOG.md`
- Use issue templates:
  - `feature_request.md` for new features
  - `bug_report.md` for problems
- Secrets (`secrets.py`) are **never committed**

---

## 🔮 Future Extensions (Optional)
- Extra pumps (GPIO 11, 12…)
- Web UI authentication
- Daily dose logging → JSON → Grafana/Home Assistant
- Reef sensors (pH, temp, salinity)
- MQTT for alerts

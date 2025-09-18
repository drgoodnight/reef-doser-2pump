Reef Doser – 2-Pump Aquarium Dosing System (Automation 2040 W + MicroPython)

An open-source, Wi-Fi connected reef dosing controller for aquariums, built on the Pimoroni Automation 2040 W
 (Raspberry Pi Pico W RP2040).
It drives 2 peristaltic pumps via onboard relays, supports manual schedules and auto split dosing, and exposes a simple web UI for calibration and control.

✨ Features

🟢 2 Pumps controlled via GPIO 9 & 10 relays

🕒 Accurate scheduling via RTC + NTP sync (with timezone offset)

🌐 Multi-WiFi support – tries multiple SSIDs until connected

⚙️ Calibration (ml/min per pump) stored in JSON config

📅 Manual schedules – run pumps at specific times / ml amounts

🔄 Auto split dosing – deliver ml/day spread across multiple splits

🖥️ Web interface – add/remove schedules, calibrate, prime/dose pumps

🚀 Non-blocking pump control – UI stays responsive while dosing

💾 Config persistence – schedules and calibration saved to flash

🔋 RTC fallback – continues schedules even if Wi-Fi/NTP fails

📸 Hardware

Automation 2040 W
 (Raspberry Pi Pico W inside)

2x 12 V Peristaltic dosing pumps

12 V DC power supply (≥2 A recommended)

Schottky diode (1N5819 or similar) across each pump for flyback protection

Optional: electrolytic capacitor (470–1000 µF) across 12 V input for stability

Wiring

Pump + → PSU +12 V

Pump – → Relay COM

Relay NO → PSU GND

Relays are driven by Pico W GPIO 9 & 10 (through Automation 2040 W board)

This setup is low-side switching: the relay switches the negative (ground) line.

🛠️ Software
Requirements

MicroPython firmware for RP2040 (latest stable recommended)

main.py (controller logic)

secrets.py (Wi-Fi + timezone settings)

secrets.py template
# secrets.py – not tracked in git
WIFI_CREDENTIALS = [
    ("YourSSID1", "YourPassword1"),
    ("YourSSID2", "YourPassword2"),
]
# Timezone offset in seconds (e.g. +3600 = GMT+1)
TZ_OFFSET = 0

🚀 Usage

Flash MicroPython to your Pico W (via Thonny or picotool)

Copy main.py and secrets.py to the board’s filesystem

Reboot – you should see serial output like:

Starting doser (relays on GPIO 9 & 10)…
[WIFI] connected to HomeWiFi
[TIME] 2025-09-18 22:47:02
[WEB] visit: http://192.168.8.229:80/  (SSID: HomeWiFi)


Open the given IP in a browser (http://…:80/ or :8080 if fallback)

Use the web UI to calibrate, add schedules, or run pumps manually

🌐 Web UI

Calibration: set ml/min for each pump

Auto dosing: ml/day split evenly into N doses per day

Manual schedule: add specific pump/time/ml entries

Quick controls: Prime pump (seconds), Dose ml, Stop immediately

All changes are stored in doser_cfg.json on the board.

⚡ Non-blocking dosing

Unlike naive implementations, this project does not block during pump runs.
When you prime/dose, the web server responds immediately and the pump runs in the background. The site stays usable.

🔧 Development Notes

Runs best with a solid 12 V PSU and proper flyback protection.

Tested with Firefox and Chrome; Brave may require disabling shields for LAN IPs.

MicroPython quirks handled:

time.strftime replaced with format_time helper

urllib.parse.unquote_plus replaced with custom unquote_plus

📂 File Structure
/
├── main.py        # Core doser firmware
├── secrets.py     # Wi-Fi + timezone (user-provided, not tracked in git)
├── doser_cfg.json # Auto-generated config (schedules, calibration)
└── README.md      # This file

📜 License

MIT License – do whatever you like, but no warranty is provided.
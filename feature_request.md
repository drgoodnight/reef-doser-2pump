---
name: "✨ Feature Request / Improvement"
about: Suggest a new feature, bug fix, or improvement for the Reef Doser project
title: "[Feature] "
labels: enhancement
assignees: ""
---

## 📋 Description
<!-- Clearly describe what you want to change or add -->

Example:  
- Add a 3rd dosing pump on GPIO 11  
- Password-protect the web UI  
- Improve logging to show how many ml were dosed each day  

---

## 🎯 Motivation
<!-- Why is this important? What problem does it solve? -->

Example:  
- Prevents accidental access on shared network  
- Makes dosing logs visible for reef tank maintenance  

---

## 🔧 Technical Details
<!-- If known, describe how it should be implemented (hardware pins, code modules, etc.) -->

- [ ] Hardware pins needed? (specify GPIO)  
- [ ] Changes to `main.py` logic?  
- [ ] Changes to `doser_cfg.json` schema?  

---

## ✅ Acceptance Criteria
<!-- Define what success looks like -->

- [ ] Works with current hardware (Automation 2040 W, GPIO 9 & 10 unchanged unless otherwise stated)  
- [ ] Maintains non-blocking pump control (UI stays responsive)  
- [ ] Preserves Wi-Fi multi-SSID support from `secrets.py`  
- [ ] Config persists to `doser_cfg.json`  
- [ ] MicroPython-compatible (no CPython-only modules)  

---

## 📎 Additional Context
<!-- Add screenshots, wiring diagrams, or example use cases -->

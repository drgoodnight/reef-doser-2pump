# ---- 2-Pump Reef Doser (Automation 2040 W, Relays GPIO 9 & 10) ----
# Non-blocking dosing, web UI, multi-WiFi (from secrets.py), RTC fail-safe.
# MicroPython-safe time formatting and HTTP handling.

import time, json, socket
from machine import Pin, RTC
import network, ntptime

# ========= LOAD SECRETS =========
try:
    import secrets
    WIFI_CREDENTIALS = getattr(secrets, "WIFI_CREDENTIALS", [])
    TZ_OFFSET = getattr(secrets, "TZ_OFFSET", 0)
except ImportError:
    WIFI_CREDENTIALS = []
    TZ_OFFSET = 0
    print("[WARN] secrets.py not found, Wi-Fi disabled")

# ========= SIMPLE TIME FORMATTER (MicroPython-safe) =========
def format_time(fmt="%Y-%m-%d %H:%M:%S", t=None):
    """Minimal strftime replacement for MicroPython builds without time.strftime."""
    if t is None:
        t = time.localtime()
    y, m, d, hh, mm, ss, wd, yd = t
    if fmt == "%Y-%m-%d %H:%M:%S":
        return "%04d-%02d-%02d %02d:%02d:%02d" % (y, m, d, hh, mm, ss)
    if fmt == "%Y-%m-%d %H:%M":
        return "%04d-%02d-%02d %02d:%02d" % (y, m, d, hh, mm)
    if fmt == "%H:%M":
        return "%02d:%02d" % (hh, mm)
    return "%04d-%02d-%02d %02d:%02d:%02d" % (y, m, d, hh, mm, ss)

# ========= CONFIG FILE =========
CFG_FILE = "doser_cfg.json"
DEFAULT_CFG = {
    "cal_ml_min": [30.0, 30.0],
    "schedule": [
        {"p": 0, "h": 9,  "m": 0,  "ml": 5.0},
        {"p": 0, "h": 21, "m": 0,  "ml": 5.0},
        {"p": 1, "h": 10, "m": 30, "ml": 4.0},
        {"p": 1, "h": 22, "m": 30, "ml": 4.0},
    ],
    "auto": [
        {"enabled": False, "ml_day": 0.0, "splits": 24},
        {"enabled": False, "ml_day": 0.0, "splits": 24},
    ],
}

# ========= HARDWARE =========
relay1 = Pin(9, Pin.OUT, value=0)   # Pump 1
relay2 = Pin(10, Pin.OUT, value=0)  # Pump 2
pumps = [relay1, relay2]
rtc = RTC()

# ========= WIFI CONNECT =========
def wifi_connect():
    """Try each SSID in WIFI_CREDENTIALS. Returns (wlan, ssid) or (None, None)."""
    if not WIFI_CREDENTIALS:
        return None, None
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        try:
            return wlan, wlan.config('essid')
        except:
            return wlan, "connected"
    for ssid, pwd in WIFI_CREDENTIALS:
        print("[WIFI] trying %s…" % ssid)
        wlan.connect(ssid, pwd)
        t0 = time.ticks_ms()
        while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < 8000:
            time.sleep(0.2)
        if wlan.isconnected():
            print("[WIFI] connected to %s" % ssid)
            return wlan, ssid
    print("[WIFI] no known networks available")
    return None, None

# ========= TIME SYNC =========
def sync_time():
    wlan, ssid = wifi_connect()
    if wlan and wlan.isconnected():
        try:
            ntptime.host = "pool.ntp.org"
            ntptime.settime()
            t = time.time() + TZ_OFFSET
            tm = time.localtime(t)
            rtc.datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
            print("[TIME] %s" % format_time("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            print("[TIME] NTP failed, using RTC: %s" % e)
    else:
        print("[TIME] no Wi-Fi; using RTC only")

# ========= CONFIG LOAD/SAVE =========
def load_cfg():
    try:
        with open(CFG_FILE) as f:
            return json.load(f)
    except:
        with open(CFG_FILE, "w") as f:
            json.dump(DEFAULT_CFG, f)
        return json.loads(json.dumps(DEFAULT_CFG))

cfg = load_cfg()
last_run_yday = {}
last_auto_minute = [None, None]
last_auto_day = [None, None]

def save_cfg():
    with open(CFG_FILE, "w") as f:
        json.dump(cfg, f)

# ========= PUMP CONTROL =========
def pump_on(i):  pumps[i].value(1)
def pump_off(i): pumps[i].value(0)

def run_ms(i, ms):
    # blocking version (kept for reference; not used in HTTP now)
    pump_on(i); time.sleep_ms(ms); pump_off(i)

def ml_to_ms(i, ml):
    mlmin = cfg["cal_ml_min"][i]
    if mlmin <= 0:
        return 0
    return int((ml / mlmin) * 60000)

def yday():
    tm = time.localtime()
    return (time.mktime((tm[0], tm[1], tm[2], 0, 0, 0, 0, 0)) // 86400)

def minutes_since_midnight():
    tm = time.localtime()
    return tm[3] * 60 + tm[4]

# ========= NON-BLOCKING RUN SUPPORT =========
def ticks_add(a, b):
    return (a + b) & 0x7FFFFFFF

pump_until = [0, 0]  # ms tick when each pump should stop (0 = idle)

def schedule_run(i, ms):
    from time import ticks_ms
    pump_on(i)
    pump_until[i] = ticks_add(ticks_ms(), ms)

# ========= SCHEDULER =========
def run_manual_scheduler():
    tm = time.localtime()
    h, m = tm[3], tm[4]
    yd = yday()
    for i, e in enumerate(cfg["schedule"]):
        if e["h"] == h and e["m"] == m:
            if last_run_yday.get(i, -1) != yd:
                last_run_yday[i] = yd
                ms = ml_to_ms(e["p"], e["ml"])
                print("[RUN-MAN] %s P%d %.1f ml -> %d ms" %
                      (format_time("%Y-%m-%d %H:%M", tm), e['p'] + 1, e['ml'], ms))
                # non-blocking:
                schedule_run(e["p"], ms)

def run_auto_scheduler():
    yd = yday()
    now_min = minutes_since_midnight()
    for idx in (0, 1):
        a = cfg["auto"][idx]
        if not a["enabled"]:
            last_auto_minute[idx] = None
            last_auto_day[idx] = yd
            continue
        splits = max(1, int(a["splits"]))
        interval = 1440 // splits if splits <= 1440 else 1
        if (now_min % interval) == 0:
            if last_auto_day[idx] != yd or last_auto_minute[idx] != now_min:
                last_auto_day[idx] = yd
                last_auto_minute[idx] = now_min
                ml_each = a["ml_day"] / float(splits)
                ms = ml_to_ms(idx, ml_each)
                print("[RUN-AUTO] %s P%d %.3f ml -> %d ms" %
                      (format_time("%H:%M"), idx + 1, ml_each, ms))
                # non-blocking:
                schedule_run(idx, ms)

def scheduler_tick():
    run_manual_scheduler()
    run_auto_scheduler()

# ========= WEB UI =========
def html_escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def unquote_plus(s):
    """Decode form-urlencoded strings: '+' -> space, %xx -> char."""
    s = s.replace("+", " ")
    out = ""
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                out += chr(int(s[i+1:i+3], 16))
                i += 3
                continue
            except:
                pass
        out += s[i]
        i += 1
    return out

def parse_qs(body):
    params = {}
    for pair in body.split("&"):
        if not pair:
            continue
        if "=" in pair:
            k, v = pair.split("=", 1)
        else:
            k, v = pair, ""
        k = unquote_plus(k)
        v = unquote_plus(v)
        params[k] = v
    return params

def render_page(ip):
    tm = time.localtime()
    time_str = format_time("%Y-%m-%d %H:%M:%S", tm)
    cal = cfg["cal_ml_min"]
    a0, a1 = cfg["auto"][0], cfg["auto"][1]
    rows = "".join(
        f"<tr><td>{i}</td><td>P{e['p']+1}</td><td>{e['h']:02d}:{e['m']:02d}</td>"
        f"<td>{e['ml']}</td>"
        f"<td><form method='POST'><input type='hidden' name='del' value='{i}'>"
        f"<button>Del</button></form></td></tr>"
        for i, e in enumerate(cfg["schedule"])
    )
    return f"""<!doctype html><html><body>
<h2>Reef Doser (2 pumps)</h2>
<p><b>Time:</b> {html_escape(time_str)} &nbsp;
<a href="/time">Sync NTP</a> &nbsp; <small>IP: {ip}</small></p>
<h3>Calibration (ml/min)</h3>
<form method="POST">
P1:<input name="cal1" type="number" step="0.01" value="{cal[0]}"> 
P2:<input name="cal2" type="number" step="0.01" value="{cal[1]}">
<button>Save</button></form>
<h3>Auto split-dosing</h3>
<form method="POST">
<table border=1>
<tr><th>Pump</th><th>Enabled</th><th>ml/day</th><th>splits/day</th></tr>
<tr><td>P1</td><td><input type="checkbox" name="a1" {"checked" if a0["enabled"] else ""}></td>
<td><input name="a1ml" type="number" step="0.1" value="{a0['ml_day']}"></td>
<td><input name="a1s" type="number" step="1" value="{a0['splits']}"></td></tr>
<tr><td>P2</td><td><input type="checkbox" name="a2" {"checked" if a1["enabled"] else ""}></td>
<td><input name="a2ml" type="number" step="0.1" value="{a1['ml_day']}"></td>
<td><input name="a2s" type="number" step="1" value="{a1['splits']}"></td></tr>
</table><button>Save Auto</button></form>
<h3>Manual schedule</h3>
<table border=1>
<tr><th>#</th><th>Pump</th><th>Time</th><th>ml</th><th>Delete</th></tr>
{rows if rows else "<tr><td colspan=5>(none)</td></tr>"}
</table>
<form method="POST">
Pump:<select name="p"><option value="1">P1</option><option value="2">P2</option></select>
Time:<input name="h" type="number" min="0" max="23" style="width:4em"> :
<input name="m" type="number" min="0" max="59" style="width:4em">
ml:<input name="ml" type="number" step="0.1" style="width:6em">
<button>Add</button></form>
<h3>Quick controls</h3>
<form method="POST">P1:<button name="prime1" value="5">Prime 5s</button>
<button name="dose1" value="1">Dose 1ml</button>
<button name="stop1" value="1">Stop</button></form><br>
<form method="POST">P2:<button name="prime2" value="5">Prime 5s</button>
<button name="dose2" value="1">Dose 1ml</button>
<button name="stop2" value="1">Stop</button></form>
</body></html>"""

# --- HTTP helpers / server (returns 3 values) ---
def start_web(port=80):
    wlan, ssid = wifi_connect()
    ip = wlan.ifconfig()[0] if wlan and wlan.isconnected() else "0.0.0.0"
    netname = ssid if ssid else "?"
    print("[WEB] visit: http://%s:%d/  (SSID: %s)" % (ip, port, netname))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
    s.listen(2)
    s.settimeout(0.1)  # short accept timeout keeps loop responsive
    return s, ip, port

def _send_resp(conn, status="200 OK", ctype="text/html; charset=utf-8", body=""):
    try:
        if isinstance(body, str):
            body_bytes = body.encode()
        else:
            body_bytes = body
        headers = (
            "HTTP/1.1 %s\r\n"
            "Content-Type: %s\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n"
        ) % (status, ctype, len(body_bytes))
        conn.send(headers)
        conn.sendall(body_bytes)
    except:
        pass

def handle_http(conn, addr, ip):
    try:
        req = conn.recv(2048)
        if not req:
            return
        # debug first line
        first = req.split(b"\r\n", 1)[0]
        try:
            print("[HTTP]", addr, first.decode())
        except:
            print("[HTTP]", addr, first)

        head, _, body = req.partition(b"\r\n\r\n")
        line = head.split(b"\r\n")[0]
        parts = line.split(b" ")
        if len(parts) < 2:
            _send_resp(conn, "400 Bad Request", "text/plain", b"Bad Request")
            return
        method = parts[0]
        path = parts[1].decode() if isinstance(parts[1], bytes) else parts[1]

        if path == "/favicon.ico":
            _send_resp(conn, "204 No Content", "text/plain", b"")
            return

        if method == b"GET" and path == "/time":
            sync_time()
            _send_resp(conn, "302 Found", "text/plain", b"")
            return

        if method == b"POST":
            p = parse_qs(body.decode())
            # delete
            if "del" in p:
                i = int(p["del"])
                if 0 <= i < len(cfg["schedule"]):
                    cfg["schedule"].pop(i); save_cfg()
            # add schedule
            if all(k in p for k in ("p","h","m","ml")):
                try:
                    e={"p":int(p["p"])-1,"h":int(p["h"]),"m":int(p["m"]),"ml":float(p["ml"])}
                    cfg["schedule"].append(e); save_cfg()
                except: pass
            # calibration
            if "cal1" in p and "cal2" in p:
                try:
                    cfg["cal_ml_min"][0]=float(p["cal1"]); cfg["cal_ml_min"][1]=float(p["cal2"]); save_cfg()
                except: pass
            # auto
            a1_on=("a1" in p); a2_on=("a2" in p)
            if "a1ml" in p and "a1s" in p:
                cfg["auto"][0]["enabled"]=a1_on
                cfg["auto"][0]["ml_day"]=float(p["a1ml"])
                cfg["auto"][0]["splits"]=int(p["a1s"]); save_cfg()
            if "a2ml" in p and "a2s" in p:
                cfg["auto"][1]["enabled"]=a2_on
                cfg["auto"][1]["ml_day"]=float(p["a2ml"])
                cfg["auto"][1]["splits"]=int(p["a2s"]); save_cfg()
            # quick controls (non-blocking)
            if "prime1" in p: schedule_run(0, int(float(p["prime1"]) * 1000))
            if "prime2" in p: schedule_run(1, int(float(p["prime2"]) * 1000))
            if "dose1"  in p: schedule_run(0, ml_to_ms(0, float(p["dose1"])))
            if "dose2"  in p: schedule_run(1, ml_to_ms(1, float(p["dose2"])))
            if "stop1"  in p: pump_off(0); pump_until[0] = 0
            if "stop2"  in p: pump_off(1); pump_until[1] = 0

            _send_resp(conn, "302 Found", "text/plain", b"")
            return

        # GET /
        page = render_page(ip)
        _send_resp(conn, "200 OK", "text/html; charset=utf-8", page)
    except Exception as e:
        # Ignore harmless timeouts; log other errors
        msg = str(e)
        if "ETIMEDOUT" in msg or "timed out" in msg:
            return
        print("[HTTP ERR]", e)
        try:
            _send_resp(conn, "500 Internal Server Error", "text/plain", msg)
        except:
            pass
    finally:
        try: conn.close()
        except: pass

# ========= MAIN =========
print("Starting doser (relays on GPIO 9 & 10)…")
sync_time()

# try 80 then 8080
try:
    server, ip, port = start_web(80)
except Exception as e:
    print("[WEB] port 80 failed (%s), trying 8080" % e)
    server, ip, port = start_web(8080)

while True:
    scheduler_tick()

    # Non-blocking pump stop checks (keep UI responsive)
    try:
        from time import ticks_ms, ticks_diff
        now = ticks_ms()
        for i in (0, 1):
            if pump_until[i]:
                if ticks_diff(pump_until[i], now) <= 0:
                    pump_off(i)
                    pump_until[i] = 0
    except Exception as _e:
        pass

    # Accept connection and give it a longer timeout than the listener
    try:
        conn, addr = server.accept()
    except OSError:
        conn = None
    if conn:
        try:
            conn.settimeout(5)   # allow up to 5s for the client to send the request
        except:
            pass
        handle_http(conn, addr, ip)

    time.sleep(0.1)  # snappier loop
#!/usr/bin/env python3
# Anthrophonic — play the same audio on several outputs at once (speakers, HDMI,
# Bluetooth) on Linux/PipeWire, with per-output latency sync so Bluetooth
# doesn't lag. Architecture: a central null-sink + one module-loopback per
# active output. Wired outputs are delayed to align with the slowest (BT).

import subprocess, os, signal, json, math, wave, tkinter as tk

NULL_SINK = "combinado"
NULL_MON  = "combinado.monitor"
MAX_MS    = 1000
BT_KEEPALIVE = 60
DEFAULT_OFFSET = 190

CFG_DIR  = os.path.expanduser("~/.config/anthrophonic")
DELAYS   = os.path.join(CFG_DIR, "delays.json")
OFFSETS  = os.path.join(CFG_DIR, "offsets.json")
PULSE    = os.path.join(CFG_DIR, "pulse.wav")

# ------------------------------------------------------------------ i18n
def detect_lang():
    for v in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(v, "")[:2] == "es":
            return "es"
    return "en"                       # default English
LANG = detect_lang()

STRINGS = {
    "en": {
        "title": "Anthrophonic", "pick": "pick a wired output", "outputs": "OUTPUTS",
        "tune": "tune:", "auto": "auto", "pulse": "pulse", "stop": "stop pulse",
        "close": "close", "measuring": "measuring…", "nobt": "no BT active",
        "delay_of": "delay · {}", "auto_ok": "synced",
        "tip_chip": "Turn this output on/off",
        "tip_auto": "Measure latency and sync every output to the slowest (BT)",
        "tip_pulse": "Play a click train to fine-tune the sync by ear",
        "tip_slider": "Delay of the selected output (ms)",
        "tip_tune": "Pick which output the slider adjusts",
        "tip_close": "Close",
    },
    "es": {
        "title": "Anthrophonic", "pick": "elige salida de cable", "outputs": "SALIDAS",
        "tune": "ajustar:", "auto": "auto", "pulse": "pulso", "stop": "parar pulso",
        "close": "cerrar", "measuring": "midiendo…", "nobt": "sin BT activo",
        "delay_of": "retardo · {}", "auto_ok": "sincronizado",
        "tip_chip": "Activa o desactiva esta salida",
        "tip_auto": "Mide la latencia y sincroniza todas las salidas con la más lenta (BT)",
        "tip_pulse": "Reproduce un tren de clics para afinar la sincronía a oído",
        "tip_slider": "Retardo de la salida seleccionada (ms)",
        "tip_tune": "Elige qué salida ajusta el slider",
        "tip_close": "Cerrar",
    },
}
def t(k, *a):
    s = STRINGS.get(LANG, STRINGS["en"]).get(k) or STRINGS["en"].get(k, k)
    return s.format(*a) if a else s

LABELS = {"analog": {"en": "Analog", "es": "Analógico"},
          "hdmi":   {"en": "HDMI", "es": "HDMI"},
          "bt":     {"en": "Bluetooth", "es": "Bluetooth"}}
def label_of(key):
    return LABELS[key].get(LANG, LABELS[key]["en"])

# ------------------------------------------------------------ storage
def _load(p):
    try: return json.load(open(p))
    except Exception: return {}
def _save(p, d):
    os.makedirs(CFG_DIR, exist_ok=True); json.dump(d, open(p, "w"))
def get_delay(s):  return int(_load(DELAYS).get(s, 300))
def set_delay(s, ms): d = _load(DELAYS); d[s] = int(ms); _save(DELAYS, d)
def get_offset(s): return int(_load(OFFSETS).get(s, DEFAULT_OFFSET))
def set_offset(s, ms): d = _load(OFFSETS); d[s] = int(ms); _save(OFFSETS, d)

# ------------------------------------------------------- pactl / pipewire
def pactl(*a):
    return subprocess.run(["pactl", *a], capture_output=True, text=True)

ORDER = ["analog", "hdmi", "bt"]
def detect_sinks():
    out = pactl("list", "short", "sinks").stdout
    found = {}
    for line in out.splitlines():
        c = line.split("\t")
        if len(c) < 2 or c[1] == NULL_SINK: continue
        n = c[1]
        if "analog-stereo" in n: found["analog"] = (n, "wired")
        elif "hdmi-stereo" in n: found["hdmi"] = (n, "wired")
        elif n.startswith("bluez_output"): found["bt"] = (n, "bt")
    return [(k, found[k][0], found[k][1]) for k in ORDER if k in found]

def has_null():
    return any(c.split("\t")[1:2] == [NULL_SINK]
               for c in pactl("list", "short", "sinks").stdout.splitlines())
def ensure_null():
    if not has_null():
        pactl("load-module", "module-null-sink", "media.class=Audio/Sink",
              f"sink_name={NULL_SINK}", "channel_map=stereo",
              "sink_properties=device.description=Combined")
        pactl("set-default-sink", NULL_SINK)
def active_loopbacks():
    res = {}
    for line in pactl("list", "short", "modules").stdout.splitlines():
        if "module-loopback" in line and NULL_MON in line:
            mid = line.split()[0]
            for tok in line.split():
                if tok.startswith("sink="): res[tok[5:]] = mid
    return res
def sink_latency_ms(name):
    try:
        d = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True).stdout)
        for o in d:
            info = o.get("info") or {}
            if (info.get("props") or {}).get("node.name", "") == name:
                for l in (info.get("params") or {}).get("Latency", []):
                    if l.get("direction") == "Input" and l.get("maxNs"):
                        return round(l["maxNs"] / 1e6)
    except Exception: pass
    return 0
def add_output(sink, kind):
    ensure_null()
    if kind == "bt": lat = BT_KEEPALIVE
    else:
        lat = get_delay(sink)
        if "analog-stereo" in sink: pactl("set-sink-port", sink, "analog-output-speaker")
    pactl("load-module", "module-loopback", f"source={NULL_MON}", f"sink={sink}", f"latency_msec={lat}")
def remove_output(sink):
    lb = active_loopbacks()
    if sink in lb: pactl("unload-module", lb[sink])
    if not active_loopbacks():
        for m in pactl("list", "short", "modules").stdout.splitlines():
            if "module-null-sink" in m and NULL_SINK in m:
                pactl("unload-module", m.split()[0])
def reload_one(sink, ms):
    lb = active_loopbacks()
    if sink in lb: pactl("unload-module", lb[sink])
    pactl("load-module", "module-loopback", f"source={NULL_MON}", f"sink={sink}", f"latency_msec={int(ms)}")

def make_pulse():
    if os.path.exists(PULSE): return
    os.makedirs(CFG_DIR, exist_ok=True)
    import numpy as np
    sr = 48000; period = int(sr*0.6); burst = int(sr*0.035); total = sr*60
    n = np.arange(total); i = n % period
    env = np.clip(1.0 - i/burst, 0, 1); env[i >= burst] = 0
    sig = ((0.6*env*np.sin(2*np.pi*1000*i/sr) + 0.012*np.sin(2*np.pi*220*n/sr))*32767).astype("<i2")
    st = np.column_stack([sig, sig]).ravel()
    w = wave.open(PULSE, "wb"); w.setnchannels(2); w.setsampwidth(2)
    w.setframerate(sr); w.writeframes(st.tobytes()); w.close()

# ================================== GUI ==================================
WAVE_BG="#101216"; BG="#1b1e24"; FG="#9aa0aa"; MUTE="#5b606b"
ACCENT="#4a9eff"; ACC_DIM="#2f4d6e"; TROUGH="#2a2d34"; GLOW="#243a55"
WAVE1="#1b2935"; WAVE2="#152029"; FONT="DejaVu Sans"

class Tip:
    def __init__(self, w, text):
        self.w, self.text, self.tip, self.job = w, text, None, None
        w.bind("<Enter>", self._enter, add="+")
        w.bind("<Leave>", self._leave, add="+")
    def _enter(self, _): self.job = self.w.after(450, self._show)
    def _show(self):
        x = self.w.winfo_rootx() + self.w.winfo_width()//2 - 80
        y = self.w.winfo_rooty() + self.w.winfo_height() + 6
        self.tip = tk.Toplevel(self.w); self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{max(0,x)}+{y}")
        tk.Label(self.tip, text=self.text, bg="#0c0d10", fg="#cfd3da",
                 font=(FONT, 9), padx=8, pady=4, wraplength=220, justify="left").pack()
    def _leave(self, _):
        if self.job: self.w.after_cancel(self.job); self.job = None
        if self.tip: self.tip.destroy(); self.tip = None

class Slider:
    def __init__(self, parent, w, mn, mx, val, cb, step=10):
        self.w, self.mn, self.mx, self.cb, self.step = w, mn, mx, cb, step
        self.pad, self.cy, self.val = 16, 22, val
        self.cv = tk.Canvas(parent, width=w, height=44, bg=BG, highlightthickness=0)
        self.cv.create_line(self.pad, self.cy, w-self.pad, self.cy, fill=TROUGH, width=4, capstyle="round")
        self.fill = self.cv.create_line(self.pad, self.cy, self.pad, self.cy, fill=ACC_DIM, width=4, capstyle="round")
        self.glow = self.cv.create_oval(0,0,0,0, fill=GLOW, outline="")
        self.knob = self.cv.create_oval(0,0,0,0, fill=ACCENT, outline="")
        self.cv.bind("<Button-1>", self._drag); self.cv.bind("<B1-Motion>", self._drag)
        self._redraw()
    def _x(self, v): return self.pad + (v-self.mn)/(self.mx-self.mn)*(self.w-2*self.pad)
    def _redraw(self):
        x = self._x(self.val)
        self.cv.coords(self.fill, self.pad, self.cy, x, self.cy)
        self.cv.coords(self.glow, x-14, self.cy-14, x+14, self.cy+14)
        self.cv.coords(self.knob, x-8, self.cy-8, x+8, self.cy+8)
    def _drag(self, e):
        frac = (e.x-self.pad)/(self.w-2*self.pad)
        v = round((self.mn+frac*(self.mx-self.mn))/self.step)*self.step
        self.set(v); self.cb(self.val)
    def set(self, v): self.val = max(self.mn, min(self.mx, int(v))); self._redraw()
    def get(self): return self.val

def flat_btn(parent, text, cmd, accent=False):
    base = ACCENT if accent else FG
    b = tk.Button(parent, text=text, command=cmd, bd=0, highlightthickness=0,
                  bg=BG, fg=base, activebackground=BG, activeforeground=ACCENT,
                  relief="flat", cursor="hand2", font=(FONT, 11), padx=8, pady=2)
    b._base = base
    b.bind("<Enter>", lambda e: b.config(fg=ACCENT))
    b.bind("<Leave>", lambda e: b.config(fg=b._base))
    return b

def chip(parent, text, cmd):
    return tk.Button(parent, text=text, command=cmd, bd=0, highlightthickness=0,
                     relief="flat", cursor="hand2", font=(FONT, 10, "bold"),
                     padx=14, pady=6, bg=TROUGH, fg=MUTE,
                     activebackground=ACC_DIM, activeforeground=ACCENT)
def paint_chip(b, on):
    b.config(bg=(ACC_DIM if on else TROUGH), fg=(ACCENT if on else MUTE))

root = tk.Tk()
root.title(t("title"))
root.geometry("540x400")
root.configure(bg=WAVE_BG)

# --- fondo de ondas de sonido animado ---
waves = tk.Canvas(root, bg=WAVE_BG, highlightthickness=0)
waves.place(x=0, y=0, relwidth=1, relheight=1)
_phase = [0.0]
def draw_waves():
    waves.delete("w")
    W = root.winfo_width() or 540; H = root.winfo_height() or 400
    for k, (amp, freq, col, sp) in enumerate([(26, 2.0, WAVE2, 0.9),
                                              (34, 1.4, WAVE1, 1.3),
                                              (20, 3.0, WAVE2, 0.6)]):
        pts = []
        for x in range(0, W+10, 10):
            y = H/2 + amp*math.sin(x/W*freq*2*math.pi + _phase[0]*sp + k)
            pts += [x, y]
        waves.create_line(*pts, fill=col, width=2, smooth=True, tags="w")
    _phase[0] += 0.06
    root.after(50, draw_waves)

# --- tarjeta central (sobre las ondas) ---
card = tk.Frame(root, bg=BG)
card.place(relx=0.5, rely=0.5, anchor="center")

SINKS = detect_sinks()
_state = {"job": None, "guard": False}
sel = {"sink": None}

status = tk.Label(card, text="—", font=(FONT, 22, "bold"), bg=BG, fg=ACCENT)
status.pack(pady=(16, 0))
substatus = tk.Label(card, text=t("pick"), font=(FONT, 9), bg=BG, fg=MUTE)
substatus.pack()

tk.Label(card, text=t("outputs"), font=(FONT, 8, "bold"), bg=BG, fg=MUTE).pack(pady=(12, 2))
outrow = tk.Frame(card, bg=BG); outrow.pack()
out_chips = {}

row = tk.Frame(card, bg=BG); row.pack(pady=(14, 2))
scale = Slider(row, 280, 0, MAX_MS, 300, lambda ms: on_slider(ms))
scale.cv.pack(side="left", padx=(0, 10))
Tip(scale.cv, t("tip_slider"))
entry_var = tk.StringVar(value="300")
entry = tk.Entry(row, width=5, textvariable=entry_var, font=(FONT, 12), justify="center",
                 bg=TROUGH, fg=FG, insertbackground=FG, relief="flat",
                 highlightthickness=1, highlightbackground=TROUGH, highlightcolor=ACCENT)
entry.pack(side="left", ipady=3)

tunerow = tk.Frame(card, bg=BG); tunerow.pack(pady=(8, 0))
tune_chips = {}
botrow = tk.Frame(card, bg=BG)

# ----------------------------- logic
def current_active(): return active_loopbacks()
def wired_active():
    act = current_active()
    return [n for (k, n, kind) in SINKS if kind == "wired" and n in act]

def refresh():
    act = current_active()
    for key, (b, name, kind) in out_chips.items():
        paint_chip(b, name in act)
    for w in tunerow.winfo_children(): w.destroy()
    tune_chips.clear()
    wa = wired_active()
    if sel["sink"] not in wa: sel["sink"] = wa[0] if wa else None
    if wa:
        tk.Label(tunerow, text=t("tune"), font=(FONT, 9), bg=BG, fg=MUTE).pack(side="left", padx=(0, 6))
        for key, name, kind in SINKS:
            if name in wa:
                b = chip(tunerow, label_of(key), lambda n=name: select_tune(n))
                b.pack(side="left", padx=4); paint_chip(b, name == sel["sink"])
                Tip(b, t("tip_tune")); tune_chips[name] = b
    sync_slider_to_sel()

def sync_slider_to_sel():
    s = sel["sink"]
    if not s:
        status.config(text="—"); substatus.config(text=t("pick")); return
    ms = get_delay(s)
    _state["guard"] = True; scale.set(ms); entry_var.set(str(ms)); _state["guard"] = False
    lab = next((label_of(k) for (k, n, kind) in SINKS if n == s), s)
    status.config(text=f"{ms} ms"); substatus.config(text=t("delay_of", lab))

def select_tune(name):
    sel["sink"] = name
    for n, b in tune_chips.items(): paint_chip(b, n == name)
    sync_slider_to_sel()

def toggle_output(key):
    name, kind = next(((n, kd) for (k, n, kd) in SINKS if k == key), (None, None))
    if not name: return
    if name in current_active(): remove_output(name)
    else: add_output(name, kind)
    refresh()

def apply(ms, learn=True):
    s = sel["sink"]
    if not s: return
    ms = max(0, min(MAX_MS, int(ms)))
    reload_one(s, ms); set_delay(s, ms)
    if learn:
        bt = next((n for (k, n, kd) in SINKS if kd == "bt"), None)
        if bt and bt in current_active():
            set_offset(s, ms - (sink_latency_ms(bt) - sink_latency_ms(s)))
    status.config(text=f"{ms} ms")

def schedule(ms):
    if _state["job"]: root.after_cancel(_state["job"])
    _state["job"] = root.after(250, lambda: apply(ms))
def on_slider(ms):
    if _state["guard"]: return
    _state["guard"] = True; entry_var.set(str(ms)); _state["guard"] = False
    status.config(text=f"{ms} ms"); schedule(ms)
def on_entry(*_):
    if _state["guard"]: return
    txt = entry_var.get().strip()
    if not txt.isdigit(): return
    ms = max(0, min(MAX_MS, int(txt)))
    _state["guard"] = True; scale.set(ms); _state["guard"] = False
    status.config(text=f"{ms} ms"); schedule(ms)
def bump(d):
    ms = max(0, min(MAX_MS, scale.get() + d))
    _state["guard"] = True; scale.set(ms); entry_var.set(str(ms)); _state["guard"] = False
    status.config(text=f"{ms} ms"); schedule(ms)
entry_var.trace_add("write", on_entry)
entry.bind("<Return>", lambda e: apply(int(entry_var.get() or 0)))

def mini_arrow(parent, glyph, d):
    b = tk.Button(parent, text=glyph, command=lambda: bump(d), bd=0, highlightthickness=0,
                  bg=BG, fg=MUTE, activebackground=BG, activeforeground=ACCENT,
                  relief="flat", cursor="hand2", font=(FONT, 8), width=2)
    b.bind("<Enter>", lambda e: b.config(fg=ACCENT)); b.bind("<Leave>", lambda e: b.config(fg=MUTE))
    return b
arrows = tk.Frame(row, bg=BG); arrows.pack(side="left", padx=(4, 0))
mini_arrow(arrows, "▲", +10).pack(); mini_arrow(arrows, "▼", -10).pack()

_pulse = {"proc": None}
def stop_pulse():
    p = _pulse["proc"]
    if p and p.poll() is None:
        try: os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception: p.terminate()
    _pulse["proc"] = None
def toggle_pulse():
    if _pulse["proc"] and _pulse["proc"].poll() is None:
        stop_pulse(); btn_pulse.config(text=t("pulse"), fg=FG); btn_pulse._base = FG; return
    make_pulse()
    _pulse["proc"] = subprocess.Popen(
        ["bash", "-c", f'while :; do paplay --device={NULL_SINK} "{PULSE}"; done'],
        start_new_session=True)
    btn_pulse.config(text=t("stop"), fg=ACCENT); btn_pulse._base = ACCENT

def auto_sync():
    if not (_pulse["proc"] and _pulse["proc"].poll() is None): toggle_pulse()
    status.config(text=t("measuring")); root.after(1300, _auto_apply)
def _auto_apply():
    act = current_active()
    bt = next((n for (k, n, kd) in SINKS if kd == "bt"), None)
    has_bt = bool(bt and bt in act)
    rep_bt = sink_latency_ms(bt) if has_bt else 0
    for s in wired_active():
        d = max(0, (rep_bt - sink_latency_ms(s)) + get_offset(s)) if has_bt else 0
        reload_one(s, d); set_delay(s, d)
    if has_bt: reload_one(bt, BT_KEEPALIVE)
    refresh()
    status.config(text=(f"{get_delay(sel['sink'])} ms · {t('auto_ok')}" if sel["sink"] else t("auto_ok")))

def stop_and_quit(): stop_pulse(); root.destroy()

for key, name, kind in SINKS:
    b = chip(outrow, label_of(key), lambda k=key: toggle_output(k))
    b.pack(side="left", padx=5); Tip(b, t("tip_chip"))
    out_chips[key] = (b, name, kind)

tk.Frame(card, bg=TROUGH, height=1).pack(fill="x", padx=24, pady=(18, 0))
botrow.pack(pady=(12, 8))
b_auto = flat_btn(botrow, t("auto"), auto_sync, accent=True); b_auto.pack(side="left", padx=8); Tip(b_auto, t("tip_auto"))
btn_pulse = flat_btn(botrow, t("pulse"), toggle_pulse); btn_pulse.pack(side="left", padx=8); Tip(btn_pulse, t("tip_pulse"))
b_close = flat_btn(botrow, t("close"), stop_and_quit); b_close.pack(side="left", padx=8); Tip(b_close, t("tip_close"))

root.protocol("WM_DELETE_WINDOW", stop_and_quit)
refresh()
draw_waves()
root.lift(); root.attributes("-topmost", True)
root.after(300, lambda: root.attributes("-topmost", False))
root.mainloop()

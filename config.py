"""Rutas y ajustes (config.json junto al programa)."""
import json
import os
import shutil
import sys

FROZEN = getattr(sys, "frozen", False)
# Donde vive el .exe (o el .py): aquí van config.json, la carpeta de sonidos y el registro de errores
BASE = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))
# Donde están los recursos internos (interfaz, sonidos de ejemplo)
RES = getattr(sys, "_MEIPASS", BASE)
CONFIG_PATH = os.path.join(BASE, "config.json")
# Compatibilidad: si ya existe la carpeta "sonidos" se sigue usando; si no, "sounds"
SOUNDS_DIR = os.path.join(BASE, "sonidos") if os.path.isdir(os.path.join(BASE, "sonidos")) else os.path.join(BASE, "sounds")
DEMO_DIR = os.path.join(RES, "demo_sounds")

DEFAULTS = {
    "mic": "",
    "cable": "",
    "monitor": "",
    "vol_mic": 1.0,
    "vol_call": 0.8,
    "vol_me": 0.6,
    "mic_muted": False,
    "denoise": True,        # reducir ruido del micro (RNNoise) antes de mezclar
    "hotkeys": {},          # acción -> combinación, p. ej. "play:Ding.wav": "ctrl+alt+Digit1"
    "trims": {},            # sonido -> [inicio, fin] en segundos
    "ui": {},               # idioma, tema, orden, tamaño de ventana
}


def ensure_sounds_dir():
    """Primera vez: crea la carpeta de sonidos con los de ejemplo."""
    if not os.path.isdir(SOUNDS_DIR):
        os.makedirs(SOUNDS_DIR, exist_ok=True)
        if os.path.isdir(DEMO_DIR):
            for f in os.listdir(DEMO_DIR):
                shutil.copy2(os.path.join(DEMO_DIR, f), os.path.join(SOUNDS_DIR, f))


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    if not isinstance(cfg.get("hotkeys"), dict):
        cfg["hotkeys"] = {}
    cfg["hotkeys"] = dict(cfg["hotkeys"])
    cfg["trims"] = dict(cfg.get("trims") or {})
    ui = cfg.get("ui") if isinstance(cfg.get("ui"), dict) else {}
    cfg["ui"] = {"lang": "", "theme": "day", "sort_hotkeys": True, "scale": 1.0, **ui}
    return cfg


def save(cfg):
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)

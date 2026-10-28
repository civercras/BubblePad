"""Bubblepad: soundboard que mezcla tu micro y tus sonidos en un solo micro virtual.
Icono junto al reloj + panel (HUD) + motor de audio."""
import json
import os
import shutil
import sys
import traceback

from PySide6.QtCore import QObject, QThread, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMenu, QSystemTrayIcon, QWidget

import config
import vbcable
import i18n
from i18n import t
from engine import AUDIO_EXT, Engine, default_devices, list_devices
from denoise import available as denoise_available
from hotkeys import HotkeyManager

APP_ID = "bubblepad-app"
UI_PATH = os.path.join(config.RES, "ui", "index.html")
BASE_W, BASE_H = 1120, 720
SCALE_MIN, SCALE_MAX = 0.8, 1.2


def log_error(msg):
    try:
        with open(os.path.join(config.BASE, "bubblepad.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


ICON_PATH = os.path.join(config.RES, "assets", "bubblepad.png")


# ── permisos de administrador ──
# Si un juego corre como administrador (p. ej. League of Legends con Vanguard), Windows no deja que
# las pulsaciones hechas en él lleguen a programas normales: los atajos solo funcionan si Bubblepad
# también es administrador.
def is_admin():
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def launch_elevated():
    """Abre otra copia de Bubblepad como administrador (aparece el aviso de Windows). True si se lanzó."""
    if sys.platform != "win32":
        return False
    import ctypes
    hidden = " --hidden" if ("--hidden" in sys.argv or "--oculto" in sys.argv) else ""
    if config.FROZEN:
        exe, args = sys.executable, "--relaunch" + hidden
    else:
        exe = sys.executable
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(pyw):
            exe = pyw
        args = f'"{os.path.abspath(__file__)}" --relaunch' + hidden
    r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, config.BASE, 1)
    return r > 32


# ── arrancar con Windows ──
# Una entrada en HKCU\...\Run (solo para este usuario, sin permisos de administrador).
# Arranca escondido en la bandeja, para que el micro virtual esté listo antes de abrir Discord.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Bubblepad"


def autostart_cmd():
    if config.FROZEN:
        return f'"{sys.executable}" --hidden'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.abspath(__file__)}" --hidden'


def autostart_enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
        return True
    except OSError:
        return False


def set_autostart(on):
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, autostart_cmd())
            else:
                try:
                    winreg.DeleteValue(k, RUN_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as e:
        log_error(f"Arranque con Windows: {e}")
        return False


def bubble_icon(muted=False):
    """Icono de la app (burbuja aqua); en gris cuando el micro está silenciado."""
    img = QPixmap(ICON_PATH).toImage() if os.path.exists(ICON_PATH) else None
    if img is None or img.isNull():
        pm = QPixmap(64, 64)
        pm.fill(QColor(40, 170, 255))
        return QIcon(pm)
    if muted:
        gray = img.convertToFormat(img.Format.Format_Grayscale8).convertToFormat(img.Format.Format_ARGB32)
        gray.setAlphaChannel(img.convertToFormat(img.Format.Format_Alpha8))
        img = gray
    return QIcon(QPixmap.fromImage(img))


class Bridge(QObject):
    """Lo que la interfaz (HTML) puede pedirle a Python."""
    stateChanged = Signal(str)
    levels = Signal(str)
    notice = Signal(str)
    scaleChanged = Signal(float)
    cableProgress = Signal(str, int)
    wavesReady = Signal(str)

    def __init__(self, app):
        super().__init__()
        self.app = app

    @Slot(result=str)
    def getState(self):
        return json.dumps(self.app.state(), ensure_ascii=False)

    @Slot(str, str)
    def setDevice(self, kind, name):
        self.app.set_device(kind, name)

    @Slot(str, float)
    def setVolume(self, kind, value):
        self.app.set_volume(kind, value)

    @Slot(bool)
    def setDenoise(self, on):
        self.app.set_denoise(on)

    @Slot()
    def toggleMute(self):
        self.app.toggle_mute()

    @Slot(str)
    def play(self, sid):
        self.app.engine.play(sid)

    @Slot(str)
    def stop(self, sid):
        self.app.engine.stop(sid or None)

    @Slot(str, str)
    def setHotkey(self, action, combo):
        self.app.set_hotkey(action, combo)

    @Slot(bool)
    def capturing(self, on):
        # mientras eliges una combinación, los atajos se pausan para no dispararlos
        self.app.apply_hotkeys(paused=on)

    @Slot(str, result=str)
    def getWaveform(self, sid):
        try:
            return json.dumps(self.app.engine.waveform(sid))
        except Exception as e:
            return json.dumps({"error": str(e)})

    @Slot(str, float, float)
    def previewTrim(self, sid, start, end):
        self.app.engine.preview(sid, start, end)

    @Slot()
    def stopPreview(self):
        self.app.engine.monitor.stop("__preview__")

    @Slot(str, float, float, float)
    def setTrim(self, sid, start, end, duration):
        self.app.set_trim(sid, start, end, duration)

    @Slot(str, str)
    def setUi(self, key, value):
        ui = self.app.cfg["ui"]
        if key == "theme":
            ui["theme"] = "night" if value == "night" else "day"
        elif key == "sort_hotkeys":
            ui["sort_hotkeys"] = value == "1"
        elif key == "skin":
            ui["skin"] = "aqua" if value == "aqua" else "chrome"
        elif key == "admin_on_start":
            ui["admin_on_start"] = value == "1"
        elif key == "autostart":
            set_autostart(value == "1")
            self.app.push_state()
            return
        elif key == "lang":
            ui["lang"] = value if value in ("es", "en") else "en"
            self.app.set_lang(ui["lang"])
        else:
            return
        config.save(self.app.cfg)

    @Slot(result=float)
    def getScale(self):
        return self.app.window.scale

    @Slot(int)
    def zoomStep(self, direction):
        self.app.window.zoom_step(direction)

    @Slot()
    def resetScale(self):
        self.app.window.set_scale(1.0)

    @Slot()
    def requestWaves(self):
        self.app.request_waves()

    @Slot()
    def installCable(self):
        if sys.platform != "win32":
            self.cableProgress.emit("error:Windows only", 0)
            return
        vbcable.install(lambda stage, pct: self.cableProgress.emit(stage, pct))

    @Slot()
    def openCableWeb(self):
        import webbrowser
        webbrowser.open(vbcable.WEB)

    @Slot()
    def restartPc(self):
        if sys.platform == "win32":
            os.system("shutdown /r /t 5")

    @Slot()
    def relaunchAdmin(self):
        if launch_elevated():
            self.app.quit()
        else:
            self.notice.emit(t("admin_cancel"))

    @Slot()
    def startResize(self):
        self.app.window.start_resize()

    @Slot()
    def startMove(self):
        h = self.app.window.windowHandle()
        if h:
            h.startSystemMove()

    @Slot()
    def minimize(self):
        self.app.window.showMinimized()

    @Slot()
    def hideWindow(self):
        self.app.window.hide()

    @Slot()
    def addSounds(self):
        self.app.add_sounds()

    @Slot()
    def openFolder(self):
        os.makedirs(config.SOUNDS_DIR, exist_ok=True)
        os.startfile(config.SOUNDS_DIR) if hasattr(os, "startfile") else None

    @Slot(str)
    def deleteSound(self, sid):
        self.app.delete_sound(sid)

    @Slot()
    def refresh(self):
        self.app._fails = 0
        self.app.refresh_devices(restart=True)
        self.app.scan_sounds()
        self.app.apply_hotkeys()
        self.app.push_state()


class Window(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Bubblepad")
        self.setWindowIcon(bubble_icon())
        # Skin con forma propia: sin marco de Windows y con fondo transparente
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.scale = 1.0
        self.setFixedSize(BASE_W, BASE_H)
        self.view = QWebEngineView(self)
        self.view.setAttribute(Qt.WA_TranslucentBackground)
        self.view.setStyleSheet("background: transparent")
        self.view.page().setBackgroundColor(Qt.transparent)
        self.view.setContextMenuPolicy(Qt.NoContextMenu)
        s = self.view.settings()
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("bridge", app.bridge)
        self.view.page().setWebChannel(self.channel)
        self.view.load(QUrl.fromLocalFile(UI_PATH))
        self.view.loadFinished.connect(lambda _ok: self.view.setZoomFactor(self.scale))
        self.setCentralWidget(self.view)
        self._resize_timer = QTimer(self)
        self._resize_timer.timeout.connect(self._resize_step)
        self._save_scale = QTimer(self, singleShot=True)
        self._save_scale.timeout.connect(self._persist_scale)
        # Ctrl + rueda lo captura la interfaz y nos pide el cambio (zoomStep). Por si Chromium
        # llegara a hacer zoom por su cuenta, lo devolvemos a la escala correcta.
        self._zoom_guard = QTimer(self)
        self._zoom_guard.timeout.connect(self._fix_zoom)
        self._zoom_guard.start(400)

    # ── tamaño: la ventana y su contenido escalan juntos, nunca se corta ──
    def set_scale(self, sc, keep_center=True):
        sc = round(max(SCALE_MIN, min(SCALE_MAX, sc)), 3)
        if abs(sc - self.scale) < 0.001:
            return
        old = self.geometry()
        self.scale = sc
        w, h = round(BASE_W * sc), round(BASE_H * sc)
        self.setFixedSize(w, h)
        self.view.setZoomFactor(sc)
        if keep_center:
            self.move(old.center().x() - w // 2, old.center().y() - h // 2)
        self._keep_on_screen()
        self.app.bridge.scaleChanged.emit(sc)
        self._save_scale.start(400)

    def _keep_on_screen(self):
        scr = self.screen().availableGeometry() if self.screen() else None
        if not scr:
            return
        g = self.frameGeometry()
        x = min(max(g.x(), scr.left() - 20), scr.right() - g.width() + 20)
        y = min(max(g.y(), scr.top() - 10), scr.bottom() - g.height() + 20)
        if (x, y) != (g.x(), g.y()):
            self.move(x, y)

    def _persist_scale(self):
        self.app.cfg["ui"]["scale"] = self.scale
        config.save(self.app.cfg)

    def start_resize(self):
        """Arrastrar el tirador: seguimos el ratón hasta que se suelta el botón."""
        self._resize_origin = self.geometry().topLeft()
        self._resize_timer.start(16)

    def _resize_step(self):
        if not (QGuiApplication.mouseButtons() & Qt.LeftButton):
            self._resize_timer.stop()
            return
        p = QCursor.pos() - self._resize_origin
        # el tirador está en la esquina inferior derecha (≈ 1076, 650 a escala 1)
        sc = (p.x() / 1076 + p.y() / 650) / 2
        self.set_scale(round(sc / 0.01) * 0.01, keep_center=False)

    def _fix_zoom(self):
        if abs(self.view.zoomFactor() - self.scale) > 0.01:
            self.view.setZoomFactor(self.scale)

    def zoom_step(self, direction):
        self.set_scale(round((self.scale + 0.05 * (1 if direction > 0 else -1)) * 20) / 20)

    def closeEvent(self, e):          # cerrar = esconder en la bandeja
        e.ignore()
        self.hide()


class BubblepadApp:
    def __init__(self, qapp):
        self.qapp = qapp
        self.cfg = config.load()
        if not self.cfg["ui"].get("lang"):
            self.cfg["ui"]["lang"] = i18n.system_lang()
        i18n.set_lang(self.cfg["ui"]["lang"])
        config.ensure_sounds_dir()
        self.engine = Engine()
        self.bridge = Bridge(self)
        self.inputs, self.outputs = [], []
        self.sounds = []

        self.refresh_devices()
        mic, cable, monitor = default_devices()
        cfg = self.cfg
        if cfg["mic"] not in self.inputs:
            cfg["mic"] = mic
        if cfg["cable"] not in self.outputs:
            cfg["cable"] = cable
        if cfg["monitor"] not in self.outputs:
            cfg["monitor"] = monitor
        self.engine.vol_mic = cfg["vol_mic"]
        self.engine.vol_call = cfg["vol_call"]
        self.engine.vol_me = cfg["vol_me"]
        self.engine.mic_muted = cfg["mic_muted"]
        self.engine.denoise_on = bool(cfg.get("denoise", True))
        self.engine.trims = {k: tuple(v) for k, v in cfg["trims"].items()}
        self.engine.start(cfg["mic"], cfg["cable"], cfg["monitor"])
        self.scan_sounds()
        config.save(cfg)

        self.hotkeys = HotkeyManager()
        self.hotkeys.pressed.connect(self._on_hotkey)
        self.hotkeys.failed.connect(self._on_hotkey_failed)
        self.apply_hotkeys()

        self.window = Window(self)
        try:
            self.window.set_scale(float(self.cfg["ui"].get("scale", 1.0)), keep_center=False)
        except (TypeError, ValueError):
            pass
        self._build_tray()

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(60)

        # vigilante: si una salida o el micro se cuelgan (cascos dormidos, reconexión…), se reabren solos
        self.watchdog = QTimer()
        self.watchdog.timeout.connect(self._watch)
        self.watchdog.start(1500)
        self._fails = 0
        self._last_playing = set()
        if not cfg["cable"]:                 # sin VB-CABLE no hay micro virtual: avisamos
            QTimer.singleShot(1500, lambda: self.tray.showMessage(
                t("no_cable_title"), t("no_cable"), QSystemTrayIcon.Warning, 10000))

    # ── bandeja ──
    def _build_tray(self):
        self.tray = QSystemTrayIcon(bubble_icon(self.engine.mic_muted))
        self.tray.setToolTip("Bubblepad")
        menu = QMenu()
        self.a_open = QAction(menu)
        self.a_open.triggered.connect(self.show_window)
        self.a_mute = QAction(menu, checkable=True)
        self.a_mute.setChecked(self.engine.mic_muted)
        self.a_mute.triggered.connect(lambda _=None: self.toggle_mute())
        self.a_stop = QAction(menu)
        self.a_stop.triggered.connect(lambda: self.engine.stop())
        self.a_quit = QAction(menu)
        self.a_quit.triggered.connect(self.quit)
        for a in (self.a_open, self.a_mute, self.a_stop):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(self.a_quit)
        self._retranslate_tray()
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_click)
        self.tray.show()
        self._menu = menu

    def _retranslate_tray(self):
        self.a_open.setText(t("tray_open"))
        self.a_mute.setText(t("tray_mute"))
        self.a_stop.setText(t("tray_stop"))
        self.a_quit.setText(t("tray_quit"))

    def set_lang(self, lang):
        i18n.set_lang(lang)
        self._retranslate_tray()
        config.save(self.cfg)
        self.refresh_devices(restart=True)     # vuelve a generar los avisos de error en el idioma nuevo
        self.push_state()

    def _tray_click(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window()

    def show_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def quit(self):
        self.timer.stop()
        self.watchdog.stop()
        self.hotkeys.stop()
        self.engine.shutdown()
        self.tray.hide()
        self.qapp.quit()

    # ── estado ──
    def refresh_devices(self, restart=False):
        try:
            if restart:
                self.engine.restart_audio()
                self.engine.set_sounds({f: os.path.join(config.SOUNDS_DIR, f) for f in self.sounds})
            self.inputs, self.outputs = list_devices()
        except Exception as e:
            log_error(f"Dispositivos: {e}")

    def _watch(self):
        if self.engine.healthy():
            self._fails = 0
            return
        self._fails += 1
        if self._fails > 5:              # no insistir eternamente si el dispositivo ya no existe
            return
        log_error("Audio colgado: reabriendo dispositivos")
        self.refresh_devices(restart=True)
        self.push_state()

    def delete_sound(self, sid):
        path = os.path.join(config.SOUNDS_DIR, sid)
        if os.path.dirname(os.path.abspath(path)) != os.path.abspath(config.SOUNDS_DIR) or not os.path.isfile(path):
            return
        self.engine.stop(sid)
        try:
            try:
                from send2trash import send2trash
                send2trash(path)              # a la papelera de reciclaje: se puede recuperar
                msg_key = "deleted_trash"
            except ImportError:
                os.remove(path)
                msg_key = "deleted"
        except OSError as e:
            self.bridge.notice.emit(t("delete_fail", err=e))
            return
        self.cfg["hotkeys"].pop("play:" + sid, None)
        self.cfg["trims"].pop(sid, None)
        self.engine.trims.pop(sid, None)
        config.save(self.cfg)
        self.scan_sounds()
        self.apply_hotkeys()
        self.push_state()
        self.bridge.notice.emit(t(msg_key, name=os.path.splitext(sid)[0]))

    def scan_sounds(self):
        os.makedirs(config.SOUNDS_DIR, exist_ok=True)
        files = sorted((f for f in os.listdir(config.SOUNDS_DIR) if f.lower().endswith(AUDIO_EXT)),
                       key=str.lower)
        self.sounds = files
        self.engine.set_sounds({f: os.path.join(config.SOUNDS_DIR, f) for f in files})

    def state(self):
        e = self.engine
        return {
            "inputs": self.inputs, "outputs": self.outputs,
            "mic": e.mic_name, "cable": e.cable_name, "monitor": e.monitor_name,
            "vol_mic": e.vol_mic, "vol_call": e.vol_call, "vol_me": e.vol_me,
            "mic_muted": e.mic_muted,
            "denoise": e.denoise_on, "denoise_ok": denoise_available(),
            "sounds": [{"id": s, "name": os.path.splitext(s)[0]} for s in self.sounds],
            "errors": e.errors,
            "hotkeys": self.cfg["hotkeys"],
            "trims": self.cfg["trims"],
            "ui": self.cfg["ui"],
            "admin": is_admin(),
            "autostart": autostart_enabled(),
            "cable_missing": not any("CABLE INPUT" in o.upper() for o in self.outputs),
        }

    def push_state(self):
        self.bridge.stateChanged.emit(json.dumps(self.state(), ensure_ascii=False))

    def set_device(self, kind, name):
        if kind == "mic":
            self.engine.set_mic(name)
        elif kind == "cable":
            self.engine.set_cable(name)
        elif kind == "monitor":
            self.engine.set_monitor(name)
        else:
            return
        self.cfg[kind] = name
        config.save(self.cfg)
        self.engine.set_sounds({f: os.path.join(config.SOUNDS_DIR, f) for f in self.sounds})
        self.push_state()

    def set_volume(self, kind, value):
        value = max(0.0, min(2.0, float(value)))
        if kind in ("vol_mic", "vol_call", "vol_me"):
            setattr(self.engine, kind, value)
            self.cfg[kind] = value
            self._save_soon()

    def set_denoise(self, on):
        self.engine.set_denoise(on)
        self.cfg["denoise"] = bool(on)
        config.save(self.cfg)
        self.push_state()

    def _save_soon(self):
        if not hasattr(self, "_save_timer"):
            self._save_timer = QTimer(singleShot=True)
            self._save_timer.timeout.connect(lambda: config.save(self.cfg))
        self._save_timer.start(500)

    def toggle_mute(self):
        e = self.engine
        e.mic_muted = not e.mic_muted
        self.cfg["mic_muted"] = e.mic_muted
        config.save(self.cfg)
        self.a_mute.setChecked(e.mic_muted)
        self.tray.setIcon(bubble_icon(e.mic_muted))
        self.push_state()

    # ── mini-ondas para la lista (en segundo plano, con caché) ──
    def request_waves(self):
        import threading
        if getattr(self, "_waves_busy", False):
            return
        self._waves_busy = True
        cache = self.__dict__.setdefault("_waves", {})
        todo = [(sid, tuple(self.cfg["trims"].get(sid, ()))) for sid in self.sounds]

        def work():
            out = {}
            for sid, tr in todo:
                key = (sid, tr)
                if key not in cache:
                    try:
                        cache[key] = self.engine.mini_wave(sid)
                    except Exception:
                        cache[key] = {"peaks": [], "dur": 0}
                out[sid] = cache[key]
            self._waves_busy = False
            self.bridge.wavesReady.emit(json.dumps(out))
        threading.Thread(target=work, daemon=True).start()

    # ── recorte ──
    def set_trim(self, sid, start, end, duration):
        start, end = max(0.0, start), min(duration, end)
        if end - start < 0.02 or (start <= 0.001 and end >= duration - 0.001):
            self.cfg["trims"].pop(sid, None)          # sin recorte
            self.engine.trims.pop(sid, None)
        else:
            self.cfg["trims"][sid] = [round(start, 3), round(end, 3)]
            self.engine.trims[sid] = (start, end)
        config.save(self.cfg)
        self.push_state()

    # ── atajos ──
    def apply_hotkeys(self, paused=False):
        hk = self.cfg["hotkeys"]
        valid = {a: c for a, c in hk.items()
                 if c and (not a.startswith("play:") or a[5:] in self.sounds)}
        self.hotkeys.set_bindings({} if paused else {c: a for a, c in valid.items()})

    def set_hotkey(self, action, combo):
        hk = self.cfg["hotkeys"]
        if combo:
            for a in [a for a, c in hk.items() if c == combo]:   # una combinación = una acción
                del hk[a]
            hk[action] = combo
        else:
            hk.pop(action, None)
        config.save(self.cfg)
        self.apply_hotkeys()
        self.push_state()

    def _on_hotkey(self, action):
        if action.startswith("play:"):
            self.engine.play(action[5:])
        elif action == "stop":
            self.engine.stop()
        elif action == "mute":
            self.toggle_mute()

    def _on_hotkey_failed(self, combos):
        msg = t("hk_taken", combos=combos.replace(",", ", ").replace("+", " + "))
        self.bridge.notice.emit(msg)
        if not self.window.isVisible():
            self.tray.showMessage("Bubblepad", msg, QSystemTrayIcon.Warning, 4000)

    def add_sounds(self):
        files, _ = QFileDialog.getOpenFileNames(
            self.window, t("add_title"), os.path.expanduser("~"),
            "Audio (*.mp3 *.wav *.ogg *.flac)")
        if not files:
            return
        os.makedirs(config.SOUNDS_DIR, exist_ok=True)
        for f in files:
            dest = os.path.join(config.SOUNDS_DIR, os.path.basename(f))
            if os.path.abspath(f) != os.path.abspath(dest):
                shutil.copy2(f, dest)
        self.scan_sounds()
        self.apply_hotkeys()
        self.push_state()

    def _tick(self):
        if not self.window.isVisible():
            return
        playing = self.engine.playing()
        data = {"levels": self.engine.levels(), "playing": sorted(playing), "pos": self.engine.positions()}
        self.bridge.levels.emit(json.dumps(data, ensure_ascii=False))


def main():
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("Bubblepad")

    # "Abrir siempre como administrador": si toca y aún no lo somos, nos relanzamos elevados
    if "--relaunch" not in sys.argv and not is_admin() and config.load()["ui"].get("admin_on_start"):
        if launch_elevated():
            return
    # Al relanzar, esperamos a que la copia anterior termine de cerrarse
    if "--relaunch" in sys.argv:
        for _ in range(40):
            probe = QLocalSocket()
            probe.connectToServer(APP_ID)
            if not probe.waitForConnected(100):
                break
            probe.abort()
            QThread.msleep(150)

    # Una sola copia abierta: si ya está, le pedimos que muestre el panel
    sock = QLocalSocket()
    sock.connectToServer(APP_ID)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        return
    QLocalServer.removeServer(APP_ID)
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.WorldAccessOption)   # visible aunque una copia sea admin y otra no
    server.listen(APP_ID)

    try:
        app = BubblepadApp(qapp)
    except Exception:
        log_error(traceback.format_exc())
        raise

    def on_conn():
        c = server.nextPendingConnection()
        if c:
            c.readyRead.connect(app.show_window)
    server.newConnection.connect(on_conn)

    # Si está activado el arranque con Windows, actualizamos la ruta (por si la carpeta se ha movido)
    if autostart_enabled():
        set_autostart(True)

    if "--oculto" not in sys.argv and "--hidden" not in sys.argv:
        app.show_window()
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()

"""Atajos de teclado globales (funcionan con la ventana minimizada o escondida).

Usa RegisterHotKey de Windows: no espía el teclado, solo pide a Windows que le
avise cuando se pulse una combinación concreta.
"""
import sys
import threading

from PySide6.QtCore import QObject, Signal

IS_WIN = sys.platform == "win32"
if IS_WIN:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

MOD = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_APP_RELOAD = 0x8001
WM_APP_QUIT = 0x8002

# KeyboardEvent.code (de la interfaz) -> tecla virtual de Windows
VK = {f"Key{c}": ord(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
VK.update({f"Digit{i}": 0x30 + i for i in range(10)})
VK.update({f"Numpad{i}": 0x60 + i for i in range(10)})
VK.update({f"F{i}": 0x6F + i for i in range(1, 25)})
VK.update({
    "NumpadMultiply": 0x6A, "NumpadAdd": 0x6B, "NumpadSubtract": 0x6D, "NumpadDecimal": 0x6E,
    "NumpadDivide": 0x6F, "Space": 0x20, "Enter": 0x0D, "Tab": 0x09, "Backspace": 0x08,
    "Insert": 0x2D, "Delete": 0x2E, "Home": 0x24, "End": 0x23, "PageUp": 0x21, "PageDown": 0x22,
    "ArrowLeft": 0x25, "ArrowUp": 0x26, "ArrowRight": 0x27, "ArrowDown": 0x28,
    "Pause": 0x13, "ScrollLock": 0x91, "PrintScreen": 0x2C,
    "Minus": 0xBD, "Equal": 0xBB, "Comma": 0xBC, "Period": 0xBE, "Slash": 0xBF, "Semicolon": 0xBA,
    "Quote": 0xDE, "BracketLeft": 0xDB, "BracketRight": 0xDD, "Backslash": 0xDC, "Backquote": 0xC0,
    "IntlBackslash": 0xE2,
})


def parse(combo):
    """'ctrl+alt+Digit1' -> (mods, vk) o None."""
    parts = [p for p in combo.split("+") if p]
    if not parts or parts[-1] not in VK:
        return None
    mods = 0
    for p in parts[:-1]:
        if p not in MOD:
            return None
        mods |= MOD[p]
    return mods, VK[parts[-1]]


class HotkeyManager(QObject):
    """Hilo propio con su bucle de mensajes. `pressed` llega al hilo de la interfaz."""
    pressed = Signal(str)          # acción, p. ej. "play:Ding.wav", "stop", "mute"
    failed = Signal(str)           # json/texto con combinaciones que Windows no dejó usar

    def __init__(self):
        super().__init__()
        self._wanted = {}          # combo -> acción
        self._lock = threading.Lock()
        self._tid = None
        self._ready = threading.Event()
        if IS_WIN:
            threading.Thread(target=self._loop, daemon=True).start()
            self._ready.wait(2)

    def set_bindings(self, bindings):
        """bindings: dict combo -> acción. Se aplica al momento."""
        with self._lock:
            self._wanted = dict(bindings)
        if IS_WIN and self._tid:
            user32.PostThreadMessageW(self._tid, WM_APP_RELOAD, 0, 0)

    def stop(self):
        if IS_WIN and self._tid:
            user32.PostThreadMessageW(self._tid, WM_APP_QUIT, 0, 0)

    def _loop(self):
        self._tid = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)   # crea la cola de mensajes
        self._ready.set()
        active = {}                                              # id -> acción
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                act = active.get(msg.wParam)
                if act:
                    self.pressed.emit(act)
            elif msg.message == WM_APP_RELOAD:
                for hid in active:
                    user32.UnregisterHotKey(None, hid)
                active.clear()
                with self._lock:
                    wanted = dict(self._wanted)
                bad = []
                for i, (combo, act) in enumerate(wanted.items(), start=1):
                    p = parse(combo)
                    if p and user32.RegisterHotKey(None, i, p[0] | MOD_NOREPEAT, p[1]):
                        active[i] = act
                    else:
                        bad.append(combo)
                if bad:
                    self.failed.emit(",".join(bad))
            elif msg.message == WM_APP_QUIT:
                break
        for hid in active:
            user32.UnregisterHotKey(None, hid)

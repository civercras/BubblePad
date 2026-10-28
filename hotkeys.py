"""Atajos de teclado globales (funcionan con la ventana minimizada o escondida).

Tres vías a la vez, para que funcionen también dentro de juegos:
  1. RegisterHotKey: Windows avisa cuando se pulsa una combinación concreta.
  2. Raw Input (RIDEV_INPUTSINK): Bubblepad lee las teclas aunque no tenga el foco.
     Algunos juegos (p. ej. League of Legends) le piden a Windows que no entregue
     los atajos de RegisterHotKey mientras están delante; esta vía no depende de eso.
     Solo mira las teclas; no las bloquea ni las guarda.
  3. Sondeo: cada 15 ms mira si las teclas de los atajos están pulsadas.
Si las dos detectan la misma pulsación, solo cuenta una vez.
"""
import sys
import threading
import os
import time

from PySide6.QtCore import QObject, Signal

import config


def diag(text):
    """Registro de diagnóstico de atajos (bubblepad.log). Nunca apunta qué teclas se pulsan."""
    try:
        with open(os.path.join(config.BASE, "bubblepad.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "  [atajos] " + text + "\n")
    except Exception:
        pass

IS_WIN = sys.platform == "win32"
if IS_WIN:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32

MOD = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_APP_RELOAD = 0x8001
WM_APP_QUIT = 0x8002
WM_INPUT = 0x00FF
WM_TIMER = 0x0113
RID_INPUT = 0x10000003
RIM_TYPEKEYBOARD = 1
RIDEV_INPUTSINK = 0x00000100
RI_KEY_BREAK = 1
RI_KEY_E0 = 2
HWND_MESSAGE = -3
MOD_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}
# Con Bloq Num apagado el teclado numérico manda flechas/Inicio/Fin... (sin la marca E0)
NAV_TO_NUMPAD = {0x2D: 0x60, 0x23: 0x61, 0x28: 0x62, 0x22: 0x63, 0x25: 0x64, 0x0C: 0x65,
                 0x27: 0x66, 0x24: 0x67, 0x26: 0x68, 0x21: 0x69, 0x2E: 0x6E}
NUMPAD_TO_NAV = {v: k for k, v in NAV_TO_NUMPAD.items()}

if IS_WIN:
    class RAWINPUTDEVICE(ctypes.Structure):
        _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT),
                    ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HWND)]

    class RAWINPUTHEADER(ctypes.Structure):
        _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD),
                    ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]

    class RAWKEYBOARD(ctypes.Structure):
        _fields_ = [("MakeCode", wintypes.USHORT), ("Flags", wintypes.USHORT), ("Reserved", wintypes.USHORT),
                    ("VKey", wintypes.USHORT), ("Message", wintypes.UINT), ("ExtraInformation", wintypes.ULONG)]

    class RAWINPUT(ctypes.Structure):
        _fields_ = [("header", RAWINPUTHEADER), ("keyboard", RAWKEYBOARD)]

    user32.GetRawInputData.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p,
                                       ctypes.POINTER(wintypes.UINT), wintypes.UINT]
    user32.GetRawInputData.restype = wintypes.UINT
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = wintypes.LPARAM
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
    user32.SetTimer.restype = ctypes.c_size_t
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                             ctypes.POINTER(wintypes.DWORD)]


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
        self._active = {}          # (mods, vk) -> acción, lo que está en vigor ahora
        self._last = {}            # acción -> momento del último disparo (para no repetir)
        self._down = set()         # teclas pulsadas según Raw Input
        self._poll_down = set()    # combinaciones pulsadas según el sondeo
        self._fg_hwnd = None
        self._fg_name = "?"
        self._tick = 0
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

    def _fire(self, act, via=""):
        now = time.monotonic()
        if now - self._last.get(act, 0) < 0.25:      # otra vía ya la disparó
            return
        self._last[act] = now
        diag(f"disparado por {via} con delante: {self._fg_name}")
        self.pressed.emit(act)

    # ── Tercera vía: mirar cada 15 ms si las teclas de los atajos están pulsadas ──
    def _poll(self):
        if not self._active:
            return
        ks = user32.GetAsyncKeyState
        def down(vk):
            return bool(ks(vk) & 0x8000)
        mods = 0
        if down(0x11): mods |= MOD["ctrl"]
        if down(0x12): mods |= MOD["alt"]
        if down(0x10): mods |= MOD["shift"]
        if down(0x5B) or down(0x5C): mods |= MOD["win"]
        now_down = set()
        for (m, vk), act in self._active.items():
            alt = NUMPAD_TO_NAV.get(vk)
            if m == mods and (down(vk) or (alt and down(alt))):
                now_down.add((m, vk))
                if (m, vk) not in self._poll_down:
                    self._fire(act, "sondeo")
        self._poll_down = now_down

    def _watch_foreground(self):
        """Apunta qué programa está delante cuando cambia (para saber si Windows nos bloquea)."""
        hwnd = user32.GetForegroundWindow()
        if hwnd == self._fg_hwnd:
            return
        self._fg_hwnd = hwnd
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        name, elev = "?", "?"
        h = kernel32.OpenProcess(0x1000, False, pid.value)          # PROCESS_QUERY_LIMITED_INFORMATION
        if h:
            buf = ctypes.create_unicode_buffer(520)
            n = wintypes.DWORD(520)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                name = os.path.basename(buf.value)
            tok = wintypes.HANDLE()
            if advapi32.OpenProcessToken(h, 0x0008, ctypes.byref(tok)):  # TOKEN_QUERY
                e = wintypes.DWORD()
                ln = wintypes.DWORD()
                if advapi32.GetTokenInformation(tok, 20, ctypes.byref(e), 4, ctypes.byref(ln)):  # TokenElevation
                    elev = "sí" if e.value else "no"
                kernel32.CloseHandle(tok)
            kernel32.CloseHandle(h)
        else:
            name = f"(pid {pid.value}, acceso denegado: error {kernel32.GetLastError()})"
        if name == self._fg_name:
            return
        self._fg_name = name
        diag(f"delante: {name} · administrador: {elev}")

    # ── Raw Input ──
    def _raw_key(self, vk, flags):
        """Una tecla leída por Raw Input. flags: bit0 = soltada, bit1 = tecla extendida (E0)."""
        up = bool(flags & RI_KEY_BREAK)
        ext = bool(flags & RI_KEY_E0)
        if not ext and vk in NAV_TO_NUMPAD:         # teclado numérico con Bloq Num apagado
            vk = NAV_TO_NUMPAD[vk]
        key = (vk, ext)                             # E0 separa Ctrl/Alt derecho del izquierdo
        if up:
            self._down.discard(key)
            return
        if key in self._down:                       # repetición por mantenerla pulsada
            return
        self._down.add(key)
        if vk in MOD_VKS:
            return
        mods = 0
        held = {k[0] for k in self._down}
        if held & {0x11}:
            mods |= MOD["ctrl"]
        if held & {0x12}:
            mods |= MOD["alt"]
        if held & {0x10}:
            mods |= MOD["shift"]
        if held & {0x5B, 0x5C}:
            mods |= MOD["win"]
        act = self._active.get((mods, vk))
        if act:
            self._fire(act, "raw input")

    def _setup_raw(self):
        """Ventana invisible que recibe las teclas aunque Bubblepad no tenga el foco."""
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                           ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                           wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        hwnd = user32.CreateWindowExW(0, "STATIC", "BubblepadKeys", 0, 0, 0, 0, 0,
                                      wintypes.HWND(HWND_MESSAGE), None, None, None)
        if not hwnd:
            return None
        dev = RAWINPUTDEVICE(0x01, 0x06, RIDEV_INPUTSINK, hwnd)   # teclados
        if not user32.RegisterRawInputDevices(ctypes.byref(dev), 1, ctypes.sizeof(RAWINPUTDEVICE)):
            user32.DestroyWindow(hwnd)
            return None
        return hwnd

    def _read_raw(self, lparam):
        size = wintypes.UINT(0)
        hdr = ctypes.sizeof(RAWINPUTHEADER)
        user32.GetRawInputData(ctypes.c_void_p(lparam), RID_INPUT, None, ctypes.byref(size), hdr)
        if not size.value or size.value > 256:
            return
        buf = ctypes.create_string_buffer(size.value)
        if user32.GetRawInputData(ctypes.c_void_p(lparam), RID_INPUT, buf, ctypes.byref(size), hdr) != size.value:
            return
        ri = RAWINPUT.from_buffer_copy(buf.raw[:ctypes.sizeof(RAWINPUT)].ljust(ctypes.sizeof(RAWINPUT), b"\0"))
        if ri.header.dwType == RIM_TYPEKEYBOARD and ri.keyboard.VKey not in (0, 0xFF):
            self._raw_key(ri.keyboard.VKey, ri.keyboard.Flags)

    def _loop(self):
        self._tid = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)   # crea la cola de mensajes
        try:
            raw_hwnd = self._setup_raw()
        except Exception:
            raw_hwnd = None
        self._ready.set()
        try:
            admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            admin = False
        diag(f"inicio · Bubblepad administrador: {'sí' if admin else 'no'} · raw input: {'sí' if raw_hwnd else 'no'}")
        user32.SetTimer(None, 0, 15, None)                       # para el sondeo
        ids = {}                                                 # id -> acción (RegisterHotKey)
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                act = ids.get(msg.wParam)
                if act:
                    self._fire(act, "RegisterHotKey")
            elif msg.message == WM_TIMER:
                try:
                    self._poll()
                    self._tick += 1
                    if self._tick % 30 == 0:                     # ~cada medio segundo
                        self._watch_foreground()
                except Exception as e:
                    if self._tick % 2000 == 1:
                        diag(f"error en sondeo: {e!r}")
            elif msg.message == WM_INPUT:
                try:
                    self._read_raw(msg.lParam)
                except Exception:
                    pass
                user32.DefWindowProcW(msg.hWnd, msg.message, msg.wParam, msg.lParam)
            elif msg.message == WM_APP_RELOAD:
                for hid in ids:
                    user32.UnregisterHotKey(None, hid)
                ids.clear()
                with self._lock:
                    wanted = dict(self._wanted)
                active, bad = {}, []
                for i, (combo, act) in enumerate(wanted.items(), start=1):
                    p = parse(combo)
                    if not p:
                        bad.append(combo)
                        continue
                    active[p] = act
                    if user32.RegisterHotKey(None, i, p[0] | MOD_NOREPEAT, p[1]):
                        ids[i] = act
                    elif not raw_hwnd:                           # sin Raw Input, de verdad no funcionará
                        bad.append(combo)
                self._active = active
                diag(f"{len(active)} atajos activos · {len(ids)} aceptados por RegisterHotKey")
                if bad:
                    self.failed.emit(",".join(bad))
            elif msg.message == WM_APP_QUIT:
                break
        for hid in ids:
            user32.UnregisterHotKey(None, hid)
        if raw_hwnd:
            user32.DestroyWindow(raw_hwnd)

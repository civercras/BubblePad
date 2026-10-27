"""Reducción de ruido del micrófono con RNNoise (Xiph, licencia BSD).

Se aplica SOLO a tu voz, antes de mezclarla con los sonidos. Así puedes quitar la supresión de
ruido de Discord (que borraría tus efectos) sin que se cuele el ruido de fondo de tu micro.

La librería nativa (rnnoise.dll) viene del paquete «pyrnnoise». No importamos ese paquete (arrastra
dependencias pesadas): solo cargamos su DLL con ctypes.
"""
import ctypes
import importlib.util
import os
import sys

import numpy as np

RATE = 48000            # RNNoise trabaja siempre a 48 kHz
_lib = None
_frame = 480            # 10 ms a 48 kHz (se confirma al cargar la librería)
load_error = ""


def _candidates():
    name = {"win32": "rnnoise.dll", "darwin": "librnnoise.dylib"}.get(sys.platform, "librnnoise.so")
    base = getattr(sys, "_MEIPASS", None)
    if base:                                                   # dentro del .exe
        yield os.path.join(base, "rnnoise", name)
        yield os.path.join(base, name)
    here = os.path.dirname(os.path.abspath(__file__))
    yield os.path.join(here, "rnnoise", name)
    try:                                                       # paquete pyrnnoise instalado
        spec = importlib.util.find_spec("pyrnnoise")
        for loc in (spec.submodule_search_locations or []) if spec else []:
            yield os.path.join(loc, name)
    except Exception:
        pass


def _load():
    global _lib, _frame, load_error
    if _lib is not None or load_error:
        return _lib
    for path in _candidates():
        if not os.path.exists(path):
            continue
        try:
            lib = ctypes.CDLL(path)
            lib.rnnoise_create.argtypes = [ctypes.c_void_p]
            lib.rnnoise_create.restype = ctypes.c_void_p
            lib.rnnoise_destroy.argtypes = [ctypes.c_void_p]
            lib.rnnoise_process_frame.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float),
                                                  ctypes.POINTER(ctypes.c_float)]
            lib.rnnoise_process_frame.restype = ctypes.c_float
            lib.rnnoise_get_frame_size.restype = ctypes.c_int
            _frame = int(lib.rnnoise_get_frame_size())
            _lib = lib
            return _lib
        except OSError as e:
            load_error = str(e)
    load_error = load_error or "rnnoise library not found"
    return None


def available():
    return _load() is not None


class Denoiser:
    """Limpia un flujo mono de float32 (-1..1) a cualquier frecuencia.

    Acumula bloques de 10 ms; añade como mucho ~10 ms de retraso. Si el micro no va a 48 kHz,
    se convierte a 48 kHz y de vuelta con interpolación lineal (suficiente para voz)."""

    def __init__(self, rate):
        lib = _load()
        if lib is None:
            raise RuntimeError(load_error)
        self.lib = lib
        self.rate = int(rate)
        self.state = lib.rnnoise_create(None)
        self.pending = np.zeros(0, np.float32)        # entrada a 48 kHz aún sin procesar
        self.buf = np.zeros(_frame, np.float32)
        self.ptr = self.buf.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

    def close(self):
        if self.state:
            self.lib.rnnoise_destroy(self.state)
            self.state = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    @staticmethod
    def _resample(x, src, dst):
        """Conversión lineal de un bloque (pequeños desfases entre bloques: inaudibles en voz)."""
        if src == dst or len(x) < 2:
            return x
        n = max(1, int(round(len(x) * dst / src)))
        return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

    def process(self, mono):
        """Devuelve la voz limpia. Puede devolver algo menos (o más) que la entrada mientras se
        llena el primer bloque de 10 ms; el búfer del motor absorbe esa diferencia."""
        if not self.state:
            return mono
        x48 = self._resample(np.asarray(mono, np.float32), self.rate, RATE)
        self.pending = np.concatenate((self.pending, x48)) if len(self.pending) else x48
        f = _frame
        k = len(self.pending) // f
        if k == 0:
            return np.zeros(0, np.float32)
        out = np.empty(k * f, np.float32)
        for i in range(k):
            self.buf[:] = self.pending[i * f:(i + 1) * f] * 32768.0
            self.lib.rnnoise_process_frame(self.state, self.ptr, self.ptr)
            out[i * f:(i + 1) * f] = self.buf * (1.0 / 32768.0)
        self.pending = self.pending[k * f:].copy()
        return self._resample(out, RATE, self.rate)

"""Motor de audio.

Tres caminos:
  micro real  ─┐
               ├─► CABLE Input  (lo que oye Discord: tu voz + sonidos)
  sonidos ─────┤
               └─► tus cascos   (solo los sonidos, tu voz NO para no oírte con eco)
"""
import threading
import time

import miniaudio
import numpy as np
import sounddevice as sd

import denoise
from i18n import t

AUDIO_EXT = (".mp3", ".wav", ".ogg", ".flac")


# ───────────────────────── dispositivos ─────────────────────────

def _wasapi_index():
    for i, api in enumerate(sd.query_hostapis()):
        if "WASAPI" in api["name"]:
            return i
    return None


def list_devices():
    """Entradas y salidas (en Windows solo WASAPI, que es la de menor retraso).
    OJO: no reinicia PortAudio; para ver dispositivos nuevos usa Engine.restart_audio()."""
    api = _wasapi_index()
    ins, outs = [], []
    for i, d in enumerate(sd.query_devices()):
        if api is not None and d["hostapi"] != api:
            continue
        if d["max_input_channels"] > 0:
            ins.append(d["name"])
        if d["max_output_channels"] > 0:
            outs.append(d["name"])
    return ins, outs


def _find(name, kind):
    """Índice del dispositivo por nombre (los índices cambian, los nombres no)."""
    api = _wasapi_index()
    key = "max_input_channels" if kind == "in" else "max_output_channels"
    for i, d in enumerate(sd.query_devices()):
        if api is not None and d["hostapi"] != api:
            continue
        if d[key] > 0 and d["name"] == name:
            return i
    return None


def default_devices():
    """Elige micro real, CABLE y cascos automáticamente."""
    ins, outs = list_devices()
    api = _wasapi_index()
    if api is not None:
        info = sd.query_hostapis(api)
        din, dout = info["default_input_device"], info["default_output_device"]
    else:
        din, dout = sd.default.device
    devs = sd.query_devices()
    name_in = devs[din]["name"] if din is not None and din >= 0 else ""
    name_out = devs[dout]["name"] if dout is not None and dout >= 0 else ""

    mic = name_in if name_in and "CABLE" not in name_in.upper() else next(
        (n for n in ins if "CABLE" not in n.upper()), "")
    cable = next((n for n in outs if "CABLE INPUT" in n.upper()), "")
    monitor = name_out if name_out and "CABLE" not in name_out.upper() else next(
        (n for n in outs if "CABLE" not in n.upper()), "")
    return mic, cable, monitor


# ───────────────────────── piezas ─────────────────────────

class Ring:
    """Búfer circular mono para pasar el micro de un dispositivo a otro."""

    def __init__(self, size):
        self.buf = np.zeros(size, np.float32)
        self.size = size
        self.r = self.w = self.n = 0
        self.lock = threading.Lock()

    def clear(self):
        with self.lock:
            self.r = self.w = self.n = 0

    def write(self, x):
        with self.lock:
            k = len(x)
            if k >= self.size:
                x, k = x[-self.size:], self.size
            over = self.n + k - self.size
            if over > 0:                       # lleno: tiramos lo más viejo
                self.r = (self.r + over) % self.size
                self.n -= over
            e = self.w + k
            if e <= self.size:
                self.buf[self.w:e] = x
            else:
                c = self.size - self.w
                self.buf[self.w:] = x[:c]
                self.buf[:k - c] = x[c:]
            self.w = e % self.size
            self.n += k

    def read(self, k, keep_max):
        """Lee k muestras; si se acumula retraso (relojes distintos), lo recorta."""
        out = np.zeros(k, np.float32)
        with self.lock:
            if self.n > keep_max + k:
                drop = self.n - keep_max
                self.r = (self.r + drop) % self.size
                self.n -= drop
            if self.n < k:                     # aún no hay bastante: esperamos un bloque
                return out                     # (mejor un silencio entero que voz a trozos)
            m = k
            e = self.r + m
            if e <= self.size:
                out[:m] = self.buf[self.r:e]
            else:
                c = self.size - self.r
                out[:c] = self.buf[self.r:]
                out[c:m] = self.buf[:m - c]
            self.r = e % self.size
            self.n -= m
        return out


class Voice:
    __slots__ = ("data", "pos", "sid")

    def __init__(self, data, sid):
        self.data, self.pos, self.sid = data, 0, sid


class Sink:
    """Una salida de audio (CABLE o cascos) con sus sonidos sonando."""

    def __init__(self, engine, name, with_mic):
        self.engine, self.name, self.with_mic = engine, name, with_mic
        self.voices = []
        self.lock = threading.Lock()
        self.stream = None
        self.rate, self.ch = 48000, 2
        self.peak = 0.0
        self.last_cb = 0.0

    def open(self):
        self.close()
        idx = _find(self.name, "out")
        if idx is None:
            raise RuntimeError(t("no_output", name=self.name))
        d = sd.query_devices(idx)
        self.rate = int(d["default_samplerate"])
        self.ch = min(2, d["max_output_channels"])
        self.stream = sd.OutputStream(device=idx, samplerate=self.rate, channels=self.ch,
                                      dtype="float32", latency="low", callback=self._cb)
        self.last_cb = time.monotonic()
        self.stream.start()

    def close(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        with self.lock:
            self.voices.clear()

    def add(self, data, sid):
        with self.lock:
            self.voices.append(Voice(data, sid))

    def stop(self, sid=None):
        with self.lock:
            self.voices = [] if sid is None else [v for v in self.voices if v.sid != sid]

    def playing(self):
        with self.lock:
            return {v.sid for v in self.voices}

    def alive(self):
        """¿Sigue Windows pidiéndonos audio? Si no, la salida se ha colgado."""
        if self.stream is None:
            return True
        try:
            active = self.stream.active
        except Exception:
            active = False
        return active and time.monotonic() - self.last_cb < 2.0

    def _cb(self, outdata, frames, _t, _status):
        self.last_cb = time.monotonic()
        eng = self.engine
        out = np.zeros((frames, self.ch), np.float32)
        gain = eng.vol_call if self.with_mic else eng.vol_me
        with self.lock:
            alive = []
            for v in self.voices:
                chunk = v.data[v.pos:v.pos + frames]
                out[:len(chunk)] += chunk * (gain * eng.gain_of(v.sid))
                v.pos += frames
                if v.pos < len(v.data):
                    alive.append(v)
            self.voices = alive
        if self.with_mic:
            mic = eng.mic_for(frames, self.rate)
            if mic is not None:
                out += mic[:, None]
        np.clip(out, -1.0, 1.0, out=out)
        self.peak = max(self.peak * 0.85, float(np.abs(out).max()) if frames else 0.0)
        outdata[:] = out


# ───────────────────────── motor ─────────────────────────

class Engine:
    def __init__(self):
        self.mic_name = self.cable_name = self.monitor_name = ""
        self.vol_mic = 1.0      # tu voz hacia Discord
        self.vol_call = 0.8     # sonidos hacia Discord
        self.vol_me = 0.6       # sonidos en tus cascos
        self.mic_muted = False
        self.denoise_on = True  # limpia tu voz antes de mezclarla (RNNoise)
        self._denoiser = None
        self.sound_gain = {}    # volumen por sonido (más adelante)
        self.trims = {}         # sid -> (inicio_s, fin_s); el archivo original no se toca
        self.mic_peak = 0.0
        self.errors = {}

        self._mic_stream = None
        self._mic_rate = 48000
        self._mic_last = 0.0
        self._ring = Ring(48000 * 2)
        self._resample_src_pos = 0.0
        self.cable = Sink(self, "", True)
        self.monitor = Sink(self, "", False)

        self._paths = {}        # sid -> ruta
        self._cache = {}        # (sid, rate, ch) -> array
        self._cache_lock = threading.Lock()

    # ── configuración ──
    def start(self, mic, cable, monitor):
        self.set_mic(mic)
        self.set_cable(cable)
        self.set_monitor(monitor)

    def set_mic(self, name):
        self.mic_name = name
        if self._mic_stream is not None:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None
        self._ring.clear()
        self.errors.pop("mic", None)
        if not name:
            return
        try:
            idx = _find(name, "in")
            if idx is None:
                raise RuntimeError(t("no_mic", name=name))
            d = sd.query_devices(idx)
            self._mic_rate = int(d["default_samplerate"])
            self._make_denoiser()
            ch = min(2, d["max_input_channels"])
            self._mic_stream = sd.InputStream(device=idx, samplerate=self._mic_rate, channels=ch,
                                              dtype="float32", latency="low", callback=self._mic_cb)
            self._mic_last = time.monotonic()
            self._mic_stream.start()
        except Exception as e:
            self.errors["mic"] = str(e)

    def _make_denoiser(self):
        # no se cierra a mano: el hilo de audio puede estar usándolo; se libera solo al soltarlo
        self._denoiser = None
        if self.denoise_on and denoise.available():
            try:
                self._denoiser = denoise.Denoiser(self._mic_rate)
            except Exception as e:
                self.errors["denoise"] = str(e)

    def set_denoise(self, on):
        self.denoise_on = bool(on)
        self.errors.pop("denoise", None)
        self._make_denoiser()

    def set_cable(self, name):
        self.cable_name = self.cable.name = name
        self._open_sink(self.cable, "cable")

    def set_monitor(self, name):
        self.monitor_name = self.monitor.name = name
        self._open_sink(self.monitor, "monitor")

    def _open_sink(self, sink, key):
        self.errors.pop(key, None)
        if not sink.name:
            sink.close()
            return
        try:
            sink.open()
        except Exception as e:
            sink.close()
            self.errors[key] = str(e)

    def restart_audio(self):
        """Cierra todo, reinicia PortAudio (ve dispositivos nuevos) y vuelve a abrir."""
        names = (self.mic_name, self.cable_name, self.monitor_name)
        self.shutdown()
        try:
            sd._terminate()
        except Exception:
            pass
        sd._initialize()
        self.start(*names)

    def healthy(self):
        mic_ok = True
        if self._mic_stream is not None:
            try:
                mic_ok = self._mic_stream.active and time.monotonic() - self._mic_last < 2.0
            except Exception:
                mic_ok = False
        return mic_ok and self.cable.alive() and self.monitor.alive()

    def shutdown(self):
        self.set_mic("")
        self.cable.close()
        self.monitor.close()

    # ── micrófono ──
    def _mic_cb(self, indata, _frames, _t, _status):
        self._mic_last = time.monotonic()
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        dn = self._denoiser
        if dn is not None:
            try:
                mono = dn.process(mono)
            except Exception:
                self._denoiser = None                     # si falla, seguimos sin limpiar antes que cortar la voz
        self.mic_peak = max(self.mic_peak * 0.85, float(np.abs(mono).max()) if len(mono) else 0.0)
        self._ring.write(mono.astype(np.float32, copy=False))

    def mic_for(self, frames, out_rate):
        """Trozo de micro listo para mezclar en el CABLE (o None si está silenciado)."""
        if self._mic_stream is None:
            return None
        keep = int(self._mic_rate * 0.04)              # máx. 40 ms de retraso acumulado
        if out_rate == self._mic_rate:
            x = self._ring.read(frames, keep)
        else:                                          # distinta frecuencia: reajuste lineal
            want = frames * self._mic_rate / out_rate + self._resample_src_pos
            need = max(1, int(want))
            self._resample_src_pos = want - need
            src = self._ring.read(need, keep)
            x = np.interp(np.linspace(0, need - 1, frames), np.arange(need), src).astype(np.float32)
        if self.mic_muted:
            return None
        return x * self.vol_mic

    # ── sonidos ──
    def set_sounds(self, paths):
        """paths: dict sid -> ruta. Precarga en segundo plano."""
        self._paths = dict(paths)
        with self._cache_lock:
            self._cache = {k: v for k, v in self._cache.items() if k[0] in self._paths}
        threading.Thread(target=self._preload, daemon=True).start()

    def _preload(self):
        for sid in list(self._paths):
            for sink in (self.cable, self.monitor):
                try:
                    self._decoded(sid, sink.rate, sink.ch)
                except Exception:
                    pass

    def _decoded(self, sid, rate, ch):
        key = (sid, rate, ch)
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]
        with open(self._paths[sid], "rb") as f:      # leer en Python: evita líos con tildes en rutas
            raw = f.read()
        dec = miniaudio.decode(raw, output_format=miniaudio.SampleFormat.FLOAT32,
                               nchannels=ch, sample_rate=rate)
        arr = np.frombuffer(dec.samples, dtype=np.float32).reshape(-1, ch).copy()
        with self._cache_lock:
            self._cache[key] = arr
        return arr

    def gain_of(self, sid):
        return self.sound_gain.get(sid, 1.0)

    def _trimmed(self, sid, sink, start=None, end=None):
        data = self._decoded(sid, sink.rate, sink.ch)
        if start is None:
            start, end = self.trims.get(sid, (0.0, None))
        a = max(0, int(start * sink.rate))
        b = len(data) if end is None else min(len(data), int(end * sink.rate))
        return data[a:max(a, b)]

    def play(self, sid):
        if sid not in self._paths:
            return False
        ok = False
        for sink in (self.cable, self.monitor):
            if sink.stream is None:
                continue
            try:
                sink.add(self._trimmed(sid, sink), sid)
                ok = True
            except Exception as e:
                self.errors["sound"] = t("cant_read", name=sid, err=e)
        return ok

    # ── recorte ──
    WAVE_RATE = 16000

    def waveform(self, sid, buckets=900):
        """Picos para dibujar la onda + propuesta automática de recorte de silencios."""
        mono = self._decoded(sid, self.WAVE_RATE, 1)[:, 0]
        dur = len(mono) / self.WAVE_RATE
        n = max(1, len(mono) // buckets)
        usable = mono[:n * (len(mono) // n)].reshape(-1, n) if len(mono) >= n else mono.reshape(1, -1)
        peaks = np.abs(usable).max(axis=1)
        top = float(peaks.max()) if len(peaks) else 0.0
        a, b = self.auto_trim(mono, self.WAVE_RATE)
        start, end = self.trims.get(sid, (0.0, dur))
        return {"duration": dur, "peaks": [round(float(x / top), 3) if top else 0 for x in peaks],
                "start": start, "end": end if end is not None else dur, "auto": [a, b]}

    @staticmethod
    def auto_trim(mono, rate):
        """Busca dónde empieza y acaba el sonido de verdad (ventanas de 10 ms, umbral relativo)."""
        if not len(mono):
            return 0.0, 0.0
        w = max(1, rate // 100)
        k = len(mono) // w
        if k == 0:
            return 0.0, len(mono) / rate
        rms = np.sqrt((mono[:k * w].reshape(k, w) ** 2).mean(axis=1))
        thr = max(float(rms.max()) * 0.03, 10 ** (-55 / 20))       # ~ -30 dB bajo el pico, mínimo -55 dBFS
        loud = np.nonzero(rms > thr)[0]
        if not len(loud):
            return 0.0, len(mono) / rate
        a = max(0.0, loud[0] * w / rate - 0.02)                     # 20 ms de margen al empezar
        b = min(len(mono) / rate, (loud[-1] + 1) * w / rate + 0.08)  # 80 ms al acabar (colas suaves)
        return round(float(a), 3), round(float(b), 3)

    def preview(self, sid, start, end):
        """Escucha la zona elegida solo en tus cascos (Discord no la oye)."""
        self.monitor.stop("__preview__")
        if sid in self._paths and self.monitor.stream is not None:
            self.monitor.add(self._trimmed(sid, self.monitor, start, end), "__preview__")

    def stop(self, sid=None):
        self.cable.stop(sid)
        self.monitor.stop(sid)

    def playing(self):
        return self.cable.playing() | self.monitor.playing()

    def levels(self):
        lv = {"mic": 0.0 if self.mic_muted else min(1.0, self.mic_peak * self.vol_mic),
              "call": min(1.0, self.cable.peak), "me": min(1.0, self.monitor.peak)}
        self.mic_peak *= 0.7
        self.cable.peak *= 0.7
        self.monitor.peak *= 0.7
        return lv

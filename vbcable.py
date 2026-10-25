"""Instalación de VB-CABLE en un clic.

VB-CABLE es donationware de VB-Audio y no se redistribuye dentro de Bubblepad:
se descarga en el momento desde la web oficial y se abre su propio instalador.
"""
import os
import re
import sys
import tempfile
import threading
import urllib.request
import zipfile

URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"   # respaldo
WEB = "https://vb-audio.com/Cable/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bubblepad"}


def latest_url():
    """Busca en la web oficial el enlace al paquete más reciente (por si sacan una versión nueva)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(WEB, headers=UA), timeout=15) as r:
            html = r.read().decode("utf-8", "ignore")
        packs = re.findall(r"https://download\.vb-audio\.com/Download_CABLE/VBCABLE_Driver_Pack(\d+)\.zip", html)
        if packs:
            v = max(int(x) for x in packs)
            return f"https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack{v}.zip"
    except Exception:
        pass
    return URL


def run_elevated_and_wait(exe, cwd):
    """Abre `exe` como administrador (aviso de Windows) y espera a que termine. Devuelve True si se ejecutó."""
    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD), ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]

    SEE_MASK_NOCLOSEPROCESS = 0x40
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = exe
    info.lpDirectory = cwd
    info.nShow = 1
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        return False                                   # el usuario dijo que no al aviso de Windows
    if info.hProcess:
        ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        ctypes.windll.kernel32.CloseHandle(info.hProcess)
    return True


def install(progress):
    """progress(stage, pct) se llama desde un hilo aparte.
    Etapas: download, extract, installer, done, cancelled, error:<texto>"""
    def work():
        try:
            folder = os.path.join(tempfile.gettempdir(), "bubblepad_vbcable")
            os.makedirs(folder, exist_ok=True)
            zpath = os.path.join(folder, "VBCABLE_Driver_Pack.zip")
            progress("download", 0)
            req = urllib.request.Request(latest_url(), headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r, open(zpath, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = r.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        progress("download", int(done * 100 / total))
            progress("extract", 100)
            with zipfile.ZipFile(zpath) as z:
                z.extractall(folder)
            setup = "VBCABLE_Setup_x64.exe" if sys.maxsize > 2 ** 32 else "VBCABLE_Setup.exe"
            exe = os.path.join(folder, setup)
            if not os.path.exists(exe):
                raise FileNotFoundError(setup)
            progress("installer", 100)
            ok = run_elevated_and_wait(exe, folder)
            progress("done" if ok else "cancelled", 100)
        except Exception as e:                       # sin internet, web cambiada, etc.
            progress("error:" + str(e), 0)
    threading.Thread(target=work, daemon=True).start()

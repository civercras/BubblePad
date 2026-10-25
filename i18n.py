"""Textos de la parte Python (bandeja, avisos, errores) en español e inglés.
La interfaz web tiene su propio diccionario en ui/index.html."""
STRINGS = {
    "es": {
        "tray_open": "Abrir Bubblepad",
        "tray_mute": "Silenciar micrófono",
        "tray_stop": "Parar todos los sonidos",
        "tray_quit": "Salir",
        "admin_cancel": "No se ha reiniciado: hacen falta permisos de administrador",
        "add_title": "Añadir sonidos",
        "hk_taken": "Otra aplicación ya usa: {combos}",
        "deleted_trash": "«{name}» enviado a la papelera",
        "deleted": "«{name}» borrado",
        "delete_fail": "No he podido eliminarlo: {err}",
        "no_output": "No encuentro la salida «{name}»",
        "no_mic": "No encuentro el micrófono «{name}»",
        "cant_read": "No puedo leer {name}: {err}",
        "no_cable_title": "Falta el micro virtual",
        "no_cable": "No encuentro VB-CABLE. Instálalo gratis desde vb-audio.com/Cable, reinicia y vuelve a abrir Bubblepad.",
    },
    "en": {
        "tray_open": "Open Bubblepad",
        "tray_mute": "Mute microphone",
        "tray_stop": "Stop all sounds",
        "tray_quit": "Quit",
        "admin_cancel": "Not restarted: administrator permission is needed",
        "add_title": "Add sounds",
        "hk_taken": "Another app is already using: {combos}",
        "deleted_trash": "“{name}” moved to the Recycle Bin",
        "deleted": "“{name}” deleted",
        "delete_fail": "Couldn't delete it: {err}",
        "no_output": "Can't find the output “{name}”",
        "no_mic": "Can't find the microphone “{name}”",
        "cant_read": "Can't read {name}: {err}",
        "no_cable_title": "Virtual mic missing",
        "no_cable": "VB-CABLE wasn't found. Install it for free from vb-audio.com/Cable, restart and open Bubblepad again.",
    },
}
LANG = "es"


def set_lang(lang):
    global LANG
    LANG = lang if lang in STRINGS else "en"


def system_lang():
    try:
        from PySide6.QtCore import QLocale
        return "es" if QLocale.system().name().lower().startswith("es") else "en"
    except Exception:
        return "en"


def t(key, **kw):
    s = STRINGS.get(LANG, STRINGS["en"]).get(key) or STRINGS["en"].get(key, key)
    return s.format(**kw) if kw else s

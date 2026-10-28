**Free Windows soundboard that plays sounds through your mic.** Mixes your microphone and sound effects into one virtual mic for Discord, games and voice chat.

### Which file do I download?
- **`Bubblepad-Setup.exe` (recommended):** installer. Installs Bubblepad for your user, no admin rights needed, with a Start menu shortcut and an uninstaller.
- **`Bubblepad-windows.zip`:** portable version. Unzip it anywhere and run `Bubblepad.exe`; nothing gets installed.

### What's new in v0.4.0
- **Sound pages.** Organise your sounds in tabs (each tab is just a subfolder of your sounds folder). Create one with **+**, and drag a sound onto a tab to move it: it follows your cursor with a bit of spring and the tab gulps it in.
- **Many sounds, few keys.** Each page has its own sound hotkeys, so `Ctrl + Num1` can play one sound on *Memes* and another on *Ranked*. Give each page its own hotkey (right-click its tab, e.g. F1, F2…) or set *Next / previous page* in ⚙. When you switch page with a hotkey you hear a soft bubble pop only you can hear (one pop for page 1, two for page 2…), so you know where you are mid-game.
- **Hotkeys now work inside League of Legends** and other games that tell Windows to ignore app shortcuts, without needing administrator rights.
- **Numpad hotkeys work with Num Lock off.**
- **Start with Windows** (⚙ → *When your PC starts*): opens hidden in the tray, so the virtual mic is always ready and Discord never needs reconfiguring.

### Since v0.3.0
- **Chrome look by default:** a silver 2000s media-player chassis with a pixel LCD, a playlist with real waveforms and a graphite/amber night mode. The bubbly Aqua look is still in ⚙ → *Look*.
- **Built-in noise reduction (RNNoise)**, a visual **connections panel** and the **installer** (v0.2.0).

### Get started
1. Open Bubblepad. No VB-CABLE yet? It offers to install it in one click (official installer from vb-audio.com → press *Install Driver*), then restart your PC.
2. In Discord or your game, set the microphone to **CABLE Output**.
3. Turn off Discord's noise suppression: Bubblepad already cleans your voice.

### Good to know
- A hotkey still doesn't reach a game that runs as administrator? ⚙ → *Games* → **Restart as administrator**.
- Windows may show a blue SmartScreen warning because the app isn't code-signed yet: *More info → Run anyway*.
- Your sound files are never modified; trims are stored in `config.json`.

---
**Español:** descarga **Bubblepad-Setup.exe** (instalador, recomendado) o el **.zip** portable. Novedades de la v0.4.0:
- **Páginas de sonidos** en pestañas. Cada una es una subcarpeta. Arrastra un sonido a una pestaña para moverlo.
- **Atajos propios en cada página**, así con pocas teclas tienes muchos sonidos. Para cambiar de página, ponle un atajo a cada una (clic derecho en la pestaña) o usa «Página siguiente/anterior». Al cambiar con un atajo, solo tú oyes un «plop» de burbuja.
- **Los atajos funcionan dentro del LoL** sin ser administrador, y los del teclado numérico también con Bloq Num apagado.
- **Opción de abrir Bubblepad al encender el PC**, escondido en la bandeja.

En Discord elige **CABLE Output** como micrófono y quita su supresión de ruido.

"""Genera la landing de Bubblepad (EN + ES) desde una sola plantilla.

python build.py preview  -> index.html (sin <head>, para la vista previa) + es.html
python build.py pages    -> site/index.html + site/es/index.html (documentos completos para GitHub Pages)
"""
import html, json, os, sys

SITE = "https://civercras.github.io/BubblePad/"
REPO = "https://github.com/civercras/BubblePad"
DL = REPO + "/releases/latest/download/Bubblepad-Setup.exe"
ZIP = REPO + "/releases/latest/download/Bubblepad-windows.zip"
VERSION = "0.5.0"

T = {
"en": dict(
  lang="en", other="es", other_label="Español",
  title="Bubblepad · Free soundboard for Discord and games (Windows)",
  desc="Play sounds through your mic in Discord and games, and hear them yourself. Free, open-source Windows soundboard with hotkeys that work in-game, sound pages and built-in noise reduction.",
  nav=["How it works","Features","FAQ"],
  eyebrow="FREE · WINDOWS 10/11 · OPEN SOURCE",
  h1="The soundboard for voice chat and gaming.",
  lead="Play sound effects through your mic in Discord and in-game voice chat, with hotkeys that work while you play. Your friends hear the airhorn, and so do you. Free, no account, no ads.",
  cta="Download for Windows", cta2="View on GitHub",
  meta=f"v{VERSION} · installer, about 170 MB · sets up VB-CABLE in one click",
  lcd_now="NOW PLAYING", lcd_song="AIRHORN",
  how_t="How it works", how_lead="Three things, connected once. After that you just press a key.",
  steps=[("Your mic and your sounds","Drop in MP3, WAV, OGG or FLAC files. Bubblepad cleans your voice with built-in noise reduction."),
         ("Bubblepad mixes them","Voice and sounds go into CABLE Input, a free virtual cable from VB-Audio. Bubblepad offers to install it if it's missing."),
         ("Pick CABLE Output in Discord","Set it as your microphone in Discord or your game, once. Your headphones get the sounds, without your own voice.")],
  cable_labels=["YOUR VOICE","THE CALL","SOUNDS FOR YOU"],
  feat_t="Built for voice chat", feat=[
   ("Hotkeys that work in-game","Global hotkeys keep working while you play. Tested in League of Legends and ARC Raiders, including games that block normal app shortcuts."),
   ("Pages: many sounds, few keys","Each page has its own hotkeys. Ctrl + Num1 can be a meme on one page and a jingle on another. A soft pop tells you which page you're on."),
   ("Noise reduction for your voice","RNNoise cleans your mic before it's mixed, so you can turn off Discord's suppression without it eating your sound effects."),
   ("Trim and remove silence","A waveform editor with one-click silence removal. Your original files are never modified."),
   ("You hear the sounds, not yourself","Separate volumes for your voice, sounds in the call and sounds in your headphones."),
   ("Starts with Windows","Optional. It opens hidden in the tray, so the virtual mic is ready before Discord is."),
  ],
  shots=[("connections","The connections panel: pick each device and see the signal on the cables."),
         ("trim","The trim editor removes silence at the start and end of a sound."),
         ("night","Night mode: graphite chassis with amber screens.")],
  demo_t="13 seconds of Bubblepad",
  faq_t="Questions", faq=[
   ("How do I play sounds through my mic in Discord?","Install Bubblepad, open it and let it set up VB-CABLE if you don't have it. In Discord go to User Settings → Voice & Video and choose CABLE Output as your input device. Everything Bubblepad plays now reaches the call together with your voice."),
   ("Is Bubblepad really free?","Yes. It's open source under the MIT license, with no account, no ads, no trial and no paid tier. The code is on GitHub."),
   ("Does it work in games?","Yes, in any game or app that lets you choose a microphone. The hotkeys are global and work while the game is focused. If a game runs as administrator, turn on “Restart as administrator” in Bubblepad's settings."),
   ("Why does Windows show a SmartScreen warning?","The app isn't code-signed yet, which costs money for a free project. Click More info → Run anyway. The installer is built automatically on GitHub from the public source code."),
   ("My voice sounds doubled or noisy in Discord.","Windows is probably also sending your mic to the cable. Press Win + R, type mmsys.cpl, open Recording → your microphone → Listen, and untick “Listen to this device”."),
   ("Do I need Discord's noise suppression?","No, turn it off. Discord can't tell your sound effects from background noise and filters them out. Bubblepad cleans your voice before mixing it."),
   ("Which formats and systems are supported?","MP3, WAV, OGG and FLAC on Windows 10 and 11 (64-bit)."),
  ],
  end_t="Ready when your friends are.", end_lead="Free download for Windows 10 and 11.",
  portable="Portable .zip",
  foot_by="Made by Pablo Grasa", foot_lic="MIT license", foot_src="Source code", foot_issues="Report a problem",
  vb_note="VB-CABLE is a separate free driver by VB-Audio.",
  img_alt_day="Bubblepad soundboard window with the sound playlist, waveforms and hotkeys",
  img_alt_night="Bubblepad in night mode",
),
"es": dict(
  lang="es", other="en", other_label="English",
  title="Bubblepad · Soundboard gratis para Discord y juegos (Windows)",
  desc="Haz que tus sonidos suenen por el micro en Discord y en juegos, y escúchalos tú también. Soundboard gratis y de código abierto para Windows, con atajos que funcionan en partida, páginas de sonidos y reducción de ruido.",
  nav=["Cómo funciona","Funciones","Preguntas"],
  eyebrow="GRATIS · WINDOWS 10/11 · CÓDIGO ABIERTO",
  h1="La soundboard para chats de voz y partidas.",
  lead="Haz sonar efectos por tu micro en Discord y en el chat de voz de tus juegos, con atajos que funcionan mientras juegas. Tus amigos oyen la bocina, y tú también. Gratis, sin cuenta y sin anuncios.",
  cta="Descargar para Windows", cta2="Ver en GitHub",
  meta=f"v{VERSION} · instalador de unos 170 MB · instala VB-CABLE con un clic",
  lcd_now="SONANDO", lcd_song="BOCINA",
  how_t="Cómo funciona", how_lead="Tres cosas que se conectan una vez. Después solo pulsas una tecla.",
  steps=[("Tu micro y tus sonidos","Añade archivos MP3, WAV, OGG o FLAC. Bubblepad limpia tu voz con reducción de ruido integrada."),
         ("Bubblepad los mezcla","La voz y los sonidos van a CABLE Input, un cable virtual gratuito de VB-Audio. Si no lo tienes, Bubblepad te ofrece instalarlo."),
         ("Elige CABLE Output en Discord","Ponlo como micrófono en Discord o en tu juego, una sola vez. En tus cascos oyes los sonidos, sin tu propia voz.")],
  cable_labels=["TU VOZ","LA LLAMADA","SONIDOS PARA TI"],
  feat_t="Pensado para el chat de voz", feat=[
   ("Atajos que funcionan en partida","Los atajos globales siguen funcionando mientras juegas. Probado en League of Legends y ARC Raiders, también en juegos que bloquean los atajos normales."),
   ("Páginas: muchos sonidos, pocas teclas","Cada página tiene sus propios atajos. Ctrl + Num1 puede ser un meme en una página y una sintonía en otra. Un «plop» suave te dice en qué página estás."),
   ("Reducción de ruido para tu voz","RNNoise limpia tu micro antes de mezclarlo, así puedes quitar la supresión de Discord sin que se coma tus efectos."),
   ("Recorta y quita silencios","Un editor con forma de onda que quita los silencios con un clic. Tus archivos originales no se tocan."),
   ("Oyes los sonidos, no a ti","Volúmenes separados para tu voz, los sonidos en la llamada y los sonidos en tus cascos."),
   ("Se abre con Windows","Opcional. Arranca escondido en la bandeja, así el micro virtual está listo antes que Discord."),
  ],
  shots=[("connections","El panel de conexiones: elige cada dispositivo y mira la señal en los cables."),
         ("trim","El editor de recorte quita el silencio del principio y del final de un sonido."),
         ("night","Modo noche: carcasa grafito y pantallas ámbar.")],
  demo_t="13 segundos de Bubblepad",
  faq_t="Preguntas", faq=[
   ("¿Cómo hago que suenen sonidos por mi micro en Discord?","Instala Bubblepad, ábrelo y deja que instale VB-CABLE si no lo tienes. En Discord ve a Ajustes de usuario → Voz y vídeo y elige CABLE Output como dispositivo de entrada. Todo lo que suene en Bubblepad llega a la llamada junto con tu voz."),
   ("¿Bubblepad es gratis de verdad?","Sí. Es de código abierto con licencia MIT: sin cuenta, sin anuncios, sin periodo de prueba y sin versión de pago. El código está en GitHub."),
   ("¿Funciona en juegos?","Sí, en cualquier juego o programa que te deje elegir micrófono. Los atajos son globales y funcionan con el juego delante. Si un juego se ejecuta como administrador, activa «Reiniciar como administrador» en los ajustes de Bubblepad."),
   ("¿Por qué Windows muestra un aviso de SmartScreen?","La app todavía no está firmada digitalmente, algo que cuesta dinero para un proyecto gratuito. Pulsa Más información → Ejecutar de todas formas. El instalador se compila automáticamente en GitHub a partir del código público."),
   ("En Discord se me oye doble o con ruido.","Seguramente Windows también envía tu micro al cable. Pulsa Win + R, escribe mmsys.cpl, abre Grabación → tu micrófono → Escuchar y desmarca «Escuchar este dispositivo»."),
   ("¿Necesito la supresión de ruido de Discord?","No, quítala. Discord no distingue tus efectos del ruido de fondo y los filtra. Bubblepad limpia tu voz antes de mezclarla."),
   ("¿Qué formatos y sistemas admite?","MP3, WAV, OGG y FLAC en Windows 10 y 11 (64 bits)."),
  ],
  end_t="Listo para cuando lo estén tus amigos.", end_lead="Descarga gratis para Windows 10 y 11.",
  portable=".zip portable",
  foot_by="Hecho por Pablo Grasa", foot_lic="Licencia MIT", foot_src="Código fuente", foot_issues="Avisar de un problema",
  vb_note="VB-CABLE es un controlador gratuito aparte, de VB-Audio.",
  img_alt_day="Ventana de Bubblepad con la lista de sonidos, sus ondas y sus atajos",
  img_alt_night="Bubblepad en modo noche",
),
}

ICONS = {  # iconos de trazo propio, uno por función
 0:'<path d="M4 7h16v10H4z"/><path d="M7 10h2M11 10h2M15 10h2M8 14h8"/>',
 1:'<path d="M5 5h10v4H5zM9 11h10v4H9zM5 17h10v2H5z"/>',
 2:'<path d="M3 12h3l2-6 3 12 3-9 2 5h5"/>',
 3:'<path d="M6 4l12 16M18 4L6 20"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/>',
 4:'<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><path d="M4 14h3v6H4zM17 14h3v6h-3z"/>',
 5:'<path d="M12 3v9"/><path d="M7 6a7 7 0 1 0 10 0"/>',
}

CSS = r"""
/* Concepto: la propia carcasa de Bubblepad. De día, metal cepillado y pantallas azules; de noche, grafito y ámbar.
   Una sola columna generosa con un héroe tipo aparato y bandas que se leen como placas atornilladas. */
:root{
  --bg:#e7eaee; --bg2:#d7dce2; --plate:#f4f6f8; --plate2:#c9cfd6; --ink:#1f2733; --ink2:#55606e; --line:#b4bcc6;
  --lcd:#0d2b6e; --lcd2:#123a8a; --lcd-ink:#d6ecff; --lcd-glow:rgba(120,190,255,.65);
  --accent:#2f72e0; --accent-ink:#ffffff; --red:#d8433a; --green:#3fbf5a; --yellow:#e2b21f; --shadow:rgba(20,30,45,.28);
  --f-body:"Barlow",system-ui,"Segoe UI",sans-serif; --f-disp:"Barlow Semi Condensed","Barlow",system-ui,sans-serif;
  --f-pix:"Silkscreen","Courier New",monospace; --f-lcd:"VT323","Consolas",monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#191c21; --bg2:#22262d; --plate:#3a4049; --plate2:#2a2f37; --ink:#e7ebf0; --ink2:#a3adba; --line:#4a515b;
  --lcd:#1c1408; --lcd2:#3a2a12; --lcd-ink:#ffd9a8; --lcd-glow:rgba(255,150,40,.6);
  --accent:#ff9f3a; --accent-ink:#1d1408; --shadow:rgba(0,0,0,.55); color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#191c21; --bg2:#22262d; --plate:#3a4049; --plate2:#2a2f37; --ink:#e7ebf0; --ink2:#a3adba; --line:#4a515b;
  --lcd:#1c1408; --lcd2:#3a2a12; --lcd-ink:#ffd9a8; --lcd-glow:rgba(255,150,40,.6);
  --accent:#ff9f3a; --accent-ink:#1d1408; --shadow:rgba(0,0,0,.55); color-scheme:dark}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}
body{margin:0;background:var(--bg);color:var(--ink);font:400 17px/1.6 var(--f-body);
  background-image:repeating-linear-gradient(90deg,transparent 0 2px,color-mix(in srgb,var(--plate) 22%,transparent) 2px 3px)}
a{color:inherit}
.wrap{max-width:1120px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.pix{font-family:var(--f-pix);letter-spacing:.12em;text-transform:uppercase;font-size:12px}
:focus-visible{outline:3px solid var(--accent);outline-offset:3px;border-radius:6px}

/* cabecera */
.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:21;background:var(--bg)}
.top .wrap{display:flex;align-items:center;gap:20px;padding-block:12px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;font-family:var(--f-pix);font-size:15px;letter-spacing:.14em}
.brand img{width:30px;height:30px}
.top nav{display:flex;gap:18px;margin-left:auto;flex-wrap:wrap}
.top nav a{text-decoration:none;color:var(--ink2);font-weight:500;font-size:15px}
.top nav a:hover{color:var(--ink)}
.lang{font-family:var(--f-pix);font-size:11px;letter-spacing:.1em;text-decoration:none;padding:6px 10px;border-radius:999px;border:1px solid var(--line);color:var(--ink2)}
@media (max-width:640px){.top nav a:not(.lang){display:none}}

/* botones de metal */
.btn{display:inline-flex;align-items:center;gap:10px;padding:14px 22px;border-radius:999px;text-decoration:none;font:600 17px/1 var(--f-body);
  color:var(--ink);background:linear-gradient(180deg,#fff 0%,#eef1f4 42%,#b9c0c9 52%,#d7dce2 100%);
  box-shadow:0 0 0 1px #343a42,0 3px 0 1px #343a42,0 8px 14px var(--shadow),inset 0 1px 0 #fff;transition:transform .12s}
.btn:hover{transform:translateY(-1px)}
.btn:active{transform:translateY(2px);box-shadow:0 0 0 1px #343a42,0 1px 0 1px #343a42,inset 0 1px 0 #fff}
.btn.primary{color:var(--accent-ink);background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 55%,#fff) 0%,var(--accent) 55%,color-mix(in srgb,var(--accent) 75%,#000) 100%);
  box-shadow:0 0 0 1px color-mix(in srgb,var(--accent) 50%,#000),0 3px 0 1px color-mix(in srgb,var(--accent) 50%,#000),0 8px 18px var(--shadow),inset 0 1px 0 rgba(255,255,255,.55)}
.btn svg{width:20px;height:20px;fill:currentColor}

/* héroe */
.hero{padding-block:56px 40px}
.hero .wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:48px;align-items:center}
@media (max-width:920px){.hero .wrap{grid-template-columns:1fr;gap:32px}}
.eyebrow{display:inline-flex;align-items:center;gap:10px;padding:7px 12px;border-radius:6px;background:linear-gradient(180deg,var(--lcd2),var(--lcd));
  color:var(--lcd-ink);text-shadow:0 0 6px var(--lcd-glow);box-shadow:inset 0 2px 5px rgba(0,0,0,.55);font-family:var(--f-pix);font-size:11px;letter-spacing:.14em}
.eyebrow i{width:7px;height:7px;border-radius:50%;background:#62d63a;box-shadow:0 0 8px #62d63a}
h1{font:800 clamp(40px,6vw,66px)/1.02 var(--f-disp);letter-spacing:-.015em;margin:18px 0 18px;text-wrap:balance}
.lead{font-size:19px;color:var(--ink2);max-width:34em;margin:0 0 28px}
.ctas{display:flex;flex-wrap:wrap;gap:14px;align-items:center}
.meta{margin-top:16px;font-size:14px;color:var(--ink2)}
.device{position:relative;min-width:0}
.device img{display:block;width:100%;height:auto;filter:drop-shadow(0 24px 30px var(--shadow))}
.device .n{display:none}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .device .d{display:none}:root:not([data-theme="light"]) .device .n{display:block}}
:root[data-theme="dark"] .device .d{display:none} :root[data-theme="dark"] .device .n{display:block}
.readout{position:absolute;right:4%;bottom:-6px;display:flex;flex-direction:column;gap:2px;padding:10px 14px;border-radius:8px;
  background:linear-gradient(180deg,var(--lcd2),var(--lcd));box-shadow:0 0 0 1px #0006,0 10px 20px var(--shadow),inset 0 2px 6px rgba(0,0,0,.55);color:var(--lcd-ink);text-shadow:0 0 6px var(--lcd-glow)}
.readout small{font-family:var(--f-pix);font-size:9px;letter-spacing:.14em;opacity:.75}
.readout b{font:400 28px/1 var(--f-lcd);letter-spacing:.04em}
.readout .vu{display:flex;gap:2px;margin-top:4px}
.readout .vu i{width:6px;height:10px;border-radius:1px;background:#62d63a;box-shadow:0 0 5px #62d63a;animation:vu 1.1s ease-in-out infinite alternate}
.readout .vu i:nth-child(n+8){background:#ffd23a;box-shadow:0 0 5px #ffd23a}
.readout .vu i:nth-child(n+10){background:#ff5544;box-shadow:0 0 5px #ff5544}
@keyframes vu{from{opacity:1}to{opacity:.25}}
.readout .vu i:nth-child(2n){animation-delay:.2s}.readout .vu i:nth-child(3n){animation-delay:.45s}

/* secciones como placas */
section{padding-block:56px}
h2{font:800 clamp(30px,4vw,42px)/1.1 var(--f-disp);margin:0 0 10px;text-wrap:balance}
.sub{color:var(--ink2);margin:0 0 32px;max-width:40em}
.plate{position:relative;background:linear-gradient(180deg,var(--plate),var(--plate2));border-radius:14px;
  box-shadow:0 0 0 1px var(--line),0 3px 0 1px color-mix(in srgb,var(--line) 70%,#000),0 14px 26px var(--shadow),inset 0 1px 0 color-mix(in srgb,#fff 70%,transparent)}
.screw{position:absolute;width:11px;height:11px;border-radius:50%;background:radial-gradient(circle at 38% 32%,#fdfdfd,#c4c9cf 45%,#7d848d);box-shadow:0 1px 1px rgba(0,0,0,.45)}
.screw::after{content:"";position:absolute;left:1.5px;right:1.5px;top:4.5px;height:2px;border-radius:1px;background:#5b626b;transform:rotate(35deg)}
.screw.a{left:10px;top:10px}.screw.b{right:10px;top:10px}.screw.c{left:10px;bottom:10px}.screw.d{right:10px;bottom:10px}

/* cómo funciona */
.flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;position:relative}
@media (max-width:860px){.flow{grid-template-columns:1fr}}
.step{padding:30px 26px 26px}
.step .no{font:400 40px/1 var(--f-lcd);color:var(--lcd-ink);background:linear-gradient(180deg,var(--lcd2),var(--lcd));text-shadow:0 0 6px var(--lcd-glow);
  display:inline-grid;place-items:center;width:54px;height:46px;border-radius:7px;box-shadow:inset 0 2px 5px rgba(0,0,0,.55)}
.step h3{font:700 22px/1.2 var(--f-disp);margin:16px 0 8px}
.step p{margin:0;color:var(--ink2);font-size:16px}
.jack{position:absolute;width:26px;height:26px;border-radius:50%;top:50%;margin-top:-13px;
  background:radial-gradient(circle,#050608 0 4px,#2a2e33 4.5px 5.5px,#9ea5ae 6px,#f4f6f8 8.5px,#b7bdc5 10.5px,#6f767f 12.5px,transparent 13px)}
.step .jack.out{right:-13px}.step .jack.in{left:-13px}
@media (max-width:860px){.step .jack{display:none}}
.legend{display:flex;flex-wrap:wrap;gap:22px;margin-top:24px}
.legend span{display:flex;align-items:center;gap:10px;color:var(--ink2)}
.legend i{width:34px;height:7px;border-radius:4px;box-shadow:inset 0 -2px 0 rgba(0,0,0,.25)}

/* funciones */
.feats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
@media (max-width:920px){.feats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:600px){.feats{grid-template-columns:1fr}}
.feat{padding:24px 24px 22px;min-width:0}
.feat svg{width:30px;height:30px;stroke:var(--accent);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.feat h3{font:700 20px/1.25 var(--f-disp);margin:12px 0 6px}
.feat p{margin:0;color:var(--ink2);font-size:15.5px}

/* capturas y vídeo */
.gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;margin-top:36px}
@media (max-width:860px){.gallery{grid-template-columns:1fr}}
figure{margin:0;min-width:0}
figure img{display:block;width:100%;height:auto;filter:drop-shadow(0 12px 18px var(--shadow))}
figcaption{margin-top:10px;font-size:14.5px;color:var(--ink2)}
.demo{padding:18px;margin-top:8px;max-width:880px;margin-left:auto;margin-right:auto}
.demo video{display:block;width:100%;height:auto;border-radius:8px;background:#000}
.demo .pix{display:block;margin:0 0 12px 8px;color:var(--ink2)}

/* preguntas */
.faq{display:grid;gap:12px;max-width:820px}
details{background:linear-gradient(180deg,var(--plate),var(--plate2));border-radius:12px;box-shadow:0 0 0 1px var(--line),0 6px 14px var(--shadow)}
summary{cursor:pointer;list-style:none;padding:18px 22px;font:700 19px/1.3 var(--f-disp);display:flex;gap:14px;align-items:center}
summary::-webkit-details-marker{display:none}
summary::before{content:"+";font:400 26px/1 var(--f-lcd);color:var(--lcd-ink);background:linear-gradient(180deg,var(--lcd2),var(--lcd));text-shadow:0 0 6px var(--lcd-glow);
  width:28px;height:28px;flex:none;display:grid;place-items:center;border-radius:6px;box-shadow:inset 0 2px 4px rgba(0,0,0,.5)}
details[open] summary::before{content:"−"}
details p{margin:0;padding:0 22px 20px 64px;color:var(--ink2)}

/* cierre */
.end{padding-block:40px 64px}
.end .plate{padding:40px 32px;display:flex;flex-wrap:wrap;gap:24px;align-items:center;justify-content:space-between}
.end h2{margin:0}
.end p{margin:6px 0 0;color:var(--ink2)}
.end .ctas a.small{font-size:15px;color:var(--ink2)}
footer{border-top:1px solid var(--line);padding-block:24px 36px;color:var(--ink2);font-size:14.5px}
footer .wrap{display:flex;flex-wrap:wrap;gap:10px 24px;align-items:center}
footer .note{flex-basis:100%;font-size:13px}
"""

WIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5.5 10.5 4.4v7.1H3zM11.5 4.3 21 3v8.5h-9.5zM3 12.5h7.5v7.1L3 18.5zM11.5 12.5H21V21l-9.5-1.3z"/></svg>'
GH = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.4-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.4 1.1 3 .8.1-.6.3-1.1.6-1.3-2.2-.3-4.6-1.1-4.6-5a3.9 3.9 0 0 1 1-2.7 3.6 3.6 0 0 1 .1-2.7s.8-.3 2.8 1a9.6 9.6 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7a3.9 3.9 0 0 1 1 2.7c0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.8V21c0 .3.2.6.7.5A10 10 0 0 0 12 2z"/></svg>'


def e(s):
    return html.escape(s, quote=True)


def page(lang, mode):
    t = T[lang]
    es = lang == "es"
    # rutas: en la vista previa todo cuelga del mismo sitio; en GitHub Pages la versión ES vive en /es/
    up = "../" if (mode == "pages" and es) else ""
    img = up + "img/"
    if mode == "preview":
        other_href = "es.html" if not es else "index.html"
    else:
        other_href = ("es/" if not es else "../")
    url = SITE + ("es/" if es else "")
    sfx = "-es" if es else ""
    ld = [
      {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Bubblepad",
       "operatingSystem": "Windows 10, Windows 11", "applicationCategory": "MultimediaApplication",
       "softwareVersion": VERSION, "description": t["desc"], "url": url, "downloadUrl": DL,
       "image": SITE + "img/day.webp", "license": "https://opensource.org/licenses/MIT",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
       "author": {"@type": "Person", "name": "Pablo Grasa"}, "inLanguage": lang},
      {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in t["faq"]]},
    ]
    head = f"""<title>{e(t['title'])}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="{e(t['desc'])}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{SITE}"><link rel="alternate" hreflang="es" href="{SITE}es/"><link rel="alternate" hreflang="x-default" href="{SITE}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(t['title'])}"><meta property="og:description" content="{e(t['desc'])}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{SITE}img/og.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{img}icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Semi+Condensed:wght@700;800&family=Silkscreen&family=VT323&display=swap">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>"""

    nav = "".join(f'<a href="#{i}">{e(n)}</a>' for i, n in zip(("how", "features", "faq"), t["nav"]))
    steps = ""
    for i, (h, p) in enumerate(t["steps"]):
        jacks = ('<i class="jack in"></i>' if i else "") + ('<i class="jack out"></i>' if i < 2 else "")
        steps += f'<div class="plate step"><span class="screw b"></span><span class="screw d"></span>{jacks}<span class="no">{i+1}</span><h3>{e(h)}</h3><p>{e(p)}</p></div>'
    feats = "".join(f'<div class="plate feat"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[i]}</svg><h3>{e(h)}</h3><p>{e(p)}</p></div>'
                    for i, (h, p) in enumerate(t["feat"]))
    shots = "".join(f'<figure><img src="{img}{n}{sfx}.webp" width="1120" height="720" loading="lazy" alt="{e(c)}"><figcaption>{e(c)}</figcaption></figure>'
                    for n, c in t["shots"])
    faq = "".join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in t["faq"])
    cl = t["cable_labels"]
    body = f"""
<header class="top"><div class="wrap">
  <a class="brand" href="#top"><img src="{img}icon.png" width="30" height="30" alt="">BUBBLEPAD</a>
  <nav>{nav}<a class="lang" href="{other_href}" hreflang="{t['other']}" lang="{t['other']}">{e(t['other_label'])}</a></nav>
</div></header>

<main id="top">
<section class="hero"><div class="wrap">
  <div>
    <span class="eyebrow"><i></i>{e(t['eyebrow'])}</span>
    <h1>{t['h1']}</h1>
    <p class="lead">{e(t['lead'])}</p>
    <div class="ctas">
      <a class="btn primary" href="{DL}">{WIN}{e(t['cta'])}</a>
      <a class="btn" href="{REPO}">{GH}{e(t['cta2'])}</a>
    </div>
    <p class="meta">{e(t['meta'])}</p>
  </div>
  <div class="device">
    <img class="d" src="{img}day{sfx}.webp" width="1120" height="720" alt="{e(t['img_alt_day'])}" fetchpriority="high">
    <img class="n" src="{img}night{sfx}.webp" width="1120" height="720" alt="{e(t['img_alt_night'])}">
    <div class="readout" aria-hidden="true"><small>{e(t['lcd_now'])}</small><b>{e(t['lcd_song'])}</b><span class="vu">{'<i></i>'*11}</span></div>
  </div>
</div></section>

<section id="how"><div class="wrap">
  <h2>{e(t['how_t'])}</h2>
  <p class="sub">{e(t['how_lead'])}</p>
  <div class="flow">{steps}</div>
  <div class="legend"><span><i style="background:var(--red)"></i>{e(cl[0])}</span><span><i style="background:var(--green)"></i>{e(cl[1])}</span><span><i style="background:var(--yellow)"></i>{e(cl[2])}</span></div>
</div></section>

<section id="features"><div class="wrap">
  <h2>{e(t['feat_t'])}</h2>
  <div class="feats" style="margin-top:28px">{feats}</div>
  <div class="gallery">{shots}</div>
  <div class="plate demo" style="margin-top:40px"><span class="pix">{e(t['demo_t'])}</span>
    <video src="{img}demo.mp4" autoplay muted loop playsinline preload="metadata" width="1120" height="720"></video></div>
</div></section>

<section id="faq"><div class="wrap">
  <h2>{e(t['faq_t'])}</h2>
  <div class="faq" style="margin-top:24px">{faq}</div>
</div></section>

<section class="end"><div class="wrap"><div class="plate"><span class="screw a"></span><span class="screw b"></span><span class="screw c"></span><span class="screw d"></span>
  <div><h2>{e(t['end_t'])}</h2><p>{e(t['end_lead'])}</p></div>
  <div class="ctas"><a class="btn primary" href="{DL}">{WIN}{e(t['cta'])}</a><a class="small" href="{ZIP}">{e(t['portable'])}</a></div>
</div></div></section>
</main>

<footer><div class="wrap">
  <span>{e(t['foot_by'])}</span><a href="{REPO}">{e(t['foot_src'])}</a><a href="{REPO}/issues">{e(t['foot_issues'])}</a><span>{e(t['foot_lic'])}</span>
  <span class="note">{e(t['vb_note'])}</span>
</div></footer>
"""
    if mode == "preview" and not es:
        return head + body          # la vista previa añade su propio <head>
    return f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n{head}\n</head>\n<body>{body}</body>\n</html>\n'


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "preview"
    here = os.path.dirname(os.path.abspath(__file__))
    if mode == "preview":
        open(os.path.join(here, "index.html"), "w", encoding="utf-8").write(page("en", "preview"))
        open(os.path.join(here, "es.html"), "w", encoding="utf-8").write(page("es", "preview"))
    else:
        out = sys.argv[2]
        os.makedirs(os.path.join(out, "es"), exist_ok=True)
        open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page("en", "pages"))
        open(os.path.join(out, "es", "index.html"), "w", encoding="utf-8").write(page("es", "pages"))
    print("ok", mode)

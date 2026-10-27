; Instalador de Bubblepad (Inno Setup 6).
; Se instala para el usuario actual en %LOCALAPPDATA%\Programs\Bubblepad: Bubblepad guarda sus ajustes
; y la carpeta de sonidos junto al .exe, así que tiene que ser una carpeta en la que pueda escribir.
; No pide permisos de administrador.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppName "Bubblepad"
#define MyAppExe "Bubblepad.exe"

[Setup]
AppId={{6A3F7C2E-9B1D-4E5A-8C47-B0B1BB1E0AD0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Pablo Grasa
AppPublisherURL=https://github.com/civercras/bubblepad
AppSupportURL=https://github.com/civercras/bubblepad/issues
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Bubblepad-Setup
SetupIconFile=..\assets\bubblepad.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Bubblepad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; Al desinstalar se borran los archivos del programa. Tus sonidos y config.json se conservan.

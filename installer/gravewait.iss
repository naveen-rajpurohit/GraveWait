; Inno Setup script for GraveWait.
; Compile after `pyinstaller gravewait.spec --noconfirm`:
;   ISCC installer\gravewait.iss
; Produces installer\Output\GraveWaitSetup.exe with:
;   - terms & conditions page (must accept)
;   - install-path selection
;   - optional "Attach to Claude Code" (runs as the real user, not admin)
;   - optional desktop shortcut launching the 4-minute standalone demo

[Setup]
AppId={{3DCBFF24-F8B1-44E0-9820-8350D2C60DFE}
AppName=GraveWait
AppVersion=1.0.0
AppPublisher=Naveen Rajpurohit
AppPublisherURL=https://github.com/naveen-rajpurohit/GraveWait
DefaultDirName={autopf}\GraveWait
DisableDirPage=no
DisableProgramGroupPage=yes
LicenseFile=EULA.txt
OutputDir=Output
OutputBaseFilename=GraveWaitSetup
SetupIconFile=gravewait.ico
UninstallDisplayIcon={app}\GraveWait.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Tasks]
Name: "claudehooks"; Description: "Attach to Claude Code (game launches on every prompt)"
Name: "desktopicon"; Description: "Desktop shortcut: standalone 4-minute game (no Claude needed)"

[Files]
Source: "..\dist\GraveWait\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\ASSETS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\GraveWait"; Filename: "{app}\GraveWait.exe"; Parameters: "--play"
Name: "{group}\Attach GraveWait to Claude Code"; Filename: "{app}\GraveWait.exe"; Parameters: "--install-hooks"
Name: "{group}\Detach GraveWait from Claude Code"; Filename: "{app}\GraveWait.exe"; Parameters: "--uninstall-hooks"
Name: "{autodesktop}\GraveWait"; Filename: "{app}\GraveWait.exe"; Parameters: "--play"; Tasks: desktopicon

[Run]
Filename: "{app}\GraveWait.exe"; Parameters: "--install-hooks"; Tasks: claudehooks; Flags: runasoriginaluser
Filename: "{app}\GraveWait.exe"; Parameters: "--play"; Description: "Play GraveWait now (standalone 4-minute run)"; Flags: postinstall nowait skipifsilent unchecked runasoriginaluser

[UninstallRun]
Filename: "{app}\GraveWait.exe"; Parameters: "--uninstall-hooks"; RunOnceId: "DetachClaude"

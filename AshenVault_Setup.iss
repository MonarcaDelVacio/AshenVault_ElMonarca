; AshenVault - instalador Windows
; Requiere Inno Setup 6.x en la máquina de desarrollo para compilar.
[Setup]
AppId={{8A0D0D77-4D47-4F93-9C45-7F3C1A5E9B21}}
AppName=AshenVault
AppVersion=1.0.0
AppPublisher=AshenVault
DefaultDirName={autopf}\AshenVault
DefaultGroupName=AshenVault
OutputDir=installer
OutputBaseFilename=AshenVault_Setup
SetupIconFile=assets\icons\AshenVaultIcon.ico
UninstallDisplayIcon={app}\AshenVault.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\AshenVault.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AshenVault"; Filename: "{app}\AshenVault.exe"; IconFilename: "{app}\AshenVault.exe"
Name: "{autodesktop}\AshenVault"; Filename: "{app}\AshenVault.exe"; IconFilename: "{app}\AshenVault.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

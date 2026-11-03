; SORTIQ Windows installation wizard - compile with Inno Setup 6.
; Produces Output/SORTIQ_2.0_Beta_Setup.exe after the Windows app has been built.
#define AppName "SORTIQ"
#define AppVersion "2.0.0-beta"
#define AppExe "SORTIQ.exe"

[Setup]
AppId={{CFDA6F22-FA85-4BE5-B251-8B104149A3C0}
AppName={#AppName}
AppVerName={#AppName} {#AppVersion}
AppVersion={#AppVersion}
AppPublisher=SORTIQ Project
DefaultDirName={localappdata}\Programs\SORTIQ
DefaultGroupName=SORTIQ
OutputDir=Output
OutputBaseFilename=SORTIQ_2.0_Beta_Setup
SetupIconFile=..\assets\icons\sortiq.ico
UninstallDisplayIcon={app}\{#AppExe}
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
LicenseFile=..\docs\EULA.txt
InfoBeforeFile=..\docs\PRIVACY.txt
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
MinVersion=10.0
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\SORTIQ\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\EULA.txt"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\PRIVACY.txt"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\SORTIQ"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"
Name: "{group}\Uninstall SORTIQ"; Filename: "{uninstallexe}"
Name: "{userdesktop}\SORTIQ"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch SORTIQ"; Flags: nowait postinstall skipifsilent

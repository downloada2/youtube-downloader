#define MyAppName "YouTube Downloader для Chrome"
#define MyAppVersion "1.0.1"

[Setup]
AppId={{7B2E5C10-3D6A-4E88-9F41-0A1C2B3D4E5F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=YouTube Downloader
DefaultDirName={localappdata}\YouTube Downloader Extension
DisableProgramGroupPage=yes
DisableDirPage=yes
Compression=lzma2/max
SolidCompression=yes
OutputDir=..\installer_output
OutputBaseFilename=YouTube-Downloader-Chrome-Extension-Setup
SetupIconFile=..\windows\app_icon.ico
UninstallDisplayIcon={app}\icons\48.png
WizardStyle=modern
PrivilegesRequired=lowest
InfoAfterFile=steps.txt

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "..\extension\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
Filename: "{code:ChromeExe}"; Parameters: "chrome://extensions"; Description: "Открыть страницу расширений Chrome"; Flags: nowait postinstall skipifsilent; Check: ChromeFound
Filename: "explorer.exe"; Parameters: """{app}"""; Description: "Показать папку с расширением"; Flags: nowait postinstall skipifsilent

[Code]
function ChromeExe(Param: String): String;
var P: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe', '', P) and FileExists(P) then Result := P
  else if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe', '', P) and FileExists(P) then Result := P;
end;

function ChromeFound: Boolean;
begin
  Result := ChromeExe('') <> '';
end;

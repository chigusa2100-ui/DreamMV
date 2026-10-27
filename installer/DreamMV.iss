; Inno Setup 6 でコンパイルすると DreamMV-Setup.exe ができます
[Setup]
AppName=DreamMV
AppVersion=1.0.0
DefaultDirName={localappdata}\DreamMV
DefaultGroupName=DreamMV
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=DreamMV-Setup
Compression=lzma2
SolidCompression=yes

[Files]
; プロジェクトルート(installerの1つ上)を丸ごと同梱。venv/モデル/出力は除外
Source: "..\*"; DestDir: "{app}"; Excludes: ".venv\*,models\*,output\*,installer\Output\*,__pycache__\*,*.pyc,.git\*"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\DreamMV"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\main.py"""; WorkingDir: "{app}"
Name: "{autodesktop}\DreamMV"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\main.py"""; WorkingDir: "{app}"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\install.ps1"" -AppDir ""{app}"""; StatusMsg: "Python環境とAnimagineモデルを準備中..."; Flags: waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\models"

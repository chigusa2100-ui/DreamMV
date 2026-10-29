; Inno Setup 6 でコンパイルすると DreamMV-Setup.exe ができます

[Setup]
AppName=DreamMV
AppVersion=1.1.0
DefaultDirName={localappdata}\DreamMV
DefaultGroupName=DreamMV
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=DreamMV-Setup
Compression=lzma2
SolidCompression=yes

[Files]
; プロジェクトルートを同梱。仮想環境・モデル・生成出力などは除外
Source: "..\*"; DestDir: "{app}"; Excludes: ".venv\*,models\*,output\*,installer\Output\*,__pycache__\*,*.pyc,.git\*"; Flags: recursesubdirs createallsubdirs

[Icons]
; スタートメニュー
Name: "{autoprograms}\DreamMV"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\DreamMV.py"""; WorkingDir: "{app}"

; デスクトップ
Name: "{autodesktop}\DreamMV"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\DreamMV.py"""; WorkingDir: "{app}"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\install.ps1"" -AppDir ""{app}"""; StatusMsg: "Python環境とAnimagineモデルを準備中..."; Flags: waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\models"
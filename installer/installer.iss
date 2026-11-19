; SAP 공사 발주 자동화 프로그램 — Inno Setup 설치 스크립트
; 빌드: ISCC /DMyAppVersion=1.1.1 installer\installer.iss  (GitHub Actions 가 app/version.json 에서 버전을 읽어 넘김)
; ※ 한글이 있으므로 빌드 전에 UTF-8(BOM)으로 변환한다(워크플로가 자동 처리).
;
; 설치 위치: 사용자 폴더(%LOCALAPPDATA%\Programs) · 관리자 권한 불필요
;   → 단가표 저장(settings.json)·로그 기록을 일반 사용자 권한으로 할 수 있게
; 업데이트: 같은 AppId 로 덮어 설치. settings.json(사용자가 고친 단가표)은 보존.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppName "SAP 공사 발주 자동화 프로그램"
#define MyAppExe "SAPOrderAutomation.exe"

[Setup]
AppId={{8C5D2F4A-6B1E-4E7A-9C3D-2A7F5B1E9D40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName}({#MyAppVersion})
UninstallDisplayName={#MyAppName}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SourceDir=..
OutputDir=installer_output
OutputBaseFilename={#MyAppName}({#MyAppVersion})
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=app\gui\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExe}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업"

[InstallDelete]
; 이전 버전 바로가기 삭제(이름에 버전이 들어 있어 패턴으로 지움)
Type: files; Name: "{userdesktop}\{#MyAppName}(*).lnk"
Type: files; Name: "{group}\{#MyAppName}(*).lnk"
; 이전 버전 프로그램 부품 정리(구버전 파일이 섞여 남지 않게) — 설정·로그(app\)는 건드리지 않음
Type: filesandordirs; Name: "{app}\_internal"

[Files]
; 프로그램 본체(PyInstaller 폴더형 결과)
Source: "dist\SAPOrderAutomation\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 화면·대기창 자원(HTML, 글꼴, 로고) — 파이썬 코드(.py)는 exe 안에 있으므로 제외
Source: "app\gui\*"; DestDir: "{app}\app\gui"; Excludes: "*.py,__pycache__"; Flags: ignoreversion recursesubdirs createallsubdirs
; 버전 정보 — 업데이트 때마다 새 값으로
Source: "app\version.json"; DestDir: "{app}\app"; Flags: ignoreversion
; 설정(허가청·업체·단가표) — 처음 설치할 때만. 업데이트 때는 사용자가 고친 단가표 보존
Source: "app\config\settings.json"; DestDir: "{app}\app\config"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}({#MyAppVersion})"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{userdesktop}\{#MyAppName}({#MyAppVersion})"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "프로그램 실행"; Flags: nowait postinstall skipifsilent

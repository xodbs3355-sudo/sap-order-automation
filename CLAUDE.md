# SAP 공사 발주 자동화 프로그램

## 프로젝트 개요
- 목적: 도시가스 공무 파트의 공사의뢰 접수 ~ 협력사 발주 전 과정 자동화
- 대상: 수요가 인입분기 공사 유형 단일
- 실행 환경: Windows 로컬 데스크탑 앱

## 기술 스택
- Python (메인)
- pywebview (GUI 프레임워크)
- win32com (SAP GUI Scripting 연동)

## 자동화 T-code 순서
ZREC0002 → ZREC0100 → ZMEC0210 → ZREC2030 → ZREC2040 → ZREC0208

## 개발 원칙
- 코드 수정 시 영향 범위를 먼저 설명하고 허락 후 진행
- 하나의 요청 = 하나의 작업만 실행
- 커밋/푸시는 반드시 사용자 허락 후 진행
- **반영 범위 확인(모든 세션 공통)**: 프로그램 로직(코드·화면·설정)을 바꾼 작업은 커밋/푸시 전에 항상 사용자에게 물어본다 —
  "① 브랜치(main: 파이썬 실행용 내려받기)와 ② 릴리즈(설치 파일 .exe 내려받기)에 **둘 다 반영할까요, 한쪽만 할까요?**"
  → 릴리즈(.exe)는 main 에서 `app/version.json`(버전)이 바뀐 푸시일 때 자동 빌드되므로, 릴리즈까지 반영하려면 버전 올림(아래 '버전 관리')도 함께 확정받는다.
- 전문용어 사용 시 반드시 설명과 비유 포함
- 폰트는 로컬 파일 방식 사용 (app/gui/assets/fonts/ 폴더)
  → 폰트 파일은 추후 사용자가 직접 해당 폴더에 복사 예정
  → HTML에서 Google Fonts @import 방식 금지, @font-face 로컬 방식만 사용

## 버전 관리
- 버전 값은 `app/version.json`의 `version`·`version_date` 한 곳에서 관리하며, 화면 우측 하단과 설치 파일·바로가기 이름에 표시된다.
  (settings.json 에서 분리한 이유: 설치형 업데이트 때 사용자가 고친 단가표(settings.json)는 보존하고 버전만 새로 바꾸기 위함)
- 버전 규칙(유의적 버전, 주.부.수정): 큰 변경=주(`2.0.0`) / 기능 추가=부(`1.1.0`) / 잔손질=수정(`1.0.2`). 윗자리 올리면 아랫자리 0으로 리셋.
- **의미 있는 변경을 커밋하기 전에**, 변경 성격에 맞는 새 버전을 **사용자에게 먼저 제안해 확정받는다**(예: "이번은 1.0.2(수정) 감입니다 — 올릴까요?"). 임의로 올리지 않는다.
- 확정되면 커밋 전에 ①`app/version.json`의 `version`·`version_date`(그날 날짜) 갱신 ②`app/docs/CHANGELOG.md` 맨 위에 `## [버전] - 날짜` + 변경 요약 추가.
- main 에서 `app/version.json`이 바뀐 푸시는 GitHub Actions 가 설치 파일을 자동 빌드해 Releases "latest"에 올린다(아래 '설치 파일 배포').

## SAP 연결 방식
- 사용자가 SAP에 직접 로그인 후 Python이 열린 세션에 연결
- win32com.client.GetObject('SAPGUI') 방식 사용
- Windows 사용자명: J0131
- pywin32 버전 310 설치 확인 완료
- SAP GUI Scripting 활성화 확인 완료

## 파일 설명
- 폴더 정리: 실행 파일 main.py 만 루트, 나머지는 app/ 폴더에 둔다.
  main.py 가 app/ 을 sys.path 에 추가해 기존 import(config_manager·sap·applog)를 유지.
- main.py: 앱 진입점 (루트, pywebview 창 실행)
- app/sap/connector.py: SAP 세션 연결 관리
- app/sap/zrec000X.py: T-code별 자동화 함수
- app/gui/index.html: 확정된 GUI (목업에서 가져온 파일)
- app/gui/splash.py: 시작 대기창(스켈레톤). main.py 가 별도 프로세스로 먼저 띄우고, 본 화면 준비(gui_ready) 시 닫음
  (자원: app/gui/assets/splash_logo.png, app/gui/assets/fonts/splash_*.ttf)
- app/gui/assets/fonts/: 로컬 폰트 파일 보관 폴더 (Gmarket Sans Bold, Nanum Gothic)
- app/paths.py: 프로그램 루트 경로 기준(파이썬 실행 / .exe 실행 공통). 설정·화면·로그 경로는 여기서 정한다.
- app/version.json: 프로그램 버전(단일 출처)
- app/config/settings.json: 허가청·업체·단가표 설정값
- app/docs/CHANGELOG.md: 버전별 변경 이력 (최신순)

## GUI 미리보기 (개발 지원)
- HTML/GUI를 수정하면 매번 헤드리스 Chromium으로 렌더링해 PNG 스크린샷으로 보여줄 것.
  → 코드만 설명하지 말고, 실제 화면을 이미지로 확인시켜 줄 것.
- 실행 환경에 브라우저가 없을 수 있으니, 로컬 CLI라면 먼저 Playwright/Chromium
  설치 여부를 확인하고, 없으면 설치 방법을 안내할 것.

## 설치 파일 배포 (.exe)
- GitHub Actions(`.github/workflows/build.yml`, windows-latest)가 PyInstaller(폴더형·콘솔 없음)로 exe 를 만들고 Inno Setup(`installer/installer.iss`)으로 설치 파일을 만든다. PC 에서 빌드하지 않는다.
- 설치 파일 이름: `SAP 공사 발주 자동화 프로그램(버전).exe`, 바탕화면 바로가기 이름도 같은 형식. 이전 버전 바로가기는 설치 때 자동 삭제.
  단, GitHub Releases 에 올리는 파일 이름은 `sap-order-automation-버전.exe`(GitHub 가 한글·공백·괄호를 지우기 때문).
- 아이콘: `app/gui/assets/app.ico`(문서 + SAP 로고). exe·바로가기·설치 파일·창 제목줄에 사용.
- 설치 위치: 사용자 폴더(%LOCALAPPDATA%\Programs, 관리자 권한 불필요). exe 옆에 `app\`(gui·config·version.json·logs)이 소스와 같은 구조로 놓인다.
- 업데이트 설치 때 `app\config\settings.json`은 덮어쓰지 않는다(단가표 보존). 허가청·업체 목록 등을 바꿔도 기존 설치 PC 에는 반영되지 않으므로 필요 시 별도 안내.
- 빌드 전용 라이브러리 버전은 `installer/requirements-build.txt`에 고정한다.
- exe 전용 실행 모드(main.py): `--splash`(대기창만), `--selftest`(빌드 검증, exe 옆 selftest.txt 기록).

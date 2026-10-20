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
- 전문용어 사용 시 반드시 설명과 비유 포함
- 폰트는 로컬 파일 방식 사용 (app/gui/assets/fonts/ 폴더)
  → 폰트 파일은 추후 사용자가 직접 해당 폴더에 복사 예정
  → HTML에서 Google Fonts @import 방식 금지, @font-face 로컬 방식만 사용

## 버전 관리
- 버전 값은 `app/config/settings.json`의 `version`·`version_date` 한 곳에서 관리하며, 화면 우측 하단에 표시된다.
- 버전 규칙(유의적 버전, 주.부.수정): 큰 변경=주(`2.0.0`) / 기능 추가=부(`1.1.0`) / 잔손질=수정(`1.0.2`). 윗자리 올리면 아랫자리 0으로 리셋.
- **의미 있는 변경을 커밋하기 전에**, 변경 성격에 맞는 새 버전을 **사용자에게 먼저 제안해 확정받는다**(예: "이번은 1.0.2(수정) 감입니다 — 올릴까요?"). 임의로 올리지 않는다.
- 확정되면 커밋 전에 ①`settings.json`의 `version`·`version_date`(그날 날짜) 갱신 ②`app/docs/CHANGELOG.md` 맨 위에 `## [버전] - 날짜` + 변경 요약 추가.

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
- app/gui/assets/fonts/: 로컬 폰트 파일 보관 폴더 (Gmarket Sans Bold, Nanum Gothic)
- app/config/settings.json: 허가청·업체·단가표 설정값
- app/docs/CHANGELOG.md: 버전별 변경 이력 (최신순)

## GUI 미리보기 (개발 지원)
- HTML/GUI를 수정하면 매번 헤드리스 Chromium으로 렌더링해 PNG 스크린샷으로 보여줄 것.
  → 코드만 설명하지 말고, 실제 화면을 이미지로 확인시켜 줄 것.
- 실행 환경에 브라우저가 없을 수 있으니, 로컬 CLI라면 먼저 Playwright/Chromium
  설치 여부를 확인하고, 없으면 설치 방법을 안내할 것.

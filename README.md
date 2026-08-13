# 공사 발주 자동화 프로그램

강원도시가스 공무 파트 — **수요가 인입분기 공사**의 접수~협력사 발주 자동화.
(대상 권역: **춘천·홍천** / 63A·연장 10m 이하)

## ▶ 실행 방법
1. SAP GUI 에 **직접 로그인** (SAP 스크립팅 활성화 상태)
2. 프로그램 실행:
   ```
   python main.py
   ```
   (윈도우: `py main.py`)

**루트에서 실행하는 파일은 `main.py` 하나뿐입니다.** 나머지 코드·설정·화면은 전부 `app/` 폴더 안에 정리돼 있습니다.

## 📁 폴더 구조
```
main.py              ← 실행 파일 (이것만 실행)
app/                 ← 프로그램 내용 (평소 직접 열 일 없음)
  config/settings.json  · 허가청·업체·단가표·지역코드 설정
  gui/                  · 화면(HTML)
  sap/                  · SAP 자동화(T-code별)
  tools/                · 지역코드 엑셀 반영 도구
  docs/                 · 참고 메모(테스트_참고메모.md)
  logs/                 · 실행 로그 (자동 생성)
  test_*.py             · 단독 테스트 스크립트
  requirements.txt      · 필요 패키지 목록
```

## 🔧 최초 설치 (한 번만)
```
python -m pip install -r app/requirements.txt
```
(윈도우: `py -m pip install -r app\requirements.txt`)

## 📝 참고
- 실행 로그: `app/logs/app_YYYYMMDD.log` (오류 시 이 파일을 확인)
- 지역코드 갱신: `python app/tools/import_region_excel.py 지역코드.xlsx`
- 자세한 설명: `app/docs/테스트_참고메모.md`

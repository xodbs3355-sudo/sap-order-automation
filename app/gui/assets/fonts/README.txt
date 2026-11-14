이 폴더의 폰트는 index.html의 @font-face가 참조하는 로컬 폰트입니다.

사용 파일 (woff2 · 서브셋, 저장소에 포함됨 — 따로 복사 불필요):
- GmarketSansBold.woff2  (Gmarket Sans Bold, font-weight 700)
- NanumGothic.woff2      (Nanum Gothic)

※ 한글 전체 + 영문/기호만 남기고 woff2로 서브셋한 파일입니다.
  (원본 .ttf 약 7MB → woff2 약 1MB · 로딩/스캔 속도 개선, 글자 깨짐 없음)
  원본 .ttf 로부터 다시 만들려면 (fonttools 필요):
    pyftsubset <원본.ttf> \
      --unicodes="U+0020-00FF,U+0100-017F,U+1100-11FF,U+2000-206F,U+2190-21FF,U+3000-303F,U+3130-318F,U+AC00-D7A3" \
      --flavor=woff2 --output-file=<이름.woff2>

※ Google Fonts @import 방식은 사용하지 않습니다 (로컬 @font-face 방식만 사용).

────────────────────────────────────────
시작 대기창(app/gui/splash.py) 전용 글꼴 (TTF · 대기창 글자만 포함)
- splash_GmarketSansBold.ttf  (제목 "공사 발주 자동화 프로그램")
- splash_NanumGothic.ttf      (안내 문구 + 숫자 0~9 + "초" "·")

※ 대기창은 tkinter 로 그리는데, tkinter 는 woff2 를 못 읽어 TTF 가 따로 필요합니다.
  대기창이 뜰 때 이 프로그램 안에서만 잠깐 등록해 씁니다(Windows 에 설치되지 않음).
  등록이 안 되면 맑은 고딕 → 기본 글꼴로 대신 표시됩니다.
※ splash.py 의 문구(TITLE/MSG/SUB)를 바꾸면 아래처럼 다시 만들어야 합니다 (fonttools 필요).
    pyftsubset GmarketSansBold.woff2 --text="공사 발주 자동화 프로그램" \
      --flavor= --output-file=splash_GmarketSansBold.ttf
    pyftsubset NanumGothic.woff2 \
      --text="화면을 준비하고 있습니다처음 실행은 시간이 조금 걸립니다·0123456789초 " \
      --flavor= --output-file=splash_NanumGothic.ttf
  (--flavor= 는 "woff2 아닌 일반 TTF 로 저장" 이라는 뜻 — 빠뜨리면 Windows 가 못 읽음)

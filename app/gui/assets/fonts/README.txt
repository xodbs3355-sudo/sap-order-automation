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

# -*- coding: utf-8 -*-
"""시작 대기창(스플래시) — 본 화면이 준비되는 동안 스켈레톤 + 안내 문구를 보여준다.

왜 따로 있나:
  본 화면(index.html)은 WebView2(Edge 엔진)가 그리는데, 첫 실행 때 이 엔진이
  깨어나는 데 수십 초가 걸릴 수 있다. 그 사이엔 화면 안에 무엇을 넣어도 보이지 않으므로,
  엔진과 무관한 tkinter(파이썬 내장 창 도구)로 '대기창'을 먼저 띄운다.
  → 비유: 공연장 조명(WebView2)이 켜질 때까지 무대 앞에 쳐 두는 막.

위치·크기 원칙:
  - 대기창은 '본 창의 내용 영역(제목줄·테두리를 뺀 안쪽)'과 같은 자리·크기에 뜬다.
  - 처음엔 본 창이 아직 없으므로 "본 창이 화면 중앙에 열릴 때의 내용 영역"을 계산해 뜬다.
  - 본 창 틀이 뜨면 main.py 가 실제 내용 영역 좌표를 딱 한 번 보내 주고(RECT 명령),
    대기창은 그 자리로 옮겨 다시 그린다. 이후 따라다니는 동작은 없다.
  - 대기창은 사용자가 옮길 수 없다(제목줄 없음).

main.py 와의 약속(표준입력/표준출력, 한 줄 단위):
  받는 것  "RECT x y w h"  → 그 화면 좌표(실제 픽셀)로 옮겨 다시 그림
           연결 끊김(EOF)   → 닫힘 (main 이 화면 준비 완료 시 끊음 / main 이 꺼져도 끊김)
  보내는 것 "SHOWN <시각>"  "RECT0 x y w h"(처음 위치)  "FONT ..."(사용 글꼴) — 로그용
  안전장치: 최대 MAX_SECONDS 가 지나면 스스로 닫힌다.

스켈레톤 배치는 실제 화면(index.html)의 늘어나는 규칙을 그대로 따른다(1560x850 등에서 측정).
  우측 패널 250px 고정·오른쪽 끝 / 하단 바 아래 끝 / 표는 남는 폭을 채움.
진행률(%)은 WebView2 가 알려주지 않으므로, 왕복 막대 + 경과 초로 표시한다.

글꼴: tkinter 는 웹 글꼴(woff2)을 못 읽어, 대기창 글자만 담은 작은 TTF
(assets/fonts/splash_*.ttf)를 이 프로세스에서만 잠깐 등록해 쓴다(Windows 에 설치 안 함).
등록이 안 되면 맑은 고딕 → 기본 글꼴 순으로 대신 쓴다(글자 깨짐 방지).
※ 문구를 바꾸면 splash_*.ttf 도 다시 만들어야 한다(방법: assets/fonts/README.txt).
"""

import os
import queue
import sys
import threading
import time

WIN_W, WIN_H = 1560, 850   # main.py create_window 의 창 크기(제목줄·테두리 포함 바깥 크기)
MAX_SECONDS = 180          # 안전장치: 이 시간이 지나면 스스로 닫힘

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_HERE, "assets", "fonts")
_LOGO = os.path.join(_HERE, "assets", "splash_logo.png")

# (TTF 파일, 글꼴 이름) — 이름은 TTF 내부 이름표(name ID 1)와 같아야 한다.
_FONT_TITLE = ("splash_GmarketSansBold.ttf", "Gmarket Sans TTF Bold")
_FONT_BODY = ("splash_NanumGothic.ttf", "NanumGothic")

TITLE = "공사 발주 자동화 프로그램"
MSG = "화면을 준비하고 있습니다"
SUB = "처음 실행은 시간이 조금 걸립니다 · %d초"

# 색상 (본 화면과 맞춤)
BG = "#FFFFFF"
LINE = "#E6E8EE"
SK = (0xEC, 0xEE, 0xF2)        # 스켈레톤 기본색
SK_HI = (0xF7, 0xF8, 0xFA)     # 반짝임 색
SK_R = (0xEC, 0xE4, 0xD8)      # 우측 패널 스켈레톤
SK_R_HI = (0xF6, 0xF1, 0xEA)
ACCENT = "#1E2A44"

# 표 열(1560 기준 x, 폭) — index.html 측정값. 0:체크 1:상태 2:구간코드 3:구간명 4:연장
# 5:승인투자비 6:의뢰일자 7:굴착허가 8:허가청 9:시공업체 10:공사기간
_COLS = [(0, 34), (34, 42), (75, 100), (175, 299), (474, 55), (529, 86), (615, 74),
         (689, 105), (794, 105), (899, 105), (1004, 305)]
_LEFT_BASE = 1309   # 1560 화면에서 표 영역 폭
# 표 영역이 좁아질 때 열별로 줄어드는 비율(1440 화면 측정: 2~9번 열이 나눠서 줄어듦)
_SHRINK = {2: 18, 3: 19, 4: 6, 5: 6, 6: 5, 7: 20, 8: 25, 9: 20}


def _columns(left_w):
    """표 영역 폭에 맞춘 열 [(x, 폭)] — 넓어지면 '구간명'만 늘고, 좁아지면 2~9번 열이 나눠 줄어듦."""
    d = left_w - _LEFT_BASE
    widths = [w for _, w in _COLS]
    if d >= 0:
        widths[3] += d
    else:
        tot = float(sum(_SHRINK.values()))
        for i, k in _SHRINK.items():
            widths[i] = max(20, widths[i] + d * k / tot)
    out, x = [], 0
    for w in widths:
        out.append((x, w))
        x += w
    return out


# ── Windows 도우미 ─────────────────────────────────
def _set_dpi_aware():
    """화면 배율(125%, 150% 등)에서 흐려지지 않게 하고, 배율값을 반환(100% = 1.0)."""
    if os.name != "nt":
        return 1.0
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            return 1.0
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


def _register_private_fonts():
    """대기창 전용 TTF 를 이 프로세스에서만 등록한다(Windows 전용, 설치 아님)."""
    if os.name != "nt":
        return
    import ctypes
    FR_PRIVATE = 0x10
    for fname, _ in (_FONT_TITLE, _FONT_BODY):
        path = os.path.join(_FONT_DIR, fname)
        if os.path.exists(path):
            try:
                ctypes.windll.gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
            except Exception:
                pass


def _estimate_client_rect(root, scale):
    """본 창이 화면 중앙에 열릴 때의 '내용 영역' 화면 좌표(실제 픽셀) 추정.

    본 창 틀이 뜨면 main.py 가 실제 좌표를 보내므로, 여기 값은 그 전까지만 쓰인다.
    """
    ow, oh = int(WIN_W * scale), int(WIN_H * scale)
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            u = ctypes.windll.user32
            wa = wintypes.RECT()
            u.SystemParametersInfoW(0x0030, 0, ctypes.byref(wa), 0)   # 작업 영역(작업표시줄 제외)
            ox = wa.left + (wa.right - wa.left - ow) // 2
            oy = wa.top + (wa.bottom - wa.top - oh) // 2
            # 테두리·제목줄 두께 (SM_CXSIZEFRAME=32, SM_CYSIZEFRAME=33, SM_CXPADDEDBORDER=92,
            #                     SM_CYCAPTION=4)
            bx = u.GetSystemMetrics(32) + u.GetSystemMetrics(92)
            by = u.GetSystemMetrics(33) + u.GetSystemMetrics(92)
            cap = u.GetSystemMetrics(4)
            return ox + bx, oy + by + cap, ow - 2 * bx, oh - 2 * by - cap
        except Exception:
            pass
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    return (sw - ow) // 2, (sh - oh) // 2, ow, oh


def _pick_font(families, wanted):
    """원하는 글꼴이 있으면 그 이름, 없으면 맑은 고딕, 그것도 없으면 기본 글꼴."""
    for name in (wanted, "Malgun Gothic", "맑은 고딕"):
        if name in families:
            return name
    return "TkDefaultFont"


class Splash:
    def __init__(self, root, scale, fonts):
        import tkinter as tk
        self.tk = tk
        self.root = root
        self.S = scale
        self.f_title, self.f_body = fonts
        self.c = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.logo_src = None
        try:
            self.logo_src = tk.PhotoImage(file=_LOGO)    # 높이 56px(2배) 원본
        except Exception:
            pass
        self.blocks = []
        self.t0 = time.perf_counter()

    # ── 좌표 도우미(논리 픽셀 → 실제 픽셀) ──────────
    def s(self, v):
        return int(round(v * self.S))

    def rr_pts(self, x, y, w, h, r):
        s = self.s
        x, y, w, h, r = s(x), s(y), s(w), s(h), s(r)
        r = min(r, w // 2, h // 2)
        return [x + r, y, x + w - r, y, x + w, y, x + w, y + r, x + w, y + h - r, x + w, y + h,
                x + w - r, y + h, x + r, y + h, x, y + h, x, y + h - r, x, y + r, x, y]

    def rrect(self, x, y, w, h, r, **kw):
        """둥근 사각형(Canvas 에 기본 제공이 없어 다각형+smooth 로 그림)."""
        return self.c.create_polygon(self.rr_pts(x, y, w, h, r), smooth=True, **kw)

    def rect(self, x1, y1, x2, y2, **kw):
        s = self.s
        return self.c.create_rectangle(s(x1), s(y1), s(x2), s(y2), **kw)

    def line(self, x1, y1, x2, y2, **kw):
        s = self.s
        return self.c.create_line(s(x1), s(y1), s(x2), s(y2), **kw)

    def sk(self, x, y, w, h, r=5, right=False):
        if w <= 2:
            return
        base, hi = (SK_R, SK_R_HI) if right else (SK, SK_HI)
        i = self.rrect(x, y, w, h, r, fill="#%02x%02x%02x" % base, outline="")
        self.blocks.append((i, self.s(x + w / 2), base, hi))

    # ── 배치 ─────────────────────────────────────
    def place(self, x, y, w, h):
        """화면 좌표(실제 픽셀)에 창을 두고, 그 크기에 맞춰 스켈레톤을 다시 그린다."""
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.c.config(width=w, height=h)
        self.draw(w / self.S, h / self.S)

    def draw(self, W, H):
        """W, H: 내용 영역 크기(논리 픽셀). index.html 과 같은 규칙으로 배치."""
        c, s, sk, rect, line = self.c, self.s, self.sk, self.rect, self.line
        c.delete("all")
        self.blocks = []
        L = W - 251          # 표 영역 폭 (우측 패널 250 + 경계선 1)
        rx = W - 250         # 우측 패널 시작
        cols = _columns(L)

        # 상단 바
        title_x = 20
        if self.logo_src is not None:
            self.logo = self.logo_src if self.S >= 1.5 else self.logo_src.subsample(2)
            c.create_image(s(20), s(29), image=self.logo, anchor="w")
            title_x = 20 + self.logo.width() / self.S + 8
        # 제목: 본 화면과 같은 25px. 글꼴 자체가 Bold 라 '굵게'를 또 걸지 않는다
        # (대체 글꼴일 때만 굵게).
        bold = () if self.f_title == _FONT_TITLE[1] else ("bold",)
        tid = c.create_text(s(title_x), s(29), text=TITLE, anchor="w",
                            font=(self.f_title, -s(25)) + bold, fill="#1A1F2B")
        try:   # 제목 옆 부제목 "(63A & 10m이하 …)" 자리
            sk(c.bbox(tid)[2] / self.S + 8, 18, 178, 12, 3)
        except Exception:
            pass
        sk(W - 373, 14, 114, 31, 8)      # 선택 건 실행
        sk(W - 129, 13, 109, 33, 8)      # 단가표 관리
        line(0, 59, W, 59, fill=LINE)

        # 툴바 1줄
        rect(0, 60, L, 98, fill="#F8F9FB", outline="")
        sk(12, 70, 118, 16)                              # SAP 의뢰공사 리스트
        sk(cols[7][0] - 155, 66, 142, 25, 6)             # 선택행 입력정보 지우기
        sk(L - 251, 66, 73, 25, 6)                       # 선택 적용
        sk(L - 168, 67, 71, 23, 6)                       # 전체 적용
        sk(L - 87, 66, 79, 25, 6)                        # 되돌리기
        # 툴바 2줄
        rect(0, 98, L, 142, fill="#F0F4FF", outline="")
        sk(12, 103, 164, 33, 8)                          # SAP 리스트 불러오기
        sk(198, 113, 196, 15)                            # 선택/전체 건수
        for k in (7, 8, 9):                              # 굴착허가·허가청·시공업체 콤보
            sk(cols[k][0] + 8, 108, cols[k][1] - 17, 24, 5)
        x10 = cols[10][0]
        sk(x10 + 8, 108, 107, 24, 5)                     # 공사기간 시작
        sk(x10 + 118, 108, 28, 23, 5)
        sk(x10 + 159, 108, 107, 24, 5)                   # 공사기간 끝
        sk(x10 + 269, 108, 28, 23, 5)
        # 표 머리
        rect(0, 142, L, 176, fill="#EEF0F4", outline="")
        for i, (x, w) in enumerate(cols):
            tw = 14 if i == 0 else min(w - 16, 26 + 6 * (i % 3))
            sk(x + (w - tw) / 2, 153, tw, 13, 3)

        # 표 본문(빈 행)
        y = 190
        bottom = H - 35
        row = 0
        while y + 30 < bottom:
            for i, (x, w) in enumerate(cols):
                if i == 0:
                    sk(x + 10, y + 6, 14, 14, 3)
                elif i == 3:
                    sk(x + 15, y + 6, max(30, (w - 40) * (1 - row * 0.045)), 14, 4)
                elif i >= 7:
                    sk(x + 11, y + 4, w - 24, 18, 4)
                else:
                    sk(x + 8, y + 6, w - 16, 14, 4)
            line(0, y + 30, L, y + 30, fill="#F1F2F5")
            y += 44
            row += 1

        # 우측 패널
        rect(rx, 60, W, H - 35, fill="#F8F4EE", outline="")
        line(rx - 1, 60, rx - 1, H - 35, fill=LINE)
        sk(rx + 16, 73, 74, 16, 4, right=True)
        sk(rx + 16, 95, 40, 11, 3, right=True)
        rect(rx + 10, 133, rx + 240, 313, fill="#FFFFFF", outline="#E3DCCF")
        sk(rx + 20, 141, 46, 12, 3, right=True)
        sk(rx + 186, 141, 44, 12, 3, right=True)
        sk(rx + 12, 322, 82, 11, 3, right=True)
        for i in range(6):
            yy = 338 + i * 45
            self.rrect(rx + 10, yy + 2, 230, 41, 10, fill="#FBF8F3", outline="#ECE4D8")
            sk(rx + 22, yy + 11, 23, 23, 6, right=True)
            sk(rx + 55, yy + 10, 56, 11, 3, right=True)
            sk(rx + 55, yy + 25, 70, 9, 3, right=True)
            sk(rx + 208, yy + 17, 22, 9, 3, right=True)
        rect(rx, H - 90, W, H - 35, fill="#EDE5D5", outline="")
        sk(rx + 12, H - 78, 226, 4, 2, right=True)       # 진행 막대 자리
        sk(rx + 12, H - 62, 34, 10, 3, right=True)       # 대기 중
        sk(W - 60, H - 68, 48, 23, 6, right=True)        # 로그 버튼

        # 하단 바
        line(0, H - 35, W, H - 35, fill=LINE)
        sk(W - 247, H - 24, 114, 13, 3)                  # TSRM 전송 건너뜀
        sk(W - 117, H - 24, 97, 13, 3)                   # 버전

        # 가운데 안내 카드(표 영역 가운데)
        cx, cy = L / 2, (176 + H - 35) / 2
        self.rrect(cx - 190, cy - 52, 380, 104, 14, fill="#FFFFFF", outline="#E3E6EC")
        c.create_text(s(cx), s(cy - 18), text=MSG, font=(self.f_body, -s(17), "bold"),
                      fill="#1A1F2B")
        self.sub = c.create_text(s(cx), s(cy + 6), text=SUB % self.elapsed(),
                                 font=(self.f_body, -s(13)), fill="#7A8090")
        self.bar_x, self.bar_y, self.bar_w, self.seg = cx - 150, cy + 26, 300, 90
        self.rrect(self.bar_x, self.bar_y, self.bar_w, 6, 3, fill="#E9ECF2", outline="")
        self.bar = self.rrect(self.bar_x, self.bar_y, self.seg, 6, 3, fill=ACCENT, outline="")
        self.width_px = s(W)

    # ── 움직임 ────────────────────────────────────
    def elapsed(self):
        return int(time.perf_counter() - self.t0)

    def animate(self):
        t = time.perf_counter() - self.t0
        # 반짝임: 왼→오로 지나가는 밝은 띠(블록 단위로 색을 바꿔 표현)
        band = (t * 900 * self.S) % (self.width_px + self.s(600)) - self.s(300)
        reach = self.s(260)
        for i, xc, base, hi in self.blocks:
            k = max(0.0, 1 - abs(xc - band) / reach)
            self.c.itemconfigure(i, fill="#%02x%02x%02x" % tuple(
                int(base[n] + (hi[n] - base[n]) * k) for n in range(3)))
        # 왕복 막대(정확한 %를 알 수 없으므로)
        p = (t * 0.6) % 2
        p = p if p < 1 else 2 - p
        self.c.coords(self.bar, *self.rr_pts(self.bar_x + p * (self.bar_w - self.seg),
                                             self.bar_y, self.seg, 6, 3))
        self.c.itemconfigure(self.sub, text=SUB % int(t))


def _say(msg):
    """main.py 로 한 줄 알림(로그용). 실패해도 대기창은 계속."""
    try:
        print(msg, flush=True)
    except Exception:
        pass


def main():
    scale = _set_dpi_aware()
    _register_private_fonts()

    import tkinter as tk
    from tkinter import font as tkfont

    root = tk.Tk()
    root.withdraw()                     # 다 그린 뒤에 한 번에 보이기
    root.overrideredirect(True)         # 제목줄 없음 → 사용자가 옮길 수 없음
    root.attributes("-topmost", True)   # 본 창(빈 흰 화면)보다 위에

    families = set(tkfont.families(root))
    fonts = (_pick_font(families, _FONT_TITLE[1]), _pick_font(families, _FONT_BODY[1]))
    sp = Splash(root, scale, fonts)

    x, y, w, h = _estimate_client_rect(root, scale)
    sp.place(x, y, w, h)

    # main.py 에서 오는 명령: RECT(한 번) / 연결 끊김(닫기)
    cmds = queue.Queue()

    def watch_stdin():
        try:
            for ln in sys.stdin:
                cmds.put(ln.strip())
        except Exception:
            pass
        cmds.put("CLOSE")

    if sys.stdin is not None:
        threading.Thread(target=watch_stdin, daemon=True).start()

    def tick():
        try:
            while True:
                cmd = cmds.get_nowait()
                if cmd == "CLOSE":
                    root.destroy()
                    return
                if cmd.startswith("RECT "):
                    try:
                        nx, ny, nw, nh = (int(v) for v in cmd.split()[1:5])
                        if nw > 200 and nh > 200:
                            sp.place(nx, ny, nw, nh)
                    except Exception:
                        pass
        except queue.Empty:
            pass
        if time.perf_counter() - sp.t0 > MAX_SECONDS:
            root.destroy()
            return
        sp.animate()
        root.after(33, tick)

    root.deiconify()
    root.update()
    _say("SHOWN %.3f" % time.time())
    _say("RECT0 %d %d %d %d" % (x, y, w, h))
    _say("FONT %s | %s | scale %.2f" % (fonts[0], fonts[1], scale))
    tick()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # 대기창은 보조 기능 — 실패해도 본 프로그램에 영향 없이 조용히 끝낸다.
        pass

"""SAP 공사 발주 자동화 프로그램 — 앱 진입점.

pywebview로 gui/index.html을 로컬 데스크탑 창으로 띄우는 최소 뼈대.
자동화 로직(SAP 연결·T-code 처리)은 이후 단계에서 추가한다.
"""

import os

import webview


def get_gui_path() -> str:
    """gui/index.html의 절대 경로를 반환한다."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "gui", "index.html")


def main() -> None:
    """pywebview 창을 생성하고 GUI를 실행한다."""
    webview.create_window(
        title="공사 발주 자동화 프로그램",
        url=get_gui_path(),
        width=1375,
        height=760,
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()

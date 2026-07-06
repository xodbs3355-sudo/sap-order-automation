"""SAP 공사 발주 자동화 프로그램 — 앱 진입점.

pywebview로 gui/index.html 을 로컬 데스크탑 창으로 띄운다.
화면(JS)과 Python 을 잇는 창구(Api 클래스)를 pywebview 에 등록해,
화면에서 window.pywebview.api.함수() 로 Python 을 호출할 수 있게 한다.

자동화 로직(SAP 연결·T-code 처리)은 이후 단계에서 추가한다.
"""

import os

import webview

from config_manager import ConfigManager
from sap import connector
from sap import zrec0002


def get_gui_path() -> str:
    """gui/index.html 의 절대 경로를 반환한다."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "gui", "index.html")


class Api:
    """화면(JS)에서 호출하는 Python 창구.

    여기 등록된 메서드는 화면에서 window.pywebview.api.<메서드>() 로 부를 수 있다.
    반환값은 JSON 으로 자동 변환되어 화면으로 전달된다.
    """

    def __init__(self):
        # 설정 관리자(창고지기). 파일이 없거나 깨졌으면 앱은 뜨되 기능만 비활성.
        try:
            self.cfg = ConfigManager()
            self.config_error = None
        except Exception as e:
            self.cfg = None
            self.config_error = str(e)

    # ── 단가표 ─────────────────────────────────────────────
    def get_price_table(self):
        """연도별 단가표(dict)를 반환. 모달을 열 때 화면이 호출."""
        if self.cfg is None:
            return {}
        self.cfg.reload()
        return self.cfg.data.get("단가표", {}).get("연도별", {})

    def save_price_table(self, price_by_year):
        """화면에서 보낸 연도별 단가표를 settings.json 에 저장한다.

        '연도별' 부분만 교체하고 '자재코드'(고정) 등 나머지는 그대로 둔다.
        """
        if self.cfg is None:
            return {"ok": False, "error": self.config_error or "설정을 불러오지 못했습니다."}
        try:
            self.cfg.reload()
            self.cfg.data.setdefault("단가표", {})["연도별"] = price_by_year
            self.cfg.save()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── 목록(드롭다운용) ───────────────────────────────────
    def get_permit_offices(self):
        """허가청 목록(코드+이름)."""
        return self.cfg.permit_offices() if self.cfg else []

    def get_vendors(self):
        """토목배관업체 목록(코드+이름)."""
        return self.cfg.vendors() if self.cfg else []

    # ── 의뢰공사 리스트 ────────────────────────────────────
    def load_request_list(self):
        """ZREC0002 조회로 의뢰 공사 목록을 읽어 반환(화면 '리스트 불러오기').

        성공: {"ok": True, "columns": [...], "rows": [...], "row_count": n}
        실패: {"ok": False, "error": 사유}
        """
        try:
            session = connector.get_session()
        except connector.SapConnectionError as e:
            return {"ok": False, "error": str(e)}
        try:
            data = zrec0002.fetch_request_list(session)
            data["ok"] = True
            return data
        except Exception as e:
            return {"ok": False, "error": "목록 조회 실패: %s" % e}

    # ── SAP 연결 ───────────────────────────────────────────
    def check_sap_connection(self):
        """SAP 연결 상태를 점검해 반환(화면의 '연결 확인'에서 호출).

        성공: {"ok": True, system/client/user/transaction/language}
        실패: {"ok": False, "error": 사유}
        """
        return connector.check_connection()

    # ── 상태 ───────────────────────────────────────────────
    def get_status(self):
        """설정 로드 상태·회사코드·테스트모드 등 기본 정보."""
        if self.cfg is None:
            return {"config_ok": False, "error": self.config_error}
        return {
            "config_ok": True,
            "company_code": self.cfg.company_code,
            "test_server_mode": self.cfg.test_server_mode,
            "problems": self.cfg.validate(),
        }


def main() -> None:
    """pywebview 창을 생성하고 GUI 를 실행한다."""
    api = Api()
    webview.create_window(
        title="SAP Work Order Automation",
        url=get_gui_path(),
        js_api=api,
        width=1440,
        height=800,
        min_size=(1200, 700),   # 이 크기 아래로는 축소 불가(축소 시 레이아웃 깨짐 방지)
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()

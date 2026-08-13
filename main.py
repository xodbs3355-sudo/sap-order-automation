"""SAP 공사 발주 자동화 프로그램 — 앱 진입점.

pywebview로 gui/index.html 을 로컬 데스크탑 창으로 띄운다.
화면(JS)과 Python 을 잇는 창구(Api 클래스)를 pywebview 에 등록해,
화면에서 window.pywebview.api.함수() 로 Python 을 호출할 수 있게 한다.

자동화 로직(SAP 연결·T-code 처리)은 이후 단계에서 추가한다.
"""

import os
import json

import webview

import applog
from config_manager import ConfigManager
from sap import connector
from sap import zrec0002
from sap import region
from sap import pipeline


# 파이프라인 단계 코드 → 우측 패널 단계 카드 인덱스(0~5)
_STEP_INDEX = {code: i for i, (code, _name) in enumerate(pipeline.STEPS)}


def _digits(s):
    """문자열에서 숫자만 뽑아 int. 없으면 None. ('3,651,000원'→3651000)"""
    d = "".join(ch for ch in str(s) if ch.isdigit())
    return int(d) if d else None


def _year_of(date_str):
    """'2026-08-01' / '2026.08.01' 등에서 연도(4자리)를 뽑는다. 없으면 None."""
    d = "".join(ch for ch in str(date_str) if ch.isdigit())
    return d[:4] if len(d) >= 4 else None


def _short_name(name):
    """패널 표시용으로 구간명을 짧게(뒤 '인입공급관' 등 제거)."""
    s = str(name or "").strip()
    for tail in (" 인입공급관", " 인입 공급관", "인입공급관"):
        if s.endswith(tail):
            s = s[: -len(tail)].strip()
            break
    return s or name


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
        # pywebview 창(화면에 로그/진행상태를 밀어넣기 위한 통로). main() 에서 연결.
        self.window = None

    # ── 화면 호출(파이썬 → JS) ─────────────────────────────
    def _js(self, fn, *args):
        """화면의 JS 함수를 호출한다(진행상태·로그 실시간 갱신용).

        예: self._js("runStep", 2, "done") → 화면에서 runStep(2,"done") 실행.
        창이 아직 없거나 실패해도 조용히 무시(로직은 계속).
        """
        if not self.window:
            return
        try:
            payload = ", ".join(json.dumps(a, ensure_ascii=False) for a in args)
            self.window.evaluate_js("%s(%s)" % (fn, payload))
        except Exception:
            pass

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

    # ── 선택 건 자동 발주 ──────────────────────────────────
    def _build_work(self, row, skip_tsrm):
        """화면 한 행(row dict) → 파이프라인 입력(work dict)으로 변환.

        반환: (work, None) 성공 / (None, 사유) 실패(수동 처리 대상).
        이름·주소를 코드로 바꾸고, 승인투자비로 재질/연장/PLP를 도출한다.
        """
        cmp = str(row.get("cmp") or "").strip()
        name = str(row.get("name") or "").strip()
        if not cmp:
            return None, "구간코드(CMP)가 없습니다."

        # 굴착허가 대상/비대상 → 1/2
        dig_raw = str(row.get("dig") or "").strip()
        if dig_raw == "대상":
            dig = "1"
        elif dig_raw == "비대상":
            dig = "2"
        else:
            return None, "굴착허가가 선택되지 않았습니다."

        # 허가청 이름 → 코드
        permit_name = str(row.get("permit") or "").strip()
        permit = self.cfg.permit_code(permit_name)
        if not permit:
            return None, "허가청 미선택/미등록: '%s'" % permit_name

        # 시공업체 이름 → 코드
        vendor_name = str(row.get("vendor") or "").strip()
        vendor = self.cfg.vendor_code(vendor_name)
        if not vendor:
            return None, "시공업체 미선택/미등록: '%s'" % vendor_name

        # 공사기간
        start = str(row.get("start") or "").strip()
        end = str(row.get("end") or "").strip()
        if not start or not end:
            return None, "공사기간(시작/종료)이 입력되지 않았습니다."

        # 구간명 → 시/군·동 코드
        try:
            reg = region.resolve(name, self.cfg)
        except region.RegionError as e:
            return None, "지역 코드 확정 실패 — %s" % e

        # 승인투자비 → 재질/연장/PLP (연도 자동 판별)
        cost = _digits(row.get("cost"))
        if cost is None:
            return None, "승인투자비를 읽지 못했습니다."
        prefer_year = _year_of(row.get("date")) or _year_of(start)
        lp = self.cfg.lookup_price_smart(cost, prefer_year=prefer_year)
        if not lp:
            return None, ("단가표 불일치(승인투자비 %s원) — 수동 처리 필요"
                          % format(cost, ","))

        work = {
            "cmp": cmp,
            "sigun": reg["sigun_code"],
            "dong": reg["dong_code"],
            "permit": permit,
            "dig": dig,
            "road": lp["material"],
            "length": lp["length"],
            "plp": lp["with_plp"],
            "vendor": vendor,
            "gu_name": name,
            "start": start,
            "end": end,
            "echk": False,
            "skip_tsrm": bool(skip_tsrm) or self.cfg.test_server_mode,
            # 로그·표시용 부가정보
            "_permit_name": permit_name,
            "_vendor_name": vendor_name,
            "_region": reg,
            "_price": lp,
            "_cost": cost,
        }
        return work, None

    def run_selected(self, rows, skip_tsrm=True):
        """화면에서 선택한 행들을 순서대로 자동 발주한다(6단계 × N건).

        rows: [{cmp,name,length,cost,date,dig,permit,vendor,start,end}, ...]
        진행 상태·로그는 self._js(...) 로 화면에 실시간 반영한다.
        반환: {"ok":bool, "results":[...], "success":n, "total":n, "error":..}
        """
        if self.cfg is None:
            return {"ok": False, "error": self.config_error or "설정 로드 실패"}
        rows = rows or []
        if not rows:
            return {"ok": False, "error": "선택된 건이 없습니다."}

        applog.section("자동 발주 시작 · 선택 %d건 (TSRM %s)"
                       % (len(rows), "생략" if skip_tsrm else "발송"))

        # SAP 연결
        try:
            session = connector.get_session()
        except connector.SapConnectionError as e:
            applog.error("SAP 연결 실패: %s" % e)
            return {"ok": False, "error": str(e)}
        conn = connector.check_connection()
        if conn.get("ok"):
            applog.info("SAP 연결됨 · 시스템 %s / 클라이언트 %s / 사용자 %s"
                        % (conn.get("system"), conn.get("client"), conn.get("user")))

        # 우측 '실행 대상' 패널 초기화
        names = [_short_name(r.get("name") or r.get("cmp") or "") for r in rows]
        self._js("runInit", names)

        results = []
        for i, row in enumerate(rows):
            cmp = str(row.get("cmp") or "").strip()
            sname = _short_name(row.get("name") or cmp)
            self._js("runWork", i, "cur", sname)

            # 완료 리포트용 한 줄(상태: skip=건너뜀 / success=성공 / fail=실패)
            rep = {"status": "skip", "cmp": cmp,
                   "name": str(row.get("name") or ""),
                   "dong": "", "material": "", "vendor": "",
                   "gongsa_no": "", "reason": ""}

            work, err = self._build_work(row, skip_tsrm)
            if err:
                rep["reason"] = err
                applog.warn("[%d/%d] %s — 준비 실패(건너뜀): %s"
                            % (i + 1, len(rows), cmp, err))
                self._js("runWork", i, "fail", sname)
                results.append(rep)
                continue

            reg = work["_region"]
            lp = work["_price"]
            rep["dong"] = "%s(%s)" % (reg["dong_name"], reg["dong_code"])
            rep["material"] = "%s %sm%s" % (work["road"], work["length"],
                                            " · PLP" if work["plp"] else "")
            rep["vendor"] = work["_vendor_name"]
            applog.info(
                "[%d/%d] %s 준비완료 → 시군 %s(%s)/동 %s(%s) · 재질 %s·연장 %sm·PLP %s "
                "(투자비 %s원, %s년) · 허가청 %s(%s)/굴착 %s · 업체 %s(%s) · 기간 %s~%s"
                % (i + 1, len(rows), cmp,
                   reg["sigun_name"], reg["sigun_code"], reg["dong_name"], reg["dong_code"],
                   work["road"], work["length"], "포함" if work["plp"] else "없음",
                   format(work["_cost"], ","), lp.get("year"),
                   work["_permit_name"], work["permit"], work["dig"],
                   work["_vendor_name"], work["vendor"], work["start"], work["end"]))

            def on_prog(step, status, info="", _i=i, _cmp=cmp):
                idx = _STEP_INDEX.get(step)
                if idx is not None:
                    self._js("runStep", idx, status)
                if status == "start":
                    applog.info("   [%d] %s 시작…" % (_i + 1, step))
                elif status == "done":
                    applog.success("   [%d] %s 완료%s"
                                   % (_i + 1, step, (" · " + info) if info else ""))
                elif status == "fail":
                    applog.error("   [%d] %s 실패 · %s" % (_i + 1, step, info))

            try:
                res = pipeline.run_one(session, work, on_progress=on_prog)
                self._js("runWork", i, "done", sname)
                rep["status"] = "success"
                rep["gongsa_no"] = res.get("gongsa_no") or ""
                rep["safety"] = res.get("safety")
                applog.success(
                    "[%d/%d] %s 발주 완료 · 공사번호 %s · 산안비 %s"
                    % (i + 1, len(rows), cmp, res.get("gongsa_no"), res.get("safety")))
            except pipeline.PipelineError as e:
                idx = _STEP_INDEX.get(e.step)
                if idx is not None:
                    self._js("runStep", idx, "fail")
                self._js("runWork", i, "fail", sname)
                rep["status"] = "fail"
                rep["reason"] = "%s 단계: %s" % (e.step, e.cause)
                applog.exc("[%d/%d] %s — %s 단계 실패: %s"
                           % (i + 1, len(rows), cmp, e.step, e.cause))
            except Exception as e:
                self._js("runWork", i, "fail", sname)
                rep["status"] = "fail"
                rep["reason"] = "예상치 못한 오류: %s" % e
                applog.exc("[%d/%d] %s — 예상치 못한 오류: %s"
                           % (i + 1, len(rows), cmp, e))
            results.append(rep)

        n_ok = sum(1 for r in results if r["status"] == "success")
        n_skip = sum(1 for r in results if r["status"] == "skip")
        n_fail = sum(1 for r in results if r["status"] == "fail")
        applog.section("자동 발주 종료 · 성공 %d / 실패 %d / 건너뜀 %d"
                       % (n_ok, n_fail, n_skip))
        self._js("runFinish", n_ok, len(results))
        return {"ok": True, "results": results, "success": n_ok,
                "fail": n_fail, "skipped": n_skip, "total": len(results)}

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
    window = webview.create_window(
        title="SAP Work Order Automation",
        url=get_gui_path(),
        js_api=api,
        width=1560,
        height=800,
        # 표(최소 약 1252px) + 실행단계 패널(250px)이 잘리지 않는 최소 창 폭.
        # 이 아래로는 축소 불가 → 공사기간 등 열이 잘리지 않는다.
        min_size=(1530, 700),
        resizable=True,
    )
    # 화면 연결: 파이썬 로그를 처리 로그 창에도 실시간으로 찍는다.
    api.window = window
    applog.set_gui_emit(lambda m, l: api._js("addLog", m, l))
    applog.info("프로그램 시작 · 로그 파일: %s" % applog.log_file_path())
    webview.start()


if __name__ == "__main__":
    main()

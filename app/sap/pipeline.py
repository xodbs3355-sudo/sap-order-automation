# -*- coding: utf-8 -*-
"""자동 발주 파이프라인 — 한 공사에 대해 6개 T-code 를 순서대로 실행한다.

순서(단계 간 값 전달 포함):
    1. ZREC0002  공사의뢰 접수         (그리드 행 선택 → 접수)
    2. ZREC0100  공사번호 생성          → 공사번호(gongsa_no) 산출
    3. ZMEC0210  설계예산서 작성         → 산업안전보건관리비(safety) 산출
    4. ZREC2030  발주구간 생성(업체 지정)
    5. ZREC2040  시행품의 생성
    6. ZREC0208  공사발주서 작성/발송     (연장·산안비 사용)

핵심 데이터 흐름:
    ZREC0100 → 공사번호 → (0210·2030·2040·0208 이 사용)
    ZMEC0210 → 산업안전보건관리비 → (0208 특기사항에 사용)

입력(work dict, 한 공사분) — 키는 영어(인코딩 안전):
    cmp        : 구간코드 — ZREC0002 접수 시 이 코드로 재조회·선택하고,
                 ZREC0100 조회에도 사용(행 번호에 의존하지 않음).
    sigun      : 시/군 코드 (ZREC0100)
    dong       : 동읍면리 코드 (ZREC0100)
    permit     : 허가청 코드 (ZREC0100). 사유지면 "" (빈값 → 허가청 칸 미입력)
    private_land : 사유지 여부(bool). True 면 ZMEC0210 점용료 2줄 모두 제외
    dig        : 굴착허가 "1"(대상)/"2"(비대상) (ZREC0100)
    road       : 도로재질 "ASP"/"CONC" (ZMEC0210)
    length     : 연장(m) (ZMEC0210 자재·수량, ZREC0208 공사개요)
    plp        : 기존관 PLP 여부(bool) (ZMEC0210)
    vendor     : 시공업체 코드 (ZREC2030)
    gu_name    : 구간명 (ZREC2040 목적 자동생성)
    start      : 공사기간 시작 "YYYY-MM-DD" (ZREC2040·ZREC0208)
    end        : 공사기간 종료 (ZREC2040·ZREC0208)
    echk       : 전자시행품의 여부(bool, 기본 False) (ZREC2040)
    skip_tsrm  : TSRM 발송 생략 여부(bool, 기본 True) (ZREC0208)

진행 알림:
    on_progress(step_code, status, info) 콜백으로 각 단계 상태를 알린다.
      status = "start" | "done" | "fail"
    (GUI 실행단계 패널 갱신 등에 사용. 없으면 무시.)

SAP 세션 위에서만 실제 동작한다(각 T-code 함수가 내부에서 화면 이동).
"""

from sap import connector  # noqa: F401  (연결 타입 참조/일관성)
from sap import zrec0002, zrec0100, zmec0210, zrec2030, zrec2040, zrec0208

# 단계 정의 (코드, 이름) — GUI 표시·순서 참조용
STEPS = [
    ("ZREC0002", "공사의뢰 접수"),
    ("ZREC0100", "공사번호 생성"),
    ("ZMEC0210", "설계예산서 작성"),
    ("ZREC2030", "발주구간 생성"),
    ("ZREC2040", "시행품의 생성"),
    ("ZREC0208", "발주서 발송"),
]


class PipelineError(Exception):
    """파이프라인 도중 실패. step(어느 단계), cause(원인)를 담는다."""

    def __init__(self, step, cause):
        self.step = step
        self.cause = cause
        super().__init__("%s 단계 실패: %s" % (step, cause))


def run_one(session, work, on_progress=None):
    """한 공사(work)에 대해 6개 T-code 를 순서대로 실행한다.

    성공 시 dict 반환:
        {"gongsa_no": 공사번호, "safety": 산안비, "message": 마지막 상태메시지}
    도중 실패 시 PipelineError 를 던진다(어느 단계에서 멈췄는지 포함).
    """
    def prog(step, status, info=""):
        if on_progress:
            try:
                on_progress(step, status, info)
            except Exception:
                pass

    def step(code, fn):
        """한 단계를 실행하며 시작/완료/실패를 알린다. 실패 시 PipelineError."""
        prog(code, "start")
        try:
            result = fn()
        except Exception as e:
            prog(code, "fail", str(e))
            raise PipelineError(code, e)
        prog(code, "done", "" if result is None else str(result))
        return result

    # 1) 공사의뢰 접수 — 구간코드(CMP)로 재조회·선택(접수 후 순번 밀림 방지)
    step("ZREC0002", lambda: zrec0002.receive_by_cmp(session, work["cmp"]))

    # 2) 공사번호 생성
    gongsa_no = step("ZREC0100", lambda: zrec0100.create_work_order(
        session, work["cmp"], work["sigun"], work["dong"], work["permit"], work["dig"]))
    if not gongsa_no:
        # 공사번호를 못 읽으면 이후 단계 진행 불가
        prog("ZREC0100", "fail", "공사번호를 읽지 못했습니다.")
        raise PipelineError("ZREC0100", "공사번호를 읽지 못했습니다.")

    # 3) 설계예산서 작성 → 산업안전보건관리비
    #    사유지(private_land)면 점용료 2줄 제외, 아니면 권역(sigun)·연장으로 면제 판정.
    safety = step("ZMEC0210", lambda: zmec0210.create_design_budget(
        session, gongsa_no, work["road"], work["length"], work.get("plp", False),
        sigun_code=work.get("sigun"), private_land=work.get("private_land", False)))

    # 4) 발주구간 생성(업체 지정)
    step("ZREC2030", lambda: zrec2030.create_order_section(
        session, gongsa_no, work["vendor"]))

    # 5) 시행품의 생성
    step("ZREC2040", lambda: zrec2040.create_approval(
        session, gongsa_no, work["gu_name"], work["start"], work["end"],
        work.get("echk", False)))

    # 6) 공사발주서 작성/발송 (연장·산안비 사용)
    message = step("ZREC0208", lambda: zrec0208.create_purchase_order(
        session, gongsa_no, work["length"], safety, work["start"], work["end"],
        work.get("skip_tsrm", True)))

    return {"gongsa_no": gongsa_no, "safety": safety, "message": message}


def run_many(session, works, on_progress=None, on_work=None):
    """여러 공사를 순서대로 실행한다.

    on_work(index, work, status, result_or_error) 콜백으로 공사 단위 상태를 알린다.
      status = "start" | "done" | "fail"
    반환: 공사별 결과 리스트 [{"ok":bool, "gongsa_no":.., "error":..}, ...]
    """
    results = []
    for i, work in enumerate(works):
        if on_work:
            try:
                on_work(i, work, "start", None)
            except Exception:
                pass
        try:
            res = run_one(session, work, on_progress=on_progress)
            results.append({"ok": True, **res})
            if on_work:
                try:
                    on_work(i, work, "done", res)
                except Exception:
                    pass
        except PipelineError as e:
            results.append({"ok": False, "step": e.step, "error": str(e.cause)})
            if on_work:
                try:
                    on_work(i, work, "fail", e)
                except Exception:
                    pass
            # 한 공사 실패해도 다음 공사는 계속 진행
    return results

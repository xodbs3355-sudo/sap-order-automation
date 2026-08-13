# -*- coding: utf-8 -*-
"""ZREC0208 — 공사발주서 작성/발송 (마지막 단계).

처리 개요(실제 녹화 기준):
    1. ZREC0208 진입 → 발주구분(SO_GYGUB)=20 + 공사번호(SO_GSCD) → 조회(tbar[1]/btn[8])
    2. 조회된 공사 행 선택(GRID selectedRows=0)
    3. 발주서 작성(tbar[1]/btn[45]) → 발주서 작성 화면
       ※ 시행품의가 끝난 정상 건이면 바로 작성 화면으로 넘어간다.
         (시행품의 미완료 테스트 데이터일 때만 "시행품의 먼저" 경고 팝업이 뜨며, 그건 무시)
    4. 작성 화면 입력(TAB02):
         - 공사기간 시작/종료(IT_207-SGSYMD / EGSYMD) : "YYYY.MM.DD"
         - 공사개요(IT_207-GEYO)   : "PE 63A {연장}M 인입공급관"  (63A 고정, 연장 가변)
         - 특기사항(IT_207-SPCTH1~5):
             1. 폐기물 물량 5ton이상 예상 시 사전신고 필수
             2. 산업안전보건관리비 : {금액}원(VAT 별도)     ← ZMEC0210에서 읽은 값
             3. SHE/기본안전수칙/시방서 준수(설계변경 시 협의요청 필수)
             4. 공사서류 제출기한 준수(준공일로부터 10일)
             5. 준공서류 3회 반려 시 차기입찰 제한
    5. 저장(tbar[1]/btn[13]) → "예"
    6. TSRM 발송(tbar[1]/btn[38]) → "예"   ※ 테스트/건너뜀이면 생략
    7. 정상 처리 여부(상태바) 확인

나머지 필드(업체정보·각종 비용·공사지원담당자·발주차수 등)는 앞 단계에서
자동으로 채워져 있으므로 건드리지 않는다.

필드 주소는 SAP Script Recording 실측값. Windows + SAP 에서만 실제 동작한다.
"""

from sap import connector

# ── 조회 화면 ──────────────────────────────────────────────
SEL_GYGUB = "wnd[0]/usr/ctxtSO_GYGUB-LOW"      # 발주구분 (20 고정)
SEL_GSCD = "wnd[0]/usr/ctxtSO_GSCD-LOW"        # 공사번호
BTN_QUERY = "wnd[0]/tbar[1]/btn[8]"            # 조회
GRID = "wnd[0]/usr/cntlGRID1/shellcont/shell/shellcont[1]/shell"  # 결과 그리드
BTN_MAKE = "wnd[0]/tbar[1]/btn[45]"            # 발주서 작성(→ 작성 화면)
POP_OK = "wnd[1]/tbar[0]/btn[0]"               # 팝업 확인

# ── 발주서 작성 화면(TAB02) ────────────────────────────────
_T = "wnd[0]/usr/tabsTS_MAIN/tabpTAB01/ssubSA_MAIN:SAPMZEC0208:0100/"
FLD_SGSYMD = _T + "ctxtIT_207-SGSYMD"          # 공사기간 시작
FLD_EGSYMD = _T + "ctxtIT_207-EGSYMD"          # 공사기간 종료
FLD_GEYO = _T + "txtIT_207-GEYO"               # 공사개요
FLD_SPCTH = _T + "txtIT_207-SPCTH%d"           # 특기사항 1~5

BTN_SAVE = "wnd[0]/tbar[1]/btn[13]"            # 저장
BTN_TSRM = "wnd[0]/tbar[1]/btn[38]"            # TSRM 발송
POP_YES = "wnd[1]/usr/btnSPOP-OPTION1"         # "예"

# ── 고정 특기사항 (2~5). 1번은 고정, 2번은 산안비로 동적 생성 ──
SPCTH_WASTE = "폐기물 물량 5ton이상 예상 시 사전신고 필수"                    # 1
SPCTH_SHE = "SHE/기본안전수칙/시방서 준수(설계변경 시 협의요청 필수)"          # 3
SPCTH_SUBMIT = "공사서류 제출기한 준수(준공일로부터 10일)"                     # 4
SPCTH_REJECT = "준공서류 3회 반려 시 차기입찰 제한"                           # 5

GYGUB = "20"


def _fmt_date(x):
    """날짜를 "YYYY.MM.DD" 형식으로. (구분자 -,/ 는 . 으로 통일)"""
    return str(x).strip().replace("-", ".").replace("/", ".")


def _work_summary(length):
    """공사개요 문자열: "PE 63A {연장}M 인입공급관" (연장은 정수 M)."""
    try:
        n = int(float(str(length)))
    except Exception:
        n = length
    return "PE 63A %sM 인입공급관" % n


def _dismiss_info_popup(session):
    """작성 진입 시 뜰 수 있는 안내/경고 팝업을 닫는다(있으면). 없으면 무시.

    정상 건이면 팝업 없이 바로 작성 화면으로 넘어간다.
    """
    try:
        session.findById("wnd[1]")
    except Exception:
        return
    try:
        session.findById(POP_OK).press()
    except Exception:
        try:
            session.findById("wnd[1]").sendVKey(0)
        except Exception:
            pass


def _read_status(session):
    """하단 상태바 메시지를 읽어 반환(정상 처리 확인용). 실패 시 None."""
    try:
        return str(session.findById("wnd[0]/sbar").text).strip()
    except Exception:
        return None


def create_purchase_order(session, gongsa_no, length, safety_cost,
                          start_date, end_date, skip_tsrm=True):
    """ZREC0208 로 공사발주서를 작성(+TSRM 발송)한다.

    인자:
        gongsa_no   : 공사번호 (예: "2026A0062")
        length      : 배관연장(m) → 공사개요에 사용 (예: 5)
        safety_cost : 산업안전보건관리비 문자열(콤마 포함, 예: "113,000")
                      → ZMEC0210 에서 읽은 값을 그대로 넘긴다.
        start_date  : 공사기간 시작 ("YYYY-MM-DD" 등)
        end_date    : 공사기간 종료
        skip_tsrm   : True 면 TSRM 발송(btn38) 생략(테스트/건너뜀). False 면 실제 발송.
    반환:
        처리 후 상태바 메시지(str) 또는 None.
    """
    # 1) 진입 → 발주구분20 + 공사번호 → 조회
    connector.go_tcode(session, "ZREC0208")
    session.findById(SEL_GYGUB).text = GYGUB
    session.findById(SEL_GSCD).text = gongsa_no
    session.findById(BTN_QUERY).press()

    # 2) 조회된 공사 행 선택
    grid = session.findById(GRID)
    grid.currentCellColumn = ""
    grid.selectedRows = "0"

    # 3) 발주서 작성 → 작성 화면 (경고 팝업 뜨면 닫기)
    session.findById(BTN_MAKE).press()
    _dismiss_info_popup(session)

    # 4) 작성 화면 입력
    session.findById(FLD_SGSYMD).text = _fmt_date(start_date)
    session.findById(FLD_EGSYMD).text = _fmt_date(end_date)
    session.findById(FLD_GEYO).text = _work_summary(length)
    session.findById(FLD_SPCTH % 1).text = SPCTH_WASTE
    session.findById(FLD_SPCTH % 2).text = "산업안전보건관리비 : %s원(VAT 별도)" % safety_cost
    session.findById(FLD_SPCTH % 3).text = SPCTH_SHE
    session.findById(FLD_SPCTH % 4).text = SPCTH_SUBMIT
    session.findById(FLD_SPCTH % 5).text = SPCTH_REJECT

    # 5) 저장 → 예
    session.findById(BTN_SAVE).press()
    try:
        session.findById(POP_YES).press()
    except Exception:
        pass

    # 6) TSRM 발송 → 예 (건너뛰지 않을 때만)
    if not skip_tsrm:
        session.findById(BTN_TSRM).press()
        try:
            session.findById(POP_YES).press()
        except Exception:
            pass

    # 7) 정상 처리 여부 확인
    return _read_status(session)

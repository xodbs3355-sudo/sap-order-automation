# -*- coding: utf-8 -*-
"""ZREC2040 — 시행품의 생성.

처리 개요(실제 녹화 기준, 헛클릭 제거):
    1. ZREC2040 진입 → 발주구분(SO_GYGUB)=20 → 공사번호(SO_GSCD) → 조회(tbar[1]/btn[8])
       ※ 공사번호로 걸었으므로 조회되는 공사는 1건.
    2. TAB02: 조회된 공사 1건 선택(체크 → BUTTON2 → 줄 선택)
    3. 작업기간(GS_ZECT2350-WORKY) 입력 (= 공사기간). ★입력 후 앞화면(F3)으로 복귀★
       (상세화면에서 바로 기본정보 탭으로 못 넘어가므로 먼저 뒤로 나가야 함)
    4. TAB01(기본정보):
         - 전자시행품의여부(chkGT_ZECT2340-ECHK) 체크 (케이스마다 다름)
         - 목적(txtGT_ZECT2340-GSPPS) 입력 (= 지번 + " 가스 공급", 구간명에서 자동생성)
    5. 시행품의 생성(tbar[1]/btn[25]) → "예" → 확인
    6. 전자일 때만: 전자결재 상신(tbar[1]/btn[26]) → 웹 팝업(시행품의서) 열림
       ※ 웹 팝업은 별도 브라우저라 SAP 자동화 영역 밖 → 사람이 웹에서 직접 상신.
    7. 종료(뒤로 ×2)

입력값(케이스마다): 공사번호 / 구간명(→목적 자동생성) / 공사기간(시작~종료) / 전자여부.
발주구분 20 고정.

필드 주소는 SAP Script Recording 실측값. Windows + SAP 에서만 실제 동작한다.

주의(테스트 검증 필요):
    - btn[26](전자 상신)이 웹 팝업을 띄운 뒤 SAP 가 대기(차단)하는지 여부는
      실기 테스트로 확인한다. (비차단이면 이후 종료까지 정상 진행)
"""

from sap import connector

# ── 화면 요소 주소 (녹화 실측) ─────────────────────────────
SEL_GYGUB = "wnd[0]/usr/ctxtSO_GYGUB-LOW"      # 발주구분 (20 고정)
SEL_GSCD = "wnd[0]/usr/ctxtSO_GSCD-LOW"        # 공사번호
BTN_QUERY = "wnd[0]/tbar[1]/btn[8]"            # 조회

_TS = "wnd[0]/usr/tabsTS_TABSTRIP/"
TAB01 = _TS + "tabpTAB01"                       # 전자여부/목적 탭
TAB02 = _TS + "tabpTAB02"                       # 공사 선택 탭

# TAB02: 조회된 공사 선택
CHK_WORK = TAB02 + "/ssubTAB_REF:ZREC2040:0120/tblZREC2040TC3/chkGT_LISTALL-CHECK[0,0]"
BTN_TAB02 = TAB02 + "/ssubTAB_REF:ZREC2040:0120/btnBUTTON2"
LBL_SELECT = TAB02 + "/ssubTAB_REF:ZREC2040:0120/tblZREC2040TC2/lblGT_LIST-VEND[1,0]"

# TAB01: 전자여부 / 목적
CHK_ECHK = TAB01 + "/ssubTAB_REF:ZREC2040:0110/chkGT_ZECT2340-ECHK"   # 전자시행품의여부
TXT_GSPPS = TAB01 + "/ssubTAB_REF:ZREC2040:0110/txtGT_ZECT2340-GSPPS"  # 목적

TXT_WORKY = "wnd[0]/usr/txtGS_ZECT2350-WORKY"  # 작업기간(=공사기간)

BTN_CREATE = "wnd[0]/tbar[1]/btn[25]"          # 시행품의 생성
BTN_ESUBMIT = "wnd[0]/tbar[1]/btn[26]"         # 전자결재 상신(웹 팝업)
BTN_BACK = "wnd[0]/tbar[0]/btn[3]"             # 뒤로
POP_YES = "wnd[1]/usr/btnSPOP-OPTION1"         # "예"
POP_OK = "wnd[1]/tbar[0]/btn[0]"               # 확인

GYGUB = "20"        # 발주구분 고정
_PIPE_MARK = "인입"  # 구간명에서 이 글자 앞까지가 지번(인입공급관/인입본관 등 제거)


def make_purpose(gu_name):
    """구간명에서 목적 텍스트를 만든다.

    구간명에서 '인입…'(인입공급관/인입본관 등) 앞까지를 지번으로 잘라내고,
    ' 가스 공급' 을 붙인다.
      "춘천시 후평동 74-19번지 인입공급관" → "춘천시 후평동 74-19번지 가스 공급"
    """
    name = str(gu_name)
    i = name.find(_PIPE_MARK)
    addr = (name[:i] if i >= 0 else name).strip()
    return addr + " 가스 공급"


def fmt_period(start, end):
    """공사기간(시작, 종료)을 "YYYY.MM.DD. ~ YYYY.MM.DD." 형식으로 조립.

    입력은 "YYYY-MM-DD" / "YYYY.MM.DD" / "YYYY/MM/DD" 아무 구분자나 허용.
    """
    def one(x):
        s = str(x).strip().replace("-", ".").replace("/", ".").rstrip(".")
        return s + "."
    return "%s ~ %s" % (one(start), one(end))


def _read_status(session):
    """하단 상태바 메시지를 읽어 반환. 실패 시 None."""
    try:
        return str(session.findById("wnd[0]/sbar").text).strip()
    except Exception:
        return None


def create_approval(session, gongsa_no, gu_name, start_date, end_date, echk=False):
    """ZREC2040 으로 시행품의를 생성한다.

    인자:
        gongsa_no  : 공사번호 (예: "2026A0045")
        gu_name    : 구간명 (목적 자동생성용, 예: "춘천시 후평동 74-19번지 인입공급관")
        start_date : 공사기간 시작 ("YYYY-MM-DD" 등)
        end_date   : 공사기간 종료
        echk       : 전자시행품의 여부(True 면 전자 → SAP 가 상신 웹 팝업을 띄운다)
    반환:
        처리 후 상태바 메시지(str) 또는 None.
    """
    purpose = make_purpose(gu_name)
    period = fmt_period(start_date, end_date)

    # 1) 진입 → 발주구분20 → 공사번호 → 조회
    connector.go_tcode(session, "ZREC2040")
    session.findById(SEL_GYGUB).text = GYGUB
    session.findById(SEL_GSCD).text = gongsa_no
    session.findById(BTN_QUERY).press()

    # 2) 조회된 공사 1건 선택 (체크 → 버튼 → 줄 선택)
    try:
        session.findById(TAB02).select()
    except Exception:
        pass
    session.findById(CHK_WORK).selected = True
    session.findById(BTN_TAB02).press()
    try:
        session.findById(LBL_SELECT).setFocus()
        session.findById("wnd[0]").sendVKey(2)   # 선택
    except Exception:
        pass

    # 3) 작업기간(=공사기간) 입력  (공사 선택 시 열린 상세화면에서 입력)
    session.findById(TXT_WORKY).text = period

    # 3-1) 상세화면 → 앞화면(F3)으로 복귀.
    #      공사기간 입력 후에는 곧바로 기본정보 탭으로 못 넘어가고, 먼저 뒤로 나가야
    #      기본정보 탭이 있는 화면으로 돌아간다. (이 F3 누락이 'control not found' 원인)
    session.findById(BTN_BACK).press()

    # 4) TAB01(기본정보): 전자여부 + 목적
    session.findById(TAB01).select()
    try:
        session.findById(CHK_ECHK).selected = bool(echk)
    except Exception:
        pass
    session.findById(TXT_GSPPS).text = purpose

    # 5) 시행품의 생성 → 예 → 확인
    session.findById(BTN_CREATE).press()
    try:
        session.findById(POP_YES).press()
    except Exception:
        pass
    try:
        session.findById(POP_OK).press()
    except Exception:
        pass

    # 6) 전자일 때만: 전자결재 상신(웹 팝업)
    if echk:
        try:
            session.findById(BTN_ESUBMIT).press()
        except Exception:
            pass

    sbar = _read_status(session)

    # 7) 종료(뒤로 ×2)
    for _ in range(2):
        try:
            session.findById(BTN_BACK).press()
        except Exception:
            pass

    return sbar

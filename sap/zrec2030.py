# -*- coding: utf-8 -*-
"""ZREC2030 — 발주구간 생성 (협력사 지정).

처리 개요(실제 녹화 기준, 헛클릭 제거):
    1. ZREC2030 진입 → 발주구분(SO_GYGUB-LOW)=20 입력 → 공사번호(SO_GSCD-LOW) 입력
       → 조회(tbar[1]/btn[8])
       ※ 공사번호로 걸었으므로 조회되는 공사는 1건.
    2. TAB02: 조회된 공사 1건 체크(chkIT_LISTALL-CHECK) → 버튼(BUTTON2)
    3. TAB01: 업체 칸(IT_BAL-DIGVD)에 협력사 업체코드 입력(그 공사에 지정된 업체)
    4. 실행(tbar[1]/btn[13]) → "예"(OPTION1) → 확인(btn[0])
    5. 종료(tbar[0]/btn[15])

입력값(케이스마다): 공사번호 / 업체코드(그 공사에 지정된 협력사).
발주구분 20(연간단가계약=인입공급관)은 고정.

업체 선택 방식(테스트 검증 필요):
    녹화는 F4 값도움에서 '위치(줄 번호)'로 골라 불안정했다. 여기서는 업체 칸에
    업체코드를 '직접 입력'한다(코드는 유일하므로 안정적). 만약 직접 입력이 안 되면
    (값이 안 붙으면) F4 코드검색 방식으로 전환한다.

필드 주소는 SAP Script Recording 실측값. Windows + SAP 에서만 실제 동작한다.
"""

from sap import connector

# ── 화면 요소 주소 (녹화 실측) ─────────────────────────────
SEL_GYGUB = "wnd[0]/usr/ctxtSO_GYGUB-LOW"      # 발주구분 (20 고정)
SEL_GSCD = "wnd[0]/usr/ctxtSO_GSCD-LOW"        # 공사번호
BTN_QUERY = "wnd[0]/tbar[1]/btn[8]"            # 조회(실행)

_TS = "wnd[0]/usr/tabsTS_TABSTRIP/"
TAB01 = _TS + "tabpTAB01"                       # 업체 지정 탭
TAB02 = _TS + "tabpTAB02"                       # 공사 목록 탭

# TAB02: 조회된 공사 체크박스 + 버튼
CHK_SELECT = TAB02 + "/ssubTAB_REF:ZREC2030:0120/tblZREC2030TC2/chkIT_LISTALL-CHECK[0,0]"
BTN_TAB02 = TAB02 + "/ssubTAB_REF:ZREC2030:0120/btnBUTTON2"

# TAB01: 업체(협력사) 입력 칸
FLD_VENDOR = TAB01 + "/ssubTAB_REF:ZREC2030:0110/ctxtIT_BAL-DIGVD"

BTN_EXEC = "wnd[0]/tbar[1]/btn[13]"            # 실행(생성)
BTN_EXIT = "wnd[0]/tbar[0]/btn[15]"            # 종료
POP_YES = "wnd[1]/usr/btnSPOP-OPTION1"         # "예"
POP_OK = "wnd[1]/tbar[0]/btn[0]"               # 확인

GYGUB = "20"     # 발주구분 고정 (연간단가계약 = 인입공급관)


def _read_status(session):
    """하단 상태바 메시지를 읽어 반환(성공/결과 확인용). 실패 시 None."""
    try:
        return str(session.findById("wnd[0]/sbar").text).strip()
    except Exception:
        return None


def create_order_section(session, gongsa_no, vendor_code):
    """ZREC2030 으로 발주구간을 생성(공사에 협력사 지정)한다.

    인자:
        gongsa_no   : 공사번호 (예: "2026A0045")
        vendor_code : 협력사 업체코드 (예: "2218126440") — 그 공사에 지정된 업체
    반환:
        처리 후 상태바 메시지(str) 또는 None.
    """
    # 1) 진입 → 발주구분 20 → 공사번호 → 조회
    connector.go_tcode(session, "ZREC2030")
    session.findById(SEL_GYGUB).text = GYGUB
    session.findById(SEL_GSCD).text = gongsa_no
    session.findById(BTN_QUERY).press()          # 조회

    # 2) TAB02: 조회된 공사 1건 체크 → 버튼
    try:
        session.findById(TAB02).select()
    except Exception:
        pass
    session.findById(CHK_SELECT).selected = True
    session.findById(BTN_TAB02).press()

    # 3) TAB01: 업체 칸에 업체코드 직접 입력
    session.findById(TAB01).select()
    fld = session.findById(FLD_VENDOR)
    fld.text = vendor_code
    fld.setFocus()

    # 4) 실행 → 예 → 확인
    session.findById(BTN_EXEC).press()
    try:
        session.findById(POP_YES).press()   # "예"
    except Exception:
        pass
    try:
        session.findById(POP_OK).press()    # 확인
    except Exception:
        pass

    msg = _read_status(session)             # 결과 메시지(있으면)

    # 5) 종료
    try:
        session.findById(BTN_EXIT).press()
    except Exception:
        pass

    return msg

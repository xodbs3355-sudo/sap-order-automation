# -*- coding: utf-8 -*-
"""ZREC0100 — 공사번호 생성.

처리 개요(실제 녹화 기준):
    1. ZREC0100 진입 → 선택화면에 CMP 입력(SO_ZSEC-LOW) → F8(조회)
    2. 좌측 구간코드(CMP) 트리에서 해당 노드 선택 → "1:1 =>"(btnCB_DCLK)
    3. 팝업 입력:
       - 공사구분(GSCD1)=A, 발주구분(GYGUB)=20   (고정)
       - 구/군(GU), 동(DONG): F4 → 찾기 → 코드 검색 → 선택
       - 굴착허가(HGYN): 1=대상 / 2=비대상
       - 허가청(GUCD1): 코드 직접 입력
       - 팝업 확인(btn[8])
    4. 저장(btn[11]) → "예"(OPTION1) → "아니오"(OPTION2)
    5. 우측 "공사번호" 트리에서 생성된 공사번호(YYYY+영문+숫자) 읽기

필드 주소는 SAP Script Recording 실측값. Windows + SAP 에서만 실제 동작한다.

주의(테스트 검증 필요):
    구/군·동의 F4 "찾기 → 코드검색 → 선택" 은 값도움 창 구조에 따라
    선택 방식이 달라질 수 있어, 첫 테스트에서 동작을 보고 다듬는다.
"""

import re

from sap import connector

# ── 화면 요소 주소 (녹화 실측) ─────────────────────────────
SEL_CMP_FIELD = "wnd[0]/usr/ctxtSO_ZSEC-LOW"                       # 선택화면 CMP 입력
CMP_TREE = "wnd[0]/shellcont[0]/shell/shellcont[1]/shell[1]"        # 좌측 CMP 트리
BTN_1TO1 = "wnd[0]/usr/btnCB_DCLK"                                  # "1:1 =>" 버튼
GONGSA_TREE = "wnd[0]/shellcont[1]/shell/shellcont[1]/shell[1]"     # 우측 공사번호 트리

# 팝업(wnd[1]) 입력 필드
POP_GSCD1 = "wnd[1]/usr/cmbZECT0101-GSCD1"   # 공사구분 (A 고정)
POP_GYGUB = "wnd[1]/usr/cmbZECT0101-GYGUB"   # 발주구분 (20 고정)
POP_GU = "wnd[1]/usr/ctxtZECT0101-GU"        # 구/군 (F4 코드검색)
POP_DONG = "wnd[1]/usr/ctxtZECT0101-DONG"    # 동읍면리 (F4 코드검색)
POP_HGYN = "wnd[1]/usr/cmbZECT0101-HGYN"     # 굴착허가 (1 대상 / 2 비대상)
POP_GUCD1 = "wnd[1]/usr/ctxtZECT0101-GUCD1"  # 허가청 (코드 직접입력)
POP_CONFIRM = "wnd[1]/tbar[0]/btn[8]"         # 팝업 확인

BTN_SAVE = "wnd[0]/tbar[0]/btn[11]"           # 저장 (Ctrl+S)
POP_YES = "wnd[1]/usr/btnSPOP-OPTION1"        # "예"
POP_NO = "wnd[1]/usr/btnSPOP-OPTION2"         # "아니오"

_GONGSA_PAT = re.compile(r"^\d{4}[A-Z]\d+$")   # 공사번호 형식 예: 2026A0043


def _focus_code_row(session, wnd, code):
    """값도움/검색결과 창(wnd)에서 코드가 적힌 줄에 커서를 올린다.

    SAP 는 "어느 줄을 고를지" 커서 위치를 알아야 선택을 허용한다.
    (안 그러면 'Place the cursor on a line in the hitlist' 오류)
    화면의 라벨들을 훑어 코드 텍스트와 일치하는 줄을 찾아 setFocus 한다.
    찾으면 True, 못 찾으면 False.
    """
    code = str(code).strip()
    try:
        usr = session.findById(wnd + "/usr")
        children = usr.Children
    except Exception:
        return False
    for i in range(children.Count):
        child = children.ElementAt(i)
        try:
            text = str(child.Text).strip()
        except Exception:
            continue
        # 코드가 그대로거나(=일치), 셀 안에 코드가 포함된 경우 모두 인정
        if text == code or (code and code in text):
            try:
                child.setFocus()
                return True
            except Exception:
                continue
    return False


def _f4_search_select(session, field_id, code):
    """필드에 F4 → 찾기(btn[71]) → 코드 검색 → 결과 선택.

    항목이 많아 한 화면에 다 안 보일 수 있는 필드(예: 동/읍/면/리)에 쓴다.
    찾기로 한 건만 남긴 뒤, 그 줄에 커서를 올려 선택한다.
    """
    fld = session.findById(field_id)
    fld.setFocus()
    fld.caretPosition = 0
    session.findById("wnd[1]").sendVKey(4)                 # F4 → 값도움 wnd[2]
    session.findById("wnd[2]/tbar[0]/btn[71]").press()     # 찾기 → wnd[3]
    session.findById("wnd[3]/usr/txtRSYSF-STRING").text = code
    session.findById("wnd[3]/tbar[0]/btn[0]").press()      # 검색 실행 → 결과 wnd[4]
    # 결과 줄에 커서를 올린 뒤 선택(더블클릭=Enter). 못 찾으면 첫 줄 선택 시도.
    _focus_code_row(session, "wnd[4]", code)
    session.findById("wnd[4]").sendVKey(2)                 # 선택 → 값도움(wnd[2])으로
    # 값도움 창에서도 같은 코드 줄에 커서를 올린 뒤 확정.
    _focus_code_row(session, "wnd[2]", code)
    session.findById("wnd[2]").sendVKey(2)                 # 값도움에서 확정


def _f4_pick_direct(session, field_id, code):
    """필드에 F4 → 값도움 팝업에서 코드 줄을 바로 선택.

    항목이 적어 한 화면에 다 보이는 필드(예: 구/군 18개)에 쓴다.
    "찾기(검색)" 단계 없이 팝업(wnd[2])에서 코드 줄을 찾아 바로 확정한다.

    만약 팝업에서 코드 줄이 화면 밖이라 못 찾으면(스크롤 필요) →
    안전하게 기존 "찾기 검색" 방식(_f4_search_select)으로 넘어간다.
    """
    fld = session.findById(field_id)
    fld.setFocus()
    fld.caretPosition = 0
    session.findById("wnd[1]").sendVKey(4)                 # F4 → 값도움 wnd[2]
    if _focus_code_row(session, "wnd[2]", code):
        session.findById("wnd[2]").sendVKey(2)            # 코드 줄 바로 확정
        return
    # 화면에 안 보이면 찾기 버튼으로 검색해서 선택(폴백)
    session.findById("wnd[2]/tbar[0]/btn[71]").press()     # 찾기 → wnd[3]
    session.findById("wnd[3]/usr/txtRSYSF-STRING").text = code
    session.findById("wnd[3]/tbar[0]/btn[0]").press()      # 검색 실행 → 결과 wnd[4]
    _focus_code_row(session, "wnd[4]", code)
    session.findById("wnd[4]").sendVKey(2)
    _focus_code_row(session, "wnd[2]", code)
    session.findById("wnd[2]").sendVKey(2)


def _read_gongsa_no(session):
    """우측 공사번호 트리에서 공사번호(YYYY+영문+숫자)를 읽어 반환.

    컬럼명을 몰라도 되도록, 모든 노드·컬럼을 훑어 형식에 맞는 값을 찾는다.
    실패 시 None.
    """
    tree = session.findById(GONGSA_TREE)
    try:
        col_names = list(tree.GetColumnNames())
        node_keys = list(tree.GetAllNodeKeys())
    except Exception:
        return None
    for nk in node_keys:
        for cn in col_names:
            try:
                val = str(tree.GetItemText(nk, cn)).strip()
            except Exception:
                continue
            if _GONGSA_PAT.match(val):
                return val
    return None


def create_work_order(session, cmp_no, sigun_code, dong_code, permit_code, dig_permit):
    """ZREC0100 으로 공사번호를 생성하고 그 번호를 반환한다.

    인자:
        cmp_no      : 구간코드 (예: "JM20260006")
        sigun_code  : 시/군 코드 (예: "51110")
        dong_code   : 동읍면리 코드 (예: "31022")  ※ 시/군 먼저 → 동 순서로 입력
        permit_code : 허가청 코드 (예: "2218300385")
        dig_permit  : 굴착허가 "1"(대상) / "2"(비대상)
    반환:
        생성된 공사번호(str, 예 "2026A0043") 또는 None(읽기 실패)
    """
    # 1) ZREC0100 진입 + CMP 로 조회
    connector.go_tcode(session, "ZREC0100")
    session.findById(SEL_CMP_FIELD).text = cmp_no
    session.findById("wnd[0]").sendVKey(8)   # F8

    # 2) 좌측 CMP 트리에서 첫 노드 선택 (CMP 로 필터했으니 대상 건)
    cmp_tree = session.findById(CMP_TREE)
    node_keys = list(cmp_tree.GetAllNodeKeys())
    if not node_keys:
        raise RuntimeError("조회된 CMP 가 없습니다: %s" % cmp_no)
    cmp_tree.selectNode(node_keys[0])

    # 3) 1:1 => 버튼 → 팝업
    session.findById(BTN_1TO1).press()

    # 4) 팝업 입력 (순서 중요: 시/군 먼저 → 동)
    session.findById(POP_GSCD1).key = "A"     # 공사구분
    session.findById(POP_GYGUB).key = "20"    # 발주구분
    _f4_pick_direct(session, POP_GU, sigun_code)       # 구/군 (18개, 팝업서 바로 선택)
    _f4_search_select(session, POP_DONG, dong_code)    # 동읍면리 (많음 → 찾기 검색)
    session.findById(POP_HGYN).key = dig_permit         # 굴착허가 1/2
    session.findById(POP_GUCD1).text = permit_code      # 허가청 코드 직접
    session.findById(POP_CONFIRM).press()               # 팝업 확인

    # 5) 저장 → 예 → 아니오
    session.findById(BTN_SAVE).press()
    try:
        session.findById(POP_YES).press()   # "마스터 정보 생성. 저장?" → 예
    except Exception:
        pass
    try:
        session.findById(POP_NO).press()    # "정보조회 이동?" → 아니오
    except Exception:
        pass

    # 6) 우측 트리에서 공사번호 읽기
    return _read_gongsa_no(session)

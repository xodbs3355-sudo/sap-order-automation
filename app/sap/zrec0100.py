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
import time

from sap import connector

try:
    import applog  # 진단 로그(파일+화면). 없어도 동작하도록 감싼다.
except Exception:  # pragma: no cover
    applog = None

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

_GONGSA_PAT = re.compile(r"^\d{4}[A-Z]\d{4}$")   # 공사번호 형식: 숫자4+영문1+숫자4 (예: 2026A0063)


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


def _log(msg, level="info"):
    """진단 로그(applog 있으면 파일+화면, 없으면 무시)."""
    if applog:
        try:
            applog.log(msg, level)
        except Exception:
            pass


def _walk(node):
    """컨트롤 트리를 재귀적으로 순회하며 모든 하위 컨트롤을 내놓는다.

    화면 구성(주소)이 조금 달라도 트리/그리드를 놓치지 않기 위해, 특정 주소에
    의존하지 않고 창(wnd[0]) 아래를 통째로 훑는다.
    """
    yield node
    try:
        children = node.Children
        count = children.Count
    except Exception:
        return
    for i in range(count):
        ch = None
        try:
            ch = children.ElementAt(i)
        except Exception:
            try:
                ch = children(i)
            except Exception:
                ch = None
        if ch is not None:
            for sub in _walk(ch):
                yield sub


def _ctype(ctrl):
    try:
        return str(ctrl.Type)
    except Exception:
        return ""


def _scan_tree(tree):
    """트리(컬럼형)의 모든 노드×열을 훑어 공사번호 형식 값을 찾는다. 없으면 None."""
    try:
        col_names = list(tree.GetColumnNames())
    except Exception:
        col_names = []
    try:
        node_keys = list(tree.GetAllNodeKeys())
    except Exception:
        node_keys = []
    for nk in node_keys:
        for cn in col_names:
            try:
                val = str(tree.GetItemText(nk, cn)).strip()
            except Exception:
                continue
            if _GONGSA_PAT.match(val):
                return val
    return None


def _scan_grid(grid):
    """그리드(ALV)의 모든 행×열을 훑어 공사번호 형식 값을 찾는다. 없으면 None."""
    try:
        col_ids = list(grid.ColumnOrder)
        rows = grid.RowCount
    except Exception:
        return None
    for r in range(rows):
        for cid in col_ids:
            try:
                val = str(grid.GetCellValue(r, cid)).strip()
            except Exception:
                continue
            if _GONGSA_PAT.match(val):
                return val
    return None


def _is_candidate(ctrl):
    """트리/그리드일 가능성이 있는 컨트롤인가?

    SAP 의 트리·그리드는 대부분 Type 이 'GuiShell' 이다(하위 SubType 이 Tree/GridView).
    그래서 'Tree'/'Grid' 라는 타입명만 보면 놓친다 → GuiShell 도 후보에 포함한다.
    """
    t = _ctype(ctrl)
    return t == "GuiShell" or "Tree" in t or "Grid" in t


def _collect_candidates(session):
    """창(wnd[0]) 아래의 트리/그리드 후보(GuiShell 등)를 한 번의 순회로 모은다."""
    cands = []
    try:
        root = session.findById("wnd[0]")
    except Exception:
        return cands
    for ctrl in _walk(root):
        if _is_candidate(ctrl):
            cands.append(ctrl)
    return cands


def _scan_candidates(cands):
    """후보 컨트롤들에서 공사번호 형식 값을 찾는다(트리·그리드 양쪽 시도)."""
    for c in cands:
        v = _scan_tree(c)
        if v:
            return v
        v = _scan_grid(c)
        if v:
            return v
    return None


def _dump_screen(session):
    """진단용: 화면 상태를 상세히 로그로 남긴다(어느 화면·어떤 컨트롤인지 확정용)."""
    _log("── 공사번호 못 찾음 · 화면 진단 덤프 ──", "warn")
    # 어느 화면인지
    try:
        info = session.Info
        _log("  트랜잭션=%s · 프로그램=%s · 화면=%s"
             % (info.Transaction, info.Program, info.ScreenNumber), "info")
    except Exception:
        pass
    try:
        _log("  창 제목: %s" % str(session.findById("wnd[0]").Text).strip(), "info")
    except Exception:
        pass
    # 팝업이 떠 있으면(=화면을 벗어났을 수 있음) 알린다
    ptext = _popup_text(session)
    if ptext:
        _log("  ⚠ 팝업(wnd[1]) 열려 있음: %s" % ptext[:120], "warn")
    else:
        _log("  팝업 없음", "info")
    try:
        _log("  상태바: %s" % str(session.findById("wnd[0]/sbar").text).strip(), "info")
    except Exception:
        pass
    # 화면의 모든 GuiShell/트리/그리드 나열 + 내용 일부
    try:
        root = session.findById("wnd[0]")
    except Exception:
        _log("  wnd[0] 접근 실패", "error")
        return
    found = 0
    for ctrl in _walk(root):
        if not _is_candidate(ctrl):
            continue
        found += 1
        t = _ctype(ctrl)
        try:
            cid = str(ctrl.Id)
        except Exception:
            cid = "?"
        sub = ""
        try:
            sub = str(ctrl.SubType)
        except Exception:
            pass
        _log("  [%s%s] %s" % (t, ("/" + sub) if sub else "", cid), "info")
        # 트리로 시도
        try:
            cols = list(ctrl.GetColumnNames())
            keys = list(ctrl.GetAllNodeKeys())
            _log("     (트리) 열=%s · 행수=%d" % (cols, len(keys)), "info")
            for nk in keys[:6]:
                vals = []
                for cn in cols:
                    try:
                        vals.append("%s=%s" % (cn, str(ctrl.GetItemText(nk, cn)).strip()))
                    except Exception:
                        pass
                _log("      · %s" % " | ".join(vals), "info")
            continue
        except Exception:
            pass
        # 그리드로 시도
        try:
            cols = list(ctrl.ColumnOrder)
            rows = ctrl.RowCount
            _log("     (그리드) 열=%s · 행수=%d" % (cols, rows), "info")
            for r in range(min(rows, 6)):
                vals = []
                for cid2 in cols:
                    try:
                        vals.append("%s=%s" % (cid2, str(ctrl.GetCellValue(r, cid2)).strip()))
                    except Exception:
                        pass
                _log("      · %s" % " | ".join(vals), "info")
        except Exception:
            pass
    if not found:
        _log("  GuiShell/트리/그리드 후보를 하나도 못 찾음 → 예상과 다른 화면일 수 있음", "warn")


def _read_gongsa_no(session, retries=6, wait=0.5):
    """생성된 공사번호(숫자4+영문1+숫자4)를 읽어 반환. 실패 시 None.

    - SAP 트리/그리드는 Type 이 'GuiShell' 이라, 화면의 GuiShell 후보를 모아
      트리·그리드 양쪽으로 값을 읽는다(주소·타입 하드코딩 의존 제거).
    - 저장 직후 늦게 그려질 수 있어 잠깐 기다렸다 재시도(순회 비용을 줄이려
      후보는 한 번 모으고, 중간에 한 번만 다시 모은다).
    - 끝내 못 찾으면 화면을 상세 진단 덤프.
    """
    # 빠른 경로: 알려진 주소 먼저
    try:
        c = session.findById(GONGSA_TREE)
        v = _scan_tree(c) or _scan_grid(c)
        if v:
            return v
    except Exception:
        pass

    cands = _collect_candidates(session)
    for attempt in range(retries):
        v = _scan_candidates(cands)
        if v:
            if attempt:
                _log("공사번호 읽음(재시도 %d회 후): %s" % (attempt, v), "info")
            return v
        time.sleep(wait)
        if attempt == 2:   # 트리가 늦게 생겼을 수 있어 한 번 더 모은다
            cands = _collect_candidates(session)
    _dump_screen(session)
    return None


def _popup_text(session):
    """wnd[1](팝업)의 제목+본문 텍스트를 모아 반환. 팝업 없으면 ''."""
    try:
        top = session.findById("wnd[1]")
    except Exception:
        return ""
    parts = []
    try:
        parts.append(str(top.Text))
    except Exception:
        pass
    for c in _walk(top):
        try:
            t = str(c.Text).strip()
            if t:
                parts.append(t)
        except Exception:
            pass
    return " ".join(parts)


def _handle_save_popups(session, max_popups=5):
    """저장 후 뜨는 팝업을 텍스트에 따라 안전하게 처리한다.

    - '정보조회/이동' 팝업(정보조회로 이동하시겠습니까?) → 아니오(OPTION2): 화면 유지
    - 그 외(저장하시겠습니까? 등)                        → 예(OPTION1)
    이렇게 하면 팝업 개수·순서가 달라도 실수로 '예 → 화면 이동'이 되지 않는다.
    """
    for _ in range(max_popups):
        try:
            session.findById("wnd[1]")
        except Exception:
            return   # 더 이상 팝업 없음
        body = _popup_text(session)
        stay = ("이동" in body) or ("정보조회" in body)
        pressed = False
        try:
            btn = "wnd[1]/usr/btnSPOP-OPTION2" if stay else "wnd[1]/usr/btnSPOP-OPTION1"
            session.findById(btn).press()
            pressed = True
            _log("팝업 처리: '%s' → %s" % (body[:40], "아니오" if stay else "예"), "info")
        except Exception:
            pass
        if not pressed:
            # 표준 SPOP 버튼이 아니면 Enter(확인)로 닫기
            try:
                session.findById("wnd[1]").sendVKey(0)
            except Exception:
                return


def _requery(session, cmp_no):
    """저장 직후 '공사번호 생성' 화면엔 새 번호가 표시되지 않으므로,
    구간코드로 다시 조회(F8)해 우측 공사번호 트리에 번호가 뜨게 한다.

    현재 화면에서 조회 필드에 바로 넣어 F8. 안 되면 T-code 재진입 후 조회.
    조회 후 좌측 CMP 노드를 선택해 우측 공사번호/매핑이 표시되도록 한다
    (1:1 버튼은 누르지 않음 — 재생성 방지).
    """
    def _do():
        session.findById(SEL_CMP_FIELD).text = cmp_no
        session.findById("wnd[0]").sendVKey(8)   # F8 조회
        try:
            tree = session.findById(CMP_TREE)
            keys = list(tree.GetAllNodeKeys())
            if keys:
                tree.selectNode(keys[0])
        except Exception:
            pass

    try:
        _do()
        return
    except Exception:
        pass
    try:
        connector.go_tcode(session, "ZREC0100")
        _do()
    except Exception:
        pass


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

    # 5) 저장 → 팝업 텍스트에 따라 안전 처리
    #    (정보조회 이동?→아니오 로 화면 유지, 저장?→예. 팝업 순서/개수 달라도 안전)
    session.findById(BTN_SAVE).press()
    _handle_save_popups(session)

    # 6) 재조회 → 공사번호 읽기
    #    저장 직후 '공사번호 생성' 화면엔 새 번호가 표시되지 않는다(진단 확인).
    #    구간코드로 다시 조회(F8)해 우측 공사번호 트리에 번호를 띄운 뒤 읽는다.
    _requery(session, cmp_no)
    return _read_gongsa_no(session)

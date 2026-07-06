# -*- coding: utf-8 -*-
"""ZREC0002 — 공사의뢰 접수/반려.

처리 개요(설계 문서 + 실제 녹화 기준):
    1. ZREC0002 진입 → F8(조회)  (회사코드 J000 고정·비활성, "의뢰" 라디오 기본 선택)
    2. 의뢰 공사 목록 그리드를 읽어 화면 표로 전달 (= 리스트 불러오기)
    3. 처리할 행 선택 → 접수 버튼(tbar[1]/btn[35], Ctrl+F11)
    4. "접수처리를 하시겠습니까?" 팝업 → "예"(wnd[1]/usr/btnBUTTON_1)

필드 주소는 SAP Script Recording 으로 확보한 실측값이다.
win32com/SAP 환경(Windows)에서만 실제 동작한다.
"""

from sap import connector

# 조회 결과 목록 그리드 (녹화 실측 주소)
GRID_ID = "wnd[0]/usr/cntlGRID1/shellcont/shell/shellcont[1]/shell"

# 접수 버튼 / 확인 팝업 "예" (녹화 실측 주소)
RECEIVE_BTN_ID = "wnd[0]/tbar[1]/btn[35]"      # 접수 (Ctrl+F11)
CONFIRM_YES_ID = "wnd[1]/usr/btnBUTTON_1"       # "예"


def _open_and_query(session):
    """ZREC0002 로 이동해 F8(조회)까지 실행한다."""
    connector.go_tcode(session, "ZREC0002")
    session.findById("wnd[0]").sendVKey(8)   # F8 = 조회


def fetch_request_list(session):
    """의뢰 공사 목록을 조회해 그리드 내용을 통째로 읽어 반환한다.

    반환(dict):
      {
        "columns": [ {"id": 열ID, "title": 열제목}, ... ],
        "rows":    [ { 열ID: 값, ... }, ... ],
        "row_count": 행수
      }
    - 열 제목(title)을 함께 담아, 첫 실행 때 실제 컬럼명을 확인해 매핑을 확정한다.
    - 주의: 행이 매우 많은 그리드는 화면에 로드된 행만 읽힐 수 있다.
      (대량이면 스크롤 읽기 보강 필요 — TODO)
    """
    _open_and_query(session)
    grid = session.findById(GRID_ID)

    # 열 목록 + 제목
    col_ids = list(grid.ColumnOrder)
    columns = []
    for cid in col_ids:
        try:
            title = grid.GetDisplayedColumnTitle(cid)
        except Exception:
            title = cid
        columns.append({"id": cid, "title": title})

    # 행 전체 읽기
    row_count = grid.RowCount
    rows = []
    for r in range(row_count):
        row = {}
        for cid in col_ids:
            try:
                row[cid] = grid.GetCellValue(r, cid)
            except Exception:
                row[cid] = ""
        rows.append(row)

    return {"columns": columns, "rows": rows, "row_count": row_count}


def receive_request(session, row_index):
    """지정한 행(row_index)을 선택해 접수 처리한다.

    설계서/녹화 기준: 행 선택 → 접수(btn[35]) → "예"(btnBUTTON_1).
    성공/실패 판단은 상위(자동화 흐름)에서 하단 메시지로 확인한다.
    """
    grid = session.findById(GRID_ID)
    grid.currentCellColumn = ""
    grid.selectedRows = str(row_index)

    session.findById(RECEIVE_BTN_ID).press()      # 접수
    # 확인 팝업이 뜨면 "예"
    try:
        session.findById(CONFIRM_YES_ID).press()
    except Exception:
        pass  # 팝업이 없을 수도 있으니 무시

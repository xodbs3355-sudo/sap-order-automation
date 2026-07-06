# -*- coding: utf-8 -*-
"""SAP 세션 연결 관리.

연결 방식(설계 문서 기준):
    사용자가 SAP GUI 에 직접 로그인 → 이미 열려 있는 세션에
    Python(win32com)이 붙는 방식.
    win32com.client.GetObject('SAPGUI') 로 실행 중인 SAP GUI 를 얻고,
    거기서 첫 번째 연결/세션을 가져온다.

이 모듈은 Windows + SAP GUI 환경에서만 실제로 동작한다(win32com 은 Windows 전용).
win32com 은 함수 안에서 import 하므로, 다른 OS 에서도 이 모듈을 불러오는 것 자체는 된다.
"""


class SapConnectionError(Exception):
    """SAP 세션에 붙지 못했을 때 발생(원인 메시지 포함)."""


def get_session():
    """열려 있는 SAP GUI 의 첫 번째 세션 객체를 반환한다.

    실패하면 SapConnectionError 를 원인 메시지와 함께 던진다.
    """
    try:
        import win32com.client
    except ImportError as e:
        raise SapConnectionError(
            "win32com(pywin32) 를 불러오지 못했습니다. (pip install pywin32 필요)"
        ) from e

    # 1) 실행 중인 SAP GUI 잡기
    try:
        sap_gui_auto = win32com.client.GetObject("SAPGUI")
    except Exception as e:
        raise SapConnectionError(
            "실행 중인 SAP GUI 를 찾지 못했습니다. "
            "SAP 로그인 여부 · 같은 세션 · 스크립팅 활성화를 확인하세요."
        ) from e

    # 2) 스크립팅 엔진 접근
    try:
        application = sap_gui_auto.GetScriptingEngine
    except Exception as e:
        raise SapConnectionError(
            "SAP 스크립팅 엔진에 접근하지 못했습니다. "
            "클라이언트 측 'Enable scripting' 설정을 확인하세요."
        ) from e

    # 3) 로그인된 연결 / 세션 확인
    if application.Children.Count == 0:
        raise SapConnectionError(
            "SAP GUI 는 떠 있으나 로그인된 연결이 없습니다. SAP 에 로그인하세요."
        )
    connection = application.Children(0)
    if connection.Children.Count == 0:
        raise SapConnectionError("연결은 있으나 열린 세션이 없습니다.")

    return connection.Children(0)


def check_connection():
    """연결 상태를 점검해 dict 로 반환한다(예외를 던지지 않음).

    성공: {"ok": True, "system", "client", "user", "transaction", "language"}
    실패: {"ok": False, "error": "사유"}
    화면(JS)에서 연결 확인 버튼 등에 쓰기 좋게 dict 형태로 돌려준다.
    """
    try:
        session = get_session()
        info = session.Info
        return {
            "ok": True,
            "system": info.SystemName,
            "client": info.Client,
            "user": info.User,
            "transaction": info.Transaction,
            "language": info.Language,
        }
    except SapConnectionError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # 예상 못한 COM 오류 등
        return {"ok": False, "error": "예상치 못한 오류: %s" % e}


def go_tcode(session, tcode):
    """현재 화면과 무관하게 지정한 T-code 로 이동한다.

    설계서 기준: 명령창(okcd)에 '/n티코드' 입력 후 엔터(sendVKey 0).
    예) go_tcode(session, "ZMEC0210")
    """
    session.findById("wnd[0]/tbar[0]/okcd").text = "/n" + tcode
    session.findById("wnd[0]").sendVKey(0)

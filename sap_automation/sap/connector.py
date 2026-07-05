"""SAP 세션 연결 관리.

연결 방식(설계 문서 기준):
    사용자가 SAP GUI에 직접 로그인 → 이미 열려 있는 세션에
    Python(win32com)이 붙는 방식.

    win32com.client.GetObject('SAPGUI') 로 실행 중인 SAP GUI 객체를 얻고,
    거기서 첫 번째 연결/세션을 가져온다.

주의: 실제 SAP 연결 로직은 이후 단계에서 구현한다. 지금은 뼈대(stub)만 둔다.
"""


def get_session():
    """열려 있는 SAP GUI 세션 객체를 반환한다(예정).

    TODO: win32com.client.GetObject('SAPGUI') 로 세션 연결 구현.
    """
    raise NotImplementedError("SAP 세션 연결 로직은 이후 단계에서 구현합니다.")

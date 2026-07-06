# -*- coding: utf-8 -*-
"""SAP 연결 확인용 스크립트 (검사 전용).

이 파일은 SAP 데이터를 절대 바꾸지 않습니다.
현재 열려 있는 SAP 세션에 Python이 붙을 수 있는지만 점검하고,
어느 서버/클라이언트/사용자/화면인지 알려줍니다.

사용법 (SAP에 로그인해 둔 상태에서, 명령 프롬프트 cmd 에서):
    python test_connection.py

- Python 안(>>>) 으로 들어갈 필요 없이 cmd 에서 바로 실행됩니다.
"""

import sys


def main():
    print("=" * 46)
    print(" SAP 연결 확인 (검사 전용 - 데이터 변경 없음)")
    print("=" * 46)

    # 1) pywin32(win32com) 준비 확인 --------------------------------
    try:
        import win32com.client
    except ImportError:
        print("[X] win32com(pywin32) 를 불러오지 못했습니다.")
        print("    → 이 파일을 실행하는 Python 에 pywin32 가 설치되어 있는지 확인하세요.")
        print("    → 설치: pip install pywin32")
        return 1

    # 2) 실행 중인 SAP GUI 붙잡기 -----------------------------------
    try:
        sap_gui_auto = win32com.client.GetObject("SAPGUI")
    except Exception as e:
        print("[X] 실행 중인 SAP GUI 를 찾지 못했습니다.")
        print("    아래를 확인하세요:")
        print("    - SAP 에 먼저 로그인되어 있나요? (같은 세션/같은 바탕화면)")
        print("    - SAP GUI Scripting 이 켜져 있나요?")
        print("      (SAP GUI 옵션 → Accessibility & Scripting → Scripting → Enable scripting)")
        print("    상세 오류:", e)
        return 1

    # 3) 스크립팅 엔진 / 연결 / 세션 접근 ----------------------------
    try:
        application = sap_gui_auto.GetScriptingEngine
    except Exception as e:
        print("[X] SAP 스크립팅 엔진에 접근하지 못했습니다.")
        print("    → 클라이언트 측 'Enable scripting' 설정을 확인하세요.")
        print("    상세 오류:", e)
        return 1

    conn_count = application.Children.Count
    if conn_count == 0:
        print("[!] SAP GUI 는 떠 있으나 열린 연결(로그인된 서버)이 없습니다.")
        print("    → SAP 에 로그인한 뒤 다시 실행하세요.")
        return 1

    # 첫 번째 연결의 첫 번째 세션 기준으로 정보 표시
    connection = application.Children(0)
    session = connection.Children(0)

    # 4) 연결 성공 + 상세 정보 표시 ---------------------------------
    print("[O] SAP 연결 성공!")
    print("-" * 46)
    try:
        info = session.Info
        print("  시스템(서버) :", info.SystemName)
        print("  클라이언트    :", info.Client)
        print("  사용자        :", info.User)
        print("  현재 T-code   :", info.Transaction)
        print("  세션 언어     :", info.Language)
    except Exception as e:
        print("  (세부 정보를 읽는 중 일부 실패:", e, ")")
    print("  열린 연결 수  :", conn_count)
    print("  이 연결의 세션 수 :", connection.Children.Count)
    print("-" * 46)
    print("COM / 스크립팅 / 세션 모두 정상입니다. 자동화 준비 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

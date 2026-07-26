# -*- coding: utf-8 -*-
"""ZREC2030 발주구간 생성(협력사 지정) — 단독 테스트 스크립트.

⚠️ 이 스크립트는 SAP 에 실제로 발주구간을 "생성"하고 업체를 지정합니다.
    반드시 테스트 서버에서, 앞 단계(ZMEC0210)까지 끝난 공사번호로 실행하세요.

사용법 (SAP 로그인 후, 명령 프롬프트에서):
    1) 아래 '샘플 입력값'을 이번에 처리할 값으로 수정
    2) python test_zrec2030.py
    3) 마지막에 상태 메시지가 출력되면 확인
"""

import sys

# ── 샘플 입력값 (테스트할 때 여기를 수정) ──────────────────
GONGSA_NO = "2026A0045"       # 공사번호 (ZMEC0210 까지 끝난 건)
VENDOR_CODE = "2218126440"    # 협력사 업체코드
#   국도건설(주)   2218126440
#   (주)태광건설   1348144106
#   대림건설(주)   4688803098
# ───────────────────────────────────────────────────────


def main():
    print("=" * 50)
    print(" ZREC2030 발주구간 생성(협력사 지정) 테스트")
    print("=" * 50)
    print(" 공사번호 :", GONGSA_NO)
    print(" 업체코드 :", VENDOR_CODE)
    print("-" * 50)

    try:
        from sap import connector, zrec2030
    except Exception as e:
        print("[X] 모듈 로드 실패:", e)
        return 1

    # SAP 연결
    try:
        session = connector.get_session()
    except connector.SapConnectionError as e:
        print("[X] SAP 연결 실패:", e)
        return 1

    # 실행
    try:
        msg = zrec2030.create_order_section(
            session,
            gongsa_no=GONGSA_NO,
            vendor_code=VENDOR_CODE,
        )
    except Exception as e:
        print("[X] ZREC2030 처리 중 오류:", e)
        print("    (어느 단계에서 멈췄는지 화면을 확인해 알려주세요)")
        return 1

    print("-" * 50)
    print("[O] 처리 완료. 상태 메시지 →", msg if msg else "(메시지 없음)")
    print("    업체가 제대로 지정됐는지 SAP 화면에서 확인해 주세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

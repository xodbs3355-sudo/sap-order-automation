# -*- coding: utf-8 -*-
"""ZREC0100 공사번호 생성 — 단독 테스트 스크립트.

⚠️ 이 스크립트는 SAP 에 실제로 공사번호를 "생성"합니다.
    반드시 테스트 서버에서, 아직 처리 안 된(공사번호 없는) CMP 로 실행하세요.

사용법 (SAP 로그인 후, 명령 프롬프트에서):
    1) 아래 '샘플 입력값'을 이번에 처리할 값으로 수정
       - CMP 는 매번 새(미처리) 구간코드로 바꿔야 함
    2) python test_zrec0100.py
    3) 마지막에 생성된 공사번호가 출력되면 성공
"""

import sys

# ── 샘플 입력값 (테스트할 때 여기를 수정) ──────────────────
CMP_NO = "JM20260006"       # 구간코드 (미처리 건으로!)
SIGUN_CODE = "51110"        # 시/군 코드 (춘천시)
DONG_CODE = "31022"         # 동읍면리 코드 (동면 만천리)
PERMIT_CODE = "2218300385"  # 허가청 코드 (춘천시청)
DIG_PERMIT = "1"            # 굴착허가 1=대상 / 2=비대상
# ───────────────────────────────────────────────────────


def main():
    print("=" * 50)
    print(" ZREC0100 공사번호 생성 테스트")
    print("=" * 50)
    print(" CMP        :", CMP_NO)
    print(" 시/군 코드 :", SIGUN_CODE)
    print(" 동 코드    :", DONG_CODE)
    print(" 허가청 코드:", PERMIT_CODE)
    print(" 굴착허가   :", DIG_PERMIT, "(1=대상/2=비대상)")
    print("-" * 50)

    try:
        from sap import connector, zrec0100
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
        gongsa_no = zrec0100.create_work_order(
            session,
            cmp_no=CMP_NO,
            sigun_code=SIGUN_CODE,
            dong_code=DONG_CODE,
            permit_code=PERMIT_CODE,
            dig_permit=DIG_PERMIT,
        )
    except Exception as e:
        print("[X] ZREC0100 처리 중 오류:", e)
        print("    (어느 단계에서 멈췄는지 화면을 확인해 알려주세요)")
        return 1

    print("-" * 50)
    if gongsa_no:
        print("[O] 공사번호 생성 성공! →", gongsa_no)
    else:
        print("[!] 처리는 됐으나 공사번호를 못 읽었습니다.")
        print("    우측 '공사번호' 트리에서 번호를 직접 확인하고 알려주세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

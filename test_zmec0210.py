# -*- coding: utf-8 -*-
"""ZMEC0210 설계예산서 작성 — 단독 테스트 스크립트.

⚠️ 이 스크립트는 SAP 에 실제로 설계예산서를 "작성/저장"합니다.
    반드시 테스트 서버에서, 아직 예산서가 없는 공사번호로 실행하세요.

사용법 (SAP 로그인 후, 명령 프롬프트에서):
    1) 아래 '샘플 입력값'을 이번에 처리할 값으로 수정
    2) python test_zmec0210.py
    3) 마지막에 산업안전보건관리비 금액이 출력되면 성공
"""

import sys

# ── 샘플 입력값 (테스트할 때 여기를 수정) ──────────────────
GONGSA_NO = "2026A0062"     # 공사번호 (ZREC0100 에서 생성된 번호)
ROAD_MATERIAL = "ASP"       # 도로재질 "ASP" 또는 "CONC"(=ASP 아님, 보도블럭 포함)
LENGTH = 5                  # 연장(m) 1~10
PLP = False                 # 기존관 PLP 여부 (True / False)
# ───────────────────────────────────────────────────────


def main():
    print("=" * 50)
    print(" ZMEC0210 설계예산서 작성 테스트")
    print("=" * 50)
    print(" 공사번호   :", GONGSA_NO)
    print(" 도로재질   :", ROAD_MATERIAL, "(ASP / CONC)")
    print(" 연장(m)    :", LENGTH)
    print(" PLP 여부   :", PLP)
    print(" 점용료 수량:", LENGTH * 30, "(= 연장 × 30일)")
    print("-" * 50)

    try:
        from sap import connector, zmec0210
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
        safety_cost = zmec0210.create_design_budget(
            session,
            gongsa_no=GONGSA_NO,
            road_material=ROAD_MATERIAL,
            length=LENGTH,
            plp=PLP,
        )
    except Exception as e:
        print("[X] ZMEC0210 처리 중 오류:", e)
        print("    (어느 단계에서 멈췄는지 화면을 확인해 알려주세요)")
        return 1

    print("-" * 50)
    if safety_cost:
        print("[O] 설계예산서 작성 완료!")
        print("    산업안전보건관리비 →", safety_cost)
    else:
        print("[!] 처리는 됐으나 산업안전보건관리비를 못 읽었습니다.")
        print("    TAB01 화면에서 금액을 직접 확인하고 알려주세요.")
        print("    (라벨 주소 lbl%#AUTOTEXT108 이 이번 화면과 다를 수 있음)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

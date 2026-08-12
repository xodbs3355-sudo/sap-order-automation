# -*- coding: utf-8 -*-
"""ZREC0208 공사발주서 작성/발송 — 단독 테스트 스크립트.

⚠️ 이 스크립트는 SAP 에 실제로 발주서를 "작성/저장"합니다.
    SKIP_TSRM=False 로 두면 TSRM(전자발주) 실제 발송까지 진행되니 주의!
    반드시 앞 단계(시행품의)까지 끝난 공사번호로 실행하세요.

사용법 (SAP 로그인 후, 명령 프롬프트에서):
    1) 아래 '샘플 입력값'을 이번에 처리할 값으로 수정
    2) python test_zrec0208.py
    3) 마지막 상태 메시지로 정상 처리 여부 확인
"""

import sys

# ── 샘플 입력값 (테스트할 때 여기를 수정) ──────────────────
GONGSA_NO = "2026A0062"       # 공사번호 (시행품의까지 끝난 건)
LENGTH = 5                    # 배관연장(m) → 공사개요 "PE 63A 5M 인입공급관"
SAFETY_COST = "113,000"       # 산업안전보건관리비 (ZMEC0210 에서 읽은 값, 콤마 포함)
START_DATE = "2026-08-01"     # 공사기간 시작
END_DATE = "2026-08-31"       # 공사기간 종료
SKIP_TSRM = True              # True=TSRM 발송 생략(안전) / False=실제 발송
# ───────────────────────────────────────────────────────


def main():
    print("=" * 50)
    print(" ZREC0208 공사발주서 작성/발송 테스트")
    print("=" * 50)
    print(" 공사번호 :", GONGSA_NO)
    print(" 연장(m)  :", LENGTH)
    print(" 산안비   :", SAFETY_COST)
    print(" 공사기간 :", START_DATE, "~", END_DATE)
    print(" TSRM발송 :", "생략" if SKIP_TSRM else "실제 발송")
    print("-" * 50)

    try:
        from sap import connector, zrec0208
    except Exception as e:
        print("[X] 모듈 로드 실패:", e)
        return 1

    # 미리보기(SAP 없이도 확인): 공사개요/특기사항2가 어떻게 만들어지는지
    print(" 공사개요   :", zrec0208._work_summary(LENGTH))
    print(" 특기사항2  :", "산업안전보건관리비 : %s원(VAT 별도)" % SAFETY_COST)
    print("-" * 50)

    # SAP 연결
    try:
        session = connector.get_session()
    except connector.SapConnectionError as e:
        print("[X] SAP 연결 실패:", e)
        return 1

    # 실행
    try:
        msg = zrec0208.create_purchase_order(
            session,
            gongsa_no=GONGSA_NO,
            length=LENGTH,
            safety_cost=SAFETY_COST,
            start_date=START_DATE,
            end_date=END_DATE,
            skip_tsrm=SKIP_TSRM,
        )
    except Exception as e:
        print("[X] ZREC0208 처리 중 오류:", e)
        print("    (어느 단계에서 멈췄는지 화면을 확인해 알려주세요)")
        return 1

    print("-" * 50)
    print("[O] 처리 완료. 상태 메시지 →", msg if msg else "(메시지 없음)")
    print("    SAP 화면에서 발주서가 제대로 작성됐는지 확인해 주세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

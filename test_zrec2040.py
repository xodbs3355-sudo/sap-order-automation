# -*- coding: utf-8 -*-
"""ZREC2040 시행품의 생성 — 단독 테스트 스크립트.

⚠️ 이 스크립트는 SAP 에 실제로 시행품의를 "생성"합니다.
    반드시 테스트 서버에서, 앞 단계(ZREC2030)까지 끝난 공사번호로 실행하세요.
    전자(ECHK=True) 로 실행하면 마지막에 전자결재 웹 페이지가 뜰 수 있습니다.

사용법 (SAP 로그인 후, 명령 프롬프트에서):
    1) 아래 '샘플 입력값'을 이번에 처리할 값으로 수정
    2) python test_zrec2040.py
    3) 마지막 안내 메시지 확인
"""

import sys

# ── 샘플 입력값 (테스트할 때 여기를 수정) ──────────────────
GONGSA_NO = "2026A0045"                       # 공사번호 (ZREC2030 까지 끝난 건)
GU_NAME = "춘천시 후평동 74-19번지 인입공급관"   # 구간명 (목적 자동생성용)
START_DATE = "2026-01-01"                      # 공사기간 시작
END_DATE = "2026-01-31"                        # 공사기간 종료
ECHK = False                                   # 전자시행품의 여부 (True / False)
# ───────────────────────────────────────────────────────


def main():
    print("=" * 50)
    print(" ZREC2040 시행품의 생성 테스트")
    print("=" * 50)
    print(" 공사번호 :", GONGSA_NO)
    print(" 구간명   :", GU_NAME)
    print(" 공사기간 :", START_DATE, "~", END_DATE)
    print(" 전자여부 :", ECHK)
    print("-" * 50)

    try:
        from sap import connector, zrec2040
    except Exception as e:
        print("[X] 모듈 로드 실패:", e)
        return 1

    # 미리보기: 목적/작업기간이 어떻게 만들어지는지 (SAP 없이도 확인 가능)
    print(" 목적(자동)   :", zrec2040.make_purpose(GU_NAME))
    print(" 작업기간(양식):", zrec2040.fmt_period(START_DATE, END_DATE))
    print("-" * 50)

    # SAP 연결
    try:
        session = connector.get_session()
    except connector.SapConnectionError as e:
        print("[X] SAP 연결 실패:", e)
        return 1

    # 실행
    try:
        msg = zrec2040.create_approval(
            session,
            gongsa_no=GONGSA_NO,
            gu_name=GU_NAME,
            start_date=START_DATE,
            end_date=END_DATE,
            echk=ECHK,
        )
    except Exception as e:
        print("[X] ZREC2040 처리 중 오류:", e)
        print("    (어느 단계에서 멈췄는지 화면을 확인해 알려주세요)")
        return 1

    print("-" * 50)
    print("[O] 처리 완료. 상태 메시지 →", msg if msg else "(메시지 없음)")
    print("    SAP 화면에서 시행품의가 제대로 생성됐는지 확인해 주세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

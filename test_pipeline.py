# -*- coding: utf-8 -*-
"""자동 발주 파이프라인 — 단독 테스트 스크립트 (한 공사 전체 6단계).

⚠️ 이 스크립트는 SAP 에서 접수~발주서까지 6단계를 실제로 실행합니다.
    반드시 테스트 서버에서, 접수 전(미처리) 의뢰공사 1건으로 실행하세요.
    SKIP_TSRM=True 로 두면 마지막 TSRM 발송은 생략합니다.

사용 전 준비:
    ZREC0002 목록이 조회돼 있어야 접수(1단계)가 가능하므로, 스크립트가
    먼저 목록을 조회한 뒤 지정한 행(ROW)을 처리합니다.

사용법 (SAP 로그인 후):
    1) 아래 입력값을 이번 건에 맞게 수정
    2) python test_pipeline.py
    3) 단계별 진행 로그와 마지막 결과 확인
"""

import sys

# ── 입력값 (테스트할 때 여기를 수정) ──────────────────────
WORK = {
    "row": 0,                 # (미사용) 접수는 이제 구간코드(CMP) 기준으로 처리함
    "cmp": "JS20260026",      # 구간코드 — 접수·조회 모두 이 값으로 처리
    "sigun": "51110",         # 시/군 코드 (춘천시)
    "dong": "31022",          # 동읍면리 코드 (동면 만천리)
    "permit": "2218300385",   # 허가청 코드
    "dig": "1",               # 굴착허가 1=대상 / 2=비대상
    "road": "ASP",            # 도로재질 ASP / CONC
    "length": 5,              # 연장(m)
    "plp": False,             # 기존관 PLP 여부
    "vendor": "2218126440",   # 시공업체 코드 (국도건설)
    "gu_name": "춘천시 동면 만천리 844-11번지 인입공급관",  # 구간명(목적 자동생성용)
    "start": "2026-08-01",    # 공사기간 시작
    "end": "2026-08-31",      # 공사기간 종료
    "echk": False,            # 전자시행품의 여부
    "skip_tsrm": True,        # TSRM 발송 생략(True=안전)
}
# ───────────────────────────────────────────────────────


def main():
    print("=" * 55)
    print(" 자동 발주 파이프라인 테스트 (6단계 전체)")
    print("=" * 55)
    for k, v in WORK.items():
        print("  %-10s: %s" % (k, v))
    print("-" * 55)

    try:
        from sap import connector, zrec0002, pipeline
    except Exception as e:
        print("[X] 모듈 로드 실패:", e)
        return 1

    # SAP 연결
    try:
        session = connector.get_session()
    except connector.SapConnectionError as e:
        print("[X] SAP 연결 실패:", e)
        return 1

    # 접수(1단계) 전에 목록을 먼저 조회해 그리드를 띄운다.
    try:
        data = zrec0002.fetch_request_list(session)
        print("  목록 조회:", data.get("row_count"), "건")
    except Exception as e:
        print("[X] 목록 조회 실패:", e)
        return 1

    # 단계 진행 로그 콜백
    def on_progress(step, status, info):
        mark = {"start": "[..]", "done": "[OK]", "fail": "[X]"}.get(status, "·")
        line = "   %s %-9s %s" % (mark, step, status)
        if info:
            line += "  → " + info
        print(line)

    # 실행
    try:
        res = pipeline.run_one(session, WORK, on_progress=on_progress)
    except pipeline.PipelineError as e:
        print("-" * 55)
        print("[X] %s 단계에서 실패:" % e.step, e.cause)
        return 1
    except Exception as e:
        print("[X] 파이프라인 오류:", e)
        return 1

    print("-" * 55)
    print("[O] 전체 완료!")
    print("    공사번호 :", res.get("gongsa_no"))
    print("    산안비   :", res.get("safety"))
    print("    발주 메시지:", res.get("message") or "(없음)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""구간명(주소) → 시/군·동 코드 변환기.

ZREC0100(공사번호 생성) 팝업에는 '구/군' 코드와 '동/읍/면/리' 코드를
넣어야 한다. 그런데 화면에서 사용자가 주는 값은 코드가 아니라 **구간명(주소)**
문자열이다. 예: "춘천시 동면 만천리 844-11번지 인입공급관".

이 모듈은 그 구간명을 읽어 config(settings.json)의 '지역' 코드표를 뒤져
(구/군 코드, 동 코드)를 찾아 준다.

── 행정동/법정동 중복 문제와 해소 방법 ──────────────────────────
SAP F4 표에는 두 종류의 지명이 섞여 있다.
  · '동읍면' 컬럼 : 행정동(예: 조운동) 또는 "면+리"(예: 동면 만천리)
  · '법정'   컬럼 : 법정동(예: 운교동, 조양동)
같은 행정동 '조운동' 이 법정동 '운교동'(11000)·'조양동'(10800) 두 줄로
쪼개지므로, 행정동 이름만으로는 코드를 하나로 정할 수 없다.

주소(구간명)에는 법정동/법정리가 쓰인다("...운교동 12-3", "...만천리 844").
그래서 매칭 키를 아래처럼 잡으면 중복이 사라진다.
  · 면/읍 지역(동읍면에 공백 있음) → 키 = '동읍면' 전체("동면 만천리")
  · 동 지역(동읍면이 행정동 한 덩어리) → 키 = '법정'(법정동 "운교동")
구간명 안에 이 키가 들어 있으면 그 줄의 코드를 쓴다. 여러 개가 걸리면
가장 긴(구체적인) 키를 우선한다. 그래도 코드가 갈리면 '중복'으로 보고
자동을 멈춘다(수동 처리 → 로그).

순수 파이썬(문자열 처리)만 쓰므로 SAP 없이도 단독 테스트가 가능하다.
"""

import re


class RegionError(Exception):
    """구간명에서 시/군·동 코드를 확정하지 못했을 때 발생(수동 처리 대상)."""


def _norm(s):
    """비교용 정규화: 앞뒤 공백 제거 + 내부 공백 단일화."""
    return re.sub(r"\s+", " ", str(s or "").strip())


def _match_key(entry):
    """동 목록의 한 줄에서 '구간명과 대조할 대표 키'를 만든다.

    면/읍(동읍면에 공백) → 동읍면 전체("동면 만천리"),
    그 외(행정동) → 법정(법정동 "운교동").
    """
    dong = _norm(entry.get("동읍면"))
    beopjeong = _norm(entry.get("법정"))
    if " " in dong:          # 면/읍 + 리
        return dong
    return beopjeong or dong  # 동 지역은 법정동으로


def resolve(gu_name, cfg):
    """구간명(gu_name)에서 시/군·동 코드를 찾아 dict 로 반환한다.

    반환:
      {
        "sigun_name": "춘천시", "sigun_code": "51110",
        "dong_name":  "동면 만천리", "dong_code": "31022",
        "matched_key": "동면 만천리"
      }
    실패:
      RegionError(사유)  — 시/군 미식별, 코드 미등록, 동 미식별, 지명 중복 등.
    """
    text = _norm(gu_name)
    if not text:
        raise RegionError("구간명이 비어 있습니다.")

    region = cfg._region() if cfg else {}
    gugun = region.get("구군코드", {})
    if not gugun:
        raise RegionError("지역 코드표(구군코드)가 비어 있습니다. (엑셀 등록 필요)")

    # 1) 시/군 식별 — 구간명에 들어 있는 구/군 이름(가장 긴 것 우선)
    sigun_hits = [name for name in gugun.keys() if name and name in text]
    if not sigun_hits:
        raise RegionError("구간명에서 시/군을 식별하지 못했습니다: '%s'" % text)
    sigun_name = max(sigun_hits, key=len)

    sigun_code = gugun.get(sigun_name) or None
    if not sigun_code:
        raise RegionError("'%s' 의 구/군 코드가 등록되지 않았습니다. (config 구군코드 확인)"
                          % sigun_name)

    # 2) 동/읍/면 식별 — 해당 시/군 동목록에서 키가 구간명에 포함되는 줄 수집
    entries = cfg.dong_entries(sigun_name) if cfg else []
    if not entries:
        raise RegionError("'%s' 의 동 목록이 비어 있습니다. (엑셀 import 필요)" % sigun_name)

    hits = []  # (키길이, 코드, 동읍면, 매칭키)
    for e in entries:
        key = _match_key(e)
        code = str(e.get("코드", "")).strip()
        if key and code and key in text:
            hits.append((len(key), code, _norm(e.get("동읍면")), key))

    # 2-폴백) 대표 키로 못 찾으면 법정명으로 한 번 더 시도.
    #   단, 동지역(동읍면에 공백 없음)만 — 면지역 법정("동면")은 리가 빠져
    #   구체적이지 않으므로 폴백 대상에서 제외(엉뚱한 리로 오인 방지).
    if not hits:
        for e in entries:
            if " " in _norm(e.get("동읍면")):
                continue
            beopjeong = _norm(e.get("법정"))
            code = str(e.get("코드", "")).strip()
            if beopjeong and code and beopjeong in text:
                hits.append((len(beopjeong), code, _norm(e.get("동읍면")), beopjeong))

    if not hits:
        raise RegionError("구간명에서 동/읍/면을 식별하지 못했습니다: '%s'" % text)

    # 3) 가장 긴(구체적인) 키 우선. 최장 키들이 같은 코드면 확정, 코드가 갈리면 중복.
    longest = max(h[0] for h in hits)
    top = [h for h in hits if h[0] == longest]
    codes = {h[1] for h in top}
    if len(codes) > 1:
        detail = ", ".join("%s→%s" % (h[3], h[1]) for h in top)
        raise RegionError("동 지명이 중복되어 코드를 하나로 정할 수 없습니다: %s" % detail)

    _, dong_code, dong_name, matched_key = top[0]
    return {
        "sigun_name": sigun_name,
        "sigun_code": sigun_code,
        "dong_name": dong_name,
        "dong_code": dong_code,
        "matched_key": matched_key,
    }


def _self_check():
    """단독 실행 시 config 로 몇 개 구간명을 시험 변환한다."""
    from config_manager import ConfigManager
    cfg = ConfigManager()
    samples = [
        "춘천시 동면 만천리 844-11번지 인입공급관",
        "춘천시 동면 장학리 12-3 인입공급관",
        "춘천시 소양로3가 55 인입공급관",
        "춘천시 후평동 74-19번지 인입공급관",
        "홍천군 홍천읍 진리 55 인입공급관",
    ]
    print("=" * 60)
    print(" 구간명 → 시/군·동 코드 변환 자가진단")
    print("=" * 60)
    for s in samples:
        try:
            r = resolve(s, cfg)
            print("  [OK] %s\n        → 시군 %s(%s) / 동 %s(%s) [키:%s]" % (
                s, r["sigun_name"], r["sigun_code"],
                r["dong_name"], r["dong_code"], r["matched_key"]))
        except RegionError as e:
            print("  [ 수동 ] %s\n        → %s" % (s, e))


if __name__ == "__main__":
    _self_check()

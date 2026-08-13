# -*- coding: utf-8 -*-
"""지역 코드표(엑셀/CSV) → config/settings.json '지역.동목록' 자동 반영기.

왜 필요한가:
    SAP F4 값도움의 동/읍/면/리 코드가 시/군당 100건이 넘어(춘천 122·홍천 115)
    사람이 손으로 옮기면 오타가 난다. 사용자가 그 목록을 엑셀/CSV 로 내보내
    이 스크립트에 넣으면, 오타 없이 그대로 config 에 채워 넣는다.

기대하는 표 형태(열 제목에 아래 단어가 들어가면 자동 인식):
    시/도 | 구/군 | 동/읍/면 | 읍면동 | 동/읍/면/리 순번
    (예)   춘천시   동면 만천리  동면      31022

    · '구/군'      → 어느 시/군의 목록인지 구분 (춘천시/홍천군)
    · '동/읍/면'   → 구간명과 대조할 이름(면지역은 "면 리")     → config "동읍면"
    · '읍면동'     → 법정동/면                                  → config "법정"
    · '순번'       → 실제 넣을 동 코드                          → config "코드"

사용법:
    python tools/import_region_excel.py  지역코드.xlsx
    python tools/import_region_excel.py  지역코드.csv

    엑셀(.xlsx)은 openpyxl 이 필요하다(pip install openpyxl).
    안 깔려 있으면 CSV 로 저장해서 넣으면 된다(엑셀에서 '다른 이름으로 저장 → CSV').

안전장치:
    · 기존 settings.json 을 settings.json.bak 로 백업한 뒤 저장한다.
    · '구군코드' 에 없는 새 시/군이 나오면 코드 빈칸으로 추가하고 경고한다
      (구/군 코드는 별도 확인 필요).
"""

import os
import sys
import csv
import json
import shutil

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SETTINGS = os.path.join(_ROOT, "config", "settings.json")


def _pick_col(headers, keyword):
    """헤더 목록에서 keyword(공백무시)가 들어간 열의 인덱스를 찾는다."""
    key = keyword.replace(" ", "")
    for i, h in enumerate(headers):
        if key in str(h).replace(" ", ""):
            return i
    return None


def _read_rows(path):
    """엑셀/CSV 를 (headers, rows) 로 읽는다. rows = [[셀,...], ...]."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit(
                "엑셀(.xlsx)을 읽으려면 openpyxl 이 필요합니다.\n"
                "  pip install openpyxl\n"
                "또는 엑셀에서 CSV 로 저장해 다시 시도하세요.")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        data = [[("" if c is None else c) for c in row]
                for row in ws.iter_rows(values_only=True)]
    else:
        # CSV (utf-8-sig: 엑셀 저장 BOM 대응)
        with open(path, encoding="utf-8-sig", newline="") as f:
            data = [row for row in csv.reader(f)]
    data = [r for r in data if any(str(c).strip() for c in r)]  # 빈 줄 제거
    if not data:
        raise SystemExit("표에서 읽을 데이터가 없습니다: %s" % path)
    return data[0], data[1:]


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    path = argv[1]
    if not os.path.exists(path):
        raise SystemExit("파일을 찾을 수 없습니다: %s" % path)

    headers, rows = _read_rows(path)
    i_gugun = _pick_col(headers, "구/군")
    i_dong = _pick_col(headers, "동/읍/면")       # "동/읍/면" (리 포함)
    i_beop = _pick_col(headers, "읍면동")          # 법정동/면
    i_code = _pick_col(headers, "순번")            # 동/읍/면/리 순번 = 코드
    if None in (i_gugun, i_dong, i_beop, i_code):
        raise SystemExit(
            "열 제목을 인식하지 못했습니다. '구/군, 동/읍/면, 읍면동, 순번'"
            " 이 포함된 헤더가 필요합니다.\n  읽은 헤더: %s" % headers)

    # 구/군별로 묶기
    by_gugun = {}
    for r in rows:
        def cell(i):
            return str(r[i]).strip() if i < len(r) else ""
        gugun = cell(i_gugun)
        dong = cell(i_dong)
        beop = cell(i_beop)
        code = cell(i_code)
        if not gugun or not code:
            continue
        by_gugun.setdefault(gugun, []).append(
            {"동읍면": dong, "법정": beop, "코드": code})

    if not by_gugun:
        raise SystemExit("유효한 행(구/군·코드)이 없습니다.")

    # settings.json 로드
    with open(_SETTINGS, encoding="utf-8") as f:
        data = json.load(f)
    region = data.setdefault("지역", {})
    dongmok = region.setdefault("동목록", {})
    gugun_code = region.setdefault("구군코드", {})

    # 반영
    for gugun, entries in by_gugun.items():
        dongmok[gugun] = entries
        if gugun not in gugun_code:
            gugun_code[gugun] = ""   # 구/군 코드는 별도 확인 필요
            print("  [경고] '%s' 는 구군코드가 없습니다 → 빈칸 추가. 구/군 코드를 확인해 채우세요."
                  % gugun)

    # 백업 후 저장
    shutil.copyfile(_SETTINGS, _SETTINGS + ".bak")
    with open(_SETTINGS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("=" * 55)
    print(" 지역 코드표 반영 완료")
    print("=" * 55)
    for gugun, entries in by_gugun.items():
        code = gugun_code.get(gugun) or "(미등록)"
        print("  %-6s : 동 %3d건  · 구/군코드 %s" % (gugun, len(entries), code))
    print("-" * 55)
    print("  백업 : %s" % (_SETTINGS + ".bak"))
    print("  저장 : %s" % _SETTINGS)
    print("  ※ 반영 후 'python -m sap.region' 로 몇 개 구간명을 시험 변환해 보세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

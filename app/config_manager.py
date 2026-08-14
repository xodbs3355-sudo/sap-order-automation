# -*- coding: utf-8 -*-
"""설정(config/settings.json) 관리 모듈.

프로그램 전체가 이 모듈을 통해 설정값(허가청·업체·단가표)을 읽고 씁니다.
- 비유: settings.json 이 '재료 창고'라면, 이 모듈은 재료를 꺼내오고
  재고를 점검하는 '창고지기' 입니다.

SAP·GUI 와 무관한 순수 파이썬 모듈이라 단독 실행/검증이 가능합니다.
    python config_manager.py     # 현재 설정 자가진단 출력

메서드 이름은 영어(오타·인코딩 안전), 설명은 한글 주석으로 답니다.
"""

import json
import os

# settings.json 기본 경로 (이 파일 기준 config/settings.json)
DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "config", "settings.json")

# 단가표에서 쓰는 도로재질 종류와 연장 범위 (고정)
MATERIALS = ("ASP", "CONC")   # ASP=절삭포장, CONC=CON'C 및 보도블럭(ASP 外)
LENGTHS = [str(n) for n in range(1, 11)]   # "1" ~ "10" (m)

# 허가청 콤보에서 '사유지'(도로점용 없음 → 점용료 자재 2줄 모두 제외)를 뜻하는 값
PRIVATE_LAND_LABEL = "해당없음"


class ConfigError(Exception):
    """설정 파일을 읽거나 해석하지 못했을 때 발생."""


class ConfigManager:
    """settings.json 을 불러오고 관리하는 클래스."""

    def __init__(self, path=None):
        self.path = path or DEFAULT_PATH
        self.data = {}
        self.load()

    # ── 파일 입출력 ────────────────────────────────────────────
    def load(self):
        """settings.json 을 읽어 self.data 에 담는다."""
        if not os.path.exists(self.path):
            raise ConfigError("설정 파일을 찾을 수 없습니다: %s" % self.path)
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError("설정 파일 형식(JSON)이 올바르지 않습니다: %s" % e)
        return self.data

    def reload(self):
        """디스크에서 다시 읽어온다(외부에서 파일이 바뀐 경우)."""
        return self.load()

    def save(self, data=None):
        """설정을 파일에 저장한다(단가표 관리 모달의 '저장'에서 사용).

        data 를 주면 그 내용으로 교체 저장하고, 안 주면 현재 self.data 를 저장.
        한글이 깨지지 않도록 ensure_ascii=False, 사람이 읽기 좋게 들여쓰기 2칸.
        """
        if data is not None:
            self.data = data
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return self.path

    # ── 기본 값 ────────────────────────────────────────────────
    @property
    def company_code(self):
        """회사코드 (기본 J000)."""
        return self.data.get("company_code", "J000")

    @property
    def test_server_mode(self):
        """테스트 서버 모드 여부 (True 면 ZREC0208 의 TSRM 전송 건너뜀)."""
        return bool(self.data.get("test_server_mode", False))

    # ── 목록(드롭다운용) ───────────────────────────────────────
    def permit_offices(self):
        """허가청 목록. code·name 이 모두 채워진 항목만 반환."""
        return [x for x in self.data.get("허가청", [])
                if x.get("code") and x.get("name")]

    def vendors(self):
        """토목배관업체 목록. code·name 이 모두 채워진 항목만 반환."""
        return [x for x in self.data.get("토목배관업체", [])
                if x.get("code") and x.get("name")]

    def permit_code(self, name):
        """허가청 이름(예: '춘천시청') → 코드. 없으면 None."""
        for x in self.permit_offices():
            if str(x.get("name")).strip() == str(name).strip():
                return x.get("code")
        return None

    def vendor_code(self, name):
        """시공업체 이름(예: '국도건설') → 코드. 없으면 None."""
        for x in self.vendors():
            if str(x.get("name")).strip() == str(name).strip():
                return x.get("code")
        return None

    # ── 지역(시/군·동 코드) ────────────────────────────────────
    def _region(self):
        return self.data.get("지역", {})

    def sigun_code(self, sigun_name):
        """구/군 이름(예: '춘천시') → 구/군 F4 코드. 미등록/빈값이면 None."""
        code = self._region().get("구군코드", {}).get(str(sigun_name).strip())
        return code or None

    def sigun_names(self):
        """등록된 구/군 이름 목록(코드 유무 무관)."""
        return list(self._region().get("구군코드", {}).keys())

    def dong_entries(self, sigun_name):
        """해당 구/군의 동 목록 [{동읍면,법정,코드}, ...]. 없으면 빈 리스트."""
        return self._region().get("동목록", {}).get(str(sigun_name).strip(), [])

    # ── 단가표 ─────────────────────────────────────────────────
    def _price_root(self):
        return self.data.get("단가표", {})

    def years(self):
        """단가표에 등록된 연도 목록 (문자열, 오름차순)."""
        return sorted(self._price_root().get("연도별", {}).keys())

    def price_year(self, year):
        """해당 연도의 금액 표(dict)를 반환. 없으면 ConfigError."""
        year = str(year)
        table = self._price_root().get("연도별", {})
        if year not in table:
            raise ConfigError("단가표에 %s 년도가 없습니다." % year)
        return table[year]

    def material_code(self, material, length):
        """(도로재질, 연장) 에 해당하는 SAP 자재코드를 반환."""
        codes = self._price_root().get("자재코드", {}).get("도로재질", {})
        return codes.get(material, {}).get(str(length))

    def plp_code(self):
        """PLP 옵션 자재코드 (202821)."""
        return self._price_root().get("자재코드", {}).get("PLP")

    def plp_amount(self, year):
        """해당 연도의 PLP 옵션 금액."""
        return self.price_year(year).get("PLP")

    def is_year_ready(self, year):
        """해당 연도 단가표가 자동화 가능한 상태인지(20개+PLP 모두 입력됨) 검사."""
        try:
            table = self.price_year(year)
        except ConfigError:
            return False
        for material in MATERIALS:
            cells = table.get(material, {})
            for length in LENGTHS:
                if cells.get(length) is None:
                    return False
        return table.get("PLP") is not None

    def lookup_price(self, investment, year):
        """투자비(investment)로 단가표를 대조해 자재코드를 찾는다.

        설계서의 단가 매핑 로직:
          Step 1. 투자비를 20개 금액과 직접 대조 → 유일 일치 시 그 코드 단독.
          Step 2. 불일치 시 각 금액 + PLP옵션 금액 을 대조 → 유일 일치 시 그 코드 + PLP.
          Step 3. 그래도 불일치 → None (자동화 중단, 수동 처리 대상).

        반환(dict) 예:
          {"status": "단독", "material": "ASP", "length": 3,
           "code": "202803", "amount": 3370000, "with_plp": False}
          {"status": "PLP포함", ..., "with_plp": True,
           "plp_code": "202821", "plp_amount": 192000}
          None  → 일치 항목 없음(또는 중복이라 유일하지 않음)
        """
        table = self.price_year(year)

        # 후보 20개 수집: (재질, 연장, 금액, 자재코드)
        candidates = []
        for material in MATERIALS:
            cells = table.get(material, {})
            for length in LENGTHS:
                amount = cells.get(length)
                if amount is None:
                    continue
                candidates.append(
                    (material, int(length), amount, self.material_code(material, length))
                )

        # Step 1. 직접 대조
        direct = [c for c in candidates if c[2] == investment]
        if len(direct) == 1:
            material, length, amount, code = direct[0]
            return {"status": "단독", "material": material, "length": length,
                    "code": code, "amount": amount, "with_plp": False}

        # Step 2. PLP 합산 대조
        plp = table.get("PLP")
        if plp is not None:
            with_plp = [c for c in candidates if c[2] + plp == investment]
            if len(with_plp) == 1:
                material, length, amount, code = with_plp[0]
                return {"status": "PLP포함", "material": material, "length": length,
                        "code": code, "amount": amount, "with_plp": True,
                        "plp_code": self.plp_code(), "plp_amount": plp}

        # Step 3. 불일치(또는 유일하지 않음) → 수동 처리
        return None

    def lookup_price_smart(self, investment, prefer_year=None):
        """연도를 몰라도 투자비로 재질/연장/PLP를 찾는다.

        prefer_year(예: 의뢰일자·공사시작 연도)를 먼저 시도하고, 안 맞으면
        등록된 모든 연도를 훑는다. 승인투자비는 연도마다 값이 달라 보통 한
        연도에서만 유일하게 맞는다.
          · 여러 연도가 걸려도 (재질·연장·PLP)가 동일하면 자재코드가 같으므로 사용.
          · 연도별로 결과가 갈리면(재질/연장 다름) 모호 → None(수동).
        반환: lookup_price 결과 dict + {"year": 사용연도, "years_matched": [...]}
              또는 None.
        """
        years = self.years()
        order = []
        if prefer_year and str(prefer_year) in years:
            order.append(str(prefer_year))
        order += [y for y in years if y not in order]

        found = []
        for y in order:
            r = self.lookup_price(investment, y)
            if r:
                found.append((y, r))
        if not found:
            return None
        sig = {(r["material"], r["length"], r["with_plp"]) for _, r in found}
        if len(sig) > 1:
            return None  # 연도별로 결과가 갈림 → 모호(수동 처리)
        y, r = found[0]
        out = dict(r)
        out["year"] = y
        out["years_matched"] = [f[0] for f in found]
        return out

    # ── 점용료(면제 판정) ──────────────────────────────────────
    def _occupancy(self):
        return self.data.get("점용료", {})

    def occupancy_width(self, sigun_code):
        """시/군 코드 → 개착폭(m). 권역 미확인/미등록이면 춘천 기준 1.0."""
        widths = self._occupancy().get("개착폭", {})
        w = widths.get(str(sigun_code).strip())
        try:
            return float(w) if w is not None else 1.0
        except (TypeError, ValueError):
            return 1.0

    def occupancy_fee(self, sigun_code, length):
        """점용료 판정금액 = 연장 × 개착폭 × 점용일수 × 일단가 (면제 판단 전용).

        ※ 이 값은 '면제 여부'를 정하는 계산일 뿐, SAP 자재 수량과는 무관하다
          (SAP 점용료 수량은 개착폭을 반영하지 않고 연장×점용일수 그대로 넣는다).
        """
        o = self._occupancy()
        days = o.get("점용일수", 30)
        rate = o.get("일단가", 75)
        try:
            return int(round(float(length) * self.occupancy_width(sigun_code)
                             * float(days) * float(rate)))
        except (TypeError, ValueError):
            return 0

    def occupancy_exempt_threshold(self):
        """점용료 면제 기준 금액(판정금액이 이 값 이하이면 면제)."""
        return self._occupancy().get("면제기준", 10000)

    def is_occupancy_exempt(self, sigun_code, length):
        """점용료 면제 대상인지(판정금액 ≤ 면제기준). 권역 미확인이면 춘천 기준."""
        return self.occupancy_fee(sigun_code, length) <= self.occupancy_exempt_threshold()

    # ── 전체 검증 ──────────────────────────────────────────────
    def validate(self):
        """설정 전체를 점검해 문제 목록(list[str])을 반환. 비어 있으면 정상."""
        problems = []
        if not self.permit_offices():
            problems.append("허가청 목록이 비어 있습니다. (설정에서 코드+이름 등록 필요)")
        if not self.vendors():
            problems.append("토목배관업체 목록이 비어 있습니다. (설정에서 코드+이름 등록 필요)")
        if not self.years():
            problems.append("단가표에 등록된 연도가 없습니다.")
        for year in self.years():
            if not self.is_year_ready(year):
                problems.append("%s 년도 단가표가 미완성입니다. (20개 금액+PLP 확인 필요)" % year)
        return problems


def _self_check():
    """단독 실행 시 현재 설정 상태를 사람이 보기 좋게 출력."""
    print("=" * 50)
    print(" 설정(config) 자가진단")
    print("=" * 50)
    cfg = ConfigManager()
    print("설정 파일 :", cfg.path)
    print("회사코드  :", cfg.company_code)
    print("테스트모드:", cfg.test_server_mode)
    print("허가청    :", len(cfg.permit_offices()), "개")
    print("배관업체  :", len(cfg.vendors()), "개")
    print("단가표 연도:", cfg.years())
    for year in cfg.years():
        print("  - %s : %s" % (year, "준비완료" if cfg.is_year_ready(year) else "미완성"))

    print("-" * 50)
    print("[단가 매핑 예시 · 2026년]")
    tests = [3370000, 3370000 + 192000, 9999999]
    for inv in tests:
        result = cfg.lookup_price(inv, "2026")
        print("  투자비 %10s →" % format(inv, ","), result)

    print("-" * 50)
    print("[점용료 면제 판정 예시]")
    for sigun, nm in (("51110", "춘천"), ("51720", "홍천")):
        for L in (3, 4, 5):
            fee = cfg.occupancy_fee(sigun, L)
            state = "면제" if cfg.is_occupancy_exempt(sigun, L) else "부과"
            print("  %s %2dm → %8s원 · %s" % (nm, L, format(fee, ","), state))

    print("-" * 50)
    problems = cfg.validate()
    if problems:
        print("검증 결과: 아래 항목 확인 필요")
        for p in problems:
            print("  [!]", p)
    else:
        print("검증 결과: 이상 없음 ✅")


if __name__ == "__main__":
    _self_check()

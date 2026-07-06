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
    problems = cfg.validate()
    if problems:
        print("검증 결과: 아래 항목 확인 필요")
        for p in problems:
            print("  [!]", p)
    else:
        print("검증 결과: 이상 없음 ✅")


if __name__ == "__main__":
    _self_check()

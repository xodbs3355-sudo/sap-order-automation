# -*- coding: utf-8 -*-
"""ZMEC0210 — 설계예산서 작성(공사비 산출).

처리 개요(실제 녹화 기준):
    1. ZMEC0210 진입 → 공사번호(GV_GSCD) 입력 → Enter(조회)
    2. 설계잠금(SGLOCK) 체크 해제
    3. 사양 탭(TAB03): 압력=LP, 재질=PEI, 관경=63(고정) + 연장(가변) 입력
    4. 자재 탭(TAB07): 부위코드별 단가코드/수량 입력 (줄마다 부위코드도 입력)
         · 배관공사(부위 31101): 도로재질 자재코드(수량1) [+ PLP옵션(수량1)]
         · 점용료(부위 91103): 상황에 따라 조건부 입력
             - 사유지        : 없음(261501·291509 모두 제외)
             - 공용지·면제    : 291509(신청수수료)만
             - 공용지·부과    : 261501(수량=연장×30) + 291509(신청수수료)
    5. 저장 → "예"
    6. TAB01에서 확인 체크(SCHK13) → 저장 → "예" → 확인
    7. 산업안전보건관리비(자동계산 금액) 라벨 읽기 → 반환
    8. 뒤로

입력값(케이스마다 다른 값): 공사번호 / 도로재질(ASP·CONC) / 연장(1~10m) / PLP 여부.
나머지(자재코드·점용료 수량·부위코드·고정 사양)는 단가표 기준으로 자동 처리한다.

- 도로재질 자재코드: 단가표(config)에서 (도로재질, 연장) 으로 조회.
- 점용료 수량: 연장(m) × 30일 (인입공급관 점용기간 1개월 고정).

필드 주소는 SAP Script Recording 실측값. Windows + SAP 에서만 실제 동작한다.

주의(테스트 검증 필요):
    산업안전보건관리비 라벨(lbl%#AUTOTEXT108)의 자동생성 번호는 화면 구성에 따라
    달라질 수 있어, 첫 테스트에서 읽힌 값이 맞는지 확인이 필요하다.
"""

import re

from sap import connector
from config_manager import ConfigManager

try:
    import applog
except Exception:  # applog 없이도 동작하도록(로그만 생략)
    applog = None

# ── 화면 요소 주소 (녹화 실측) ─────────────────────────────
SEL_GSCD = "wnd[0]/usr/ctxtGV_GSCD"                 # 공사번호 입력
CHK_SGLOCK = "wnd[0]/usr/chkZECT0101-SGLOCK"        # 설계잠금 체크박스

TAB = "wnd[0]/usr/tabsTABST01/"                     # 탭 컨트롤 접두어
TAB01 = TAB + "tabpTAB01"
TAB03 = TAB + "tabpTAB03"
TAB07 = TAB + "tabpTAB07"

# 사양 탭(TAB03) 입력 셀 (한 줄, row 0)
_T03 = TAB03 + "/ssubTAB_REF:SAPMZEC0210:0103/tblSAPMZEC0210TC03/"
CMB_PRESSURE = _T03 + "cmbIT_03-PRESSURE[0,0]"      # 압력 (LP 고정)
CMB_QUALITY = _T03 + "cmbIT_03-QUALITY[1,0]"        # 재질 (PEI 고정)
CMB_PI = _T03 + "cmbIT_03-PI[2,0]"                  # 관경 (63 고정)
TXT_SILEN = _T03 + "txtIT_03-SILEN[3,0]"            # 연장(m) (가변)

# 자재 탭(TAB07) 입력 셀 — 열: 0=부위코드, 2=단가코드, 6=수량 / 줄(row)은 가변
_T07 = TAB07 + "/ssubTAB_REF:SAPMZEC0210:0107/tblSAPMZEC0210TC07/"
CELL_BWCD = _T07 + "ctxtIT_07-BWCD[0,%d]"           # 부위코드 (열0)
CELL_JAJAE = _T07 + "ctxtIT_07-JAJAE[2,%d]"         # 단가코드 (열2)
CELL_SURA = _T07 + "txtIT_07-SURA[6,%d]"            # 수량 (열6)

# TAB01 요소
SUB1101 = TAB01 + "/ssubTAB_REF:SAPMZEC0210:1101"  # TAB01 서브스크린(1101)
_T01 = SUB1101 + "/"
CHK_SCHK13 = _T01 + "chkZECT0213-SCHK13"            # 확인 체크박스
SAFETY_CAPTION = "산업안전보건관리비"                 # 이 제목 라벨과 같은 줄의 숫자 = 금액

_AMOUNT_PAT = re.compile(r"^-?[\d,]+$")            # 금액(천단위 콤마 포함) 형식

BTN_SAVE = "wnd[0]/tbar[0]/btn[11]"      # 저장 (Ctrl+S)
BTN_BACK = "wnd[0]/tbar[0]/btn[3]"       # 뒤로 (F3)
POP_YES = "wnd[1]/usr/btnSPOP-OPTION1"   # 저장 팝업 "예"
POP_OK = "wnd[1]/tbar[0]/btn[0]"         # 확인(정보 팝업)

# ── 고정값 ─────────────────────────────────────────────────
BWCD_PIPE = "31101"      # 부위: 배관공사
BWCD_FEE = "91103"       # 부위: 점용료
CODE_OCCUPY = "261501"   # 단가코드: 점용료 산정 (수량=연장×30)
CODE_SUBMIT = "291509"   # 단가코드: 제출비용 (수량=1)

SPEC_PRESSURE = "LP"     # 압력 (63A 전용 고정)
SPEC_QUALITY = "PEI"     # 재질 (고정)
SPEC_PI = "63"           # 관경 63A (고정)

OCCUPY_DAYS = 30         # 점용 일수 (인입공급관 = 1개월 고정)


def _occ_log(msg):
    """점용료 처리 결정을 로그로 남긴다(applog 없으면 조용히 생략)."""
    if applog:
        try:
            applog.info("[점용료] " + msg)
        except Exception:
            pass


def _enter_row(session, r, bwcd, jajae, sura):
    """자재 탭 r번째 줄에 [부위코드, 단가코드, 수량]을 입력한다.

    각 셀 입력 후 Enter(sendVKey 0)로 확정 — 녹화 실측 순서 그대로.
    (부위코드는 줄마다 각각 입력한다.)
    """
    session.findById(CELL_BWCD % r).text = bwcd
    session.findById("wnd[0]").sendVKey(0)
    session.findById(CELL_JAJAE % r).text = jajae
    session.findById("wnd[0]").sendVKey(0)
    session.findById(CELL_SURA % r).text = sura
    session.findById("wnd[0]").sendVKey(0)


def _save(session):
    """저장(btn[11]) 후 뒤따르는 "예"/확인 팝업을 처리한다(있으면)."""
    session.findById(BTN_SAVE).press()
    try:
        session.findById(POP_YES).press()   # "저장하시겠습니까?" → 예
    except Exception:
        pass
    # 이어서 정보/확인 팝업이 뜨면 닫는다(확인 버튼 또는 Enter)
    try:
        session.findById(POP_OK).press()
    except Exception:
        try:
            session.findById("wnd[1]").sendVKey(0)
        except Exception:
            pass


def _read_safety_cost(session):
    """TAB01의 산업안전보건관리비(자동계산) '금액'을 읽어 반환.

    화면에는 '산업안전보건관리비(배관)' 제목 라벨과, 그 옆(같은 줄)에 금액이
    별도 라벨로 표시된다. 제목의 자동생성 ID(AUTOTEXT###)는 화면마다 바뀔 수
    있으므로 ID 를 직접 쓰지 않고, 서브스크린(1101)의 라벨들을 훑어서
      ① '산업안전보건관리비' 제목 라벨의 세로 위치(Top)를 찾고
      ② 같은 줄에 있는 숫자 형태 라벨(=금액)을 골라 반환한다.
    저장(계산) 후에만 값이 채워진다. 실패 시 None.
    """
    try:
        session.findById(TAB01).select()
    except Exception:
        pass
    try:
        children = session.findById(SUB1101).Children
    except Exception:
        return None

    # 라벨 수집 + 제목(산업안전보건관리비) 줄의 세로 위치 찾기
    labels = []            # (top, text)
    caption_top = None
    for i in range(children.Count):
        try:
            ch = children.ElementAt(i)
            text = str(ch.Text).strip()
            top = int(ch.Top)
        except Exception:
            continue
        labels.append((top, text))
        if SAFETY_CAPTION in text:
            # '(배관)' 을 우선, 없으면 첫 제목 사용
            if caption_top is None or text == SAFETY_CAPTION + "(배관)":
                caption_top = top

    if caption_top is None:
        return None

    # 같은 줄(Top 근사)에서 숫자 형태의 라벨(=금액)을 반환
    for top, text in labels:
        if abs(top - caption_top) <= 2 and SAFETY_CAPTION not in text:
            cleaned = text.replace(" ", "")
            if cleaned and _AMOUNT_PAT.match(cleaned):
                return text
    return None


def create_design_budget(session, gongsa_no, road_material, length, plp=False,
                         cfg=None, sigun_code=None, private_land=False):
    """ZMEC0210 으로 설계예산서를 작성하고 산업안전보건관리비를 반환한다.

    인자:
        gongsa_no     : 공사번호 (예: "2026A0062")
        road_material : 도로재질 "ASP" 또는 "CONC"(=ASP 아님, 보도블럭 포함)
        length        : 연장(m) 1~10 (정수)
        plp           : 기존관 PLP 여부 (True 면 PLP옵션 단가코드 1줄 추가)
        cfg           : ConfigManager (없으면 새로 생성) — 단가표 자재코드 조회용
        sigun_code    : 시/군 코드(예 "51110") — 점용료 면제 판정(개착폭)에 사용.
                        미확인이면 춘천 기준(1.0)으로 판정.
        private_land  : 사유지 여부. True 면 점용료 2줄(261501·291509) 모두 제외.
    반환:
        산업안전보건관리비 금액 문자열(예: "1,234,567") 또는 None(읽기 실패)

    점용료 처리 규칙:
        · 사유지            → 점용료·신청수수료 둘 다 제외
        · 공용지·면제        → 판정금액 ≤ 면제기준 이면 점용료(261501)만 제외, 신청수수료(291509)는 유지
        · 공용지·부과        → 점용료(수량=연장×점용일수) + 신청수수료 둘 다 입력
    """
    cfg = cfg or ConfigManager()
    length = int(length)

    # 1) 도로재질 자재코드 (단가표 기준). 없으면 잘못된 입력.
    road_code = cfg.material_code(road_material, length)
    if not road_code:
        raise RuntimeError("자재코드를 찾을 수 없습니다: 재질=%s, 연장=%s"
                           % (road_material, length))

    # 2) 입력할 자재 줄 구성 (부위코드, 단가코드, 수량) — 순서 그대로 입력
    rows = [(BWCD_PIPE, road_code, "1")]                       # 배관공사: 도로재질(수량1)
    if plp:
        rows.append((BWCD_PIPE, cfg.plp_code(), "1"))          # 배관공사: PLP옵션(수량1)

    # 2-1) 점용료 2줄 — 사유지/면제 규칙 적용
    if private_land:
        _occ_log("사유지 → 점용료·신청수수료 모두 제외")
    else:
        fee = cfg.occupancy_fee(sigun_code, length)            # 면제 판정금액(SAP 수량과 무관)
        if cfg.is_occupancy_exempt(sigun_code, length):
            _occ_log("점용료 면제(판정 %s원 ≤ %s원) → 점용료 제외, 신청수수료만 입력"
                     % (format(fee, ","), format(cfg.occupancy_exempt_threshold(), ",")))
        else:
            _occ_log("점용료 부과(판정 %s원) → 점용료+신청수수료 입력" % format(fee, ","))
            rows.append((BWCD_FEE, CODE_OCCUPY, str(length * OCCUPY_DAYS)))  # 점용료(연장×30)
        rows.append((BWCD_FEE, CODE_SUBMIT, "1"))              # 신청수수료(면제여도 유지, 수량1)

    # 3) ZMEC0210 진입 + 공사번호 조회
    #    ※ 이 화면은 Enter 1번으로는 코드만 확정되고, 2번째 Enter라야
    #      실제 데이터가 표시된다. → sendVKey(0) 을 2번 보낸다.
    connector.go_tcode(session, "ZMEC0210")
    session.findById(SEL_GSCD).text = gongsa_no
    session.findById("wnd[0]").sendVKey(0)   # 1차 Enter (코드 확정)
    session.findById("wnd[0]").sendVKey(0)   # 2차 Enter (데이터 표시)

    # 4) 설계잠금(SGLOCK) 처리 — 상태를 보고 필요할 때만 해제
    #    실제 프로세스: 잠금(체크)된 상태 → 해제해야 편집 가능.
    #    이미 해제돼 있으면(테스트처럼) 그대로 둔다.
    try:
        chk = session.findById(CHK_SGLOCK)
        if chk.selected:          # 체크(잠금)되어 있을 때만
            chk.selected = False  # 해제
    except Exception:
        pass

    # 5) 사양 탭(TAB03): 압력/재질/관경(고정) + 연장(가변)
    session.findById(TAB03).select()
    session.findById(CMB_PRESSURE).key = SPEC_PRESSURE
    session.findById(CMB_QUALITY).key = SPEC_QUALITY
    session.findById(CMB_PI).key = SPEC_PI
    session.findById(TXT_SILEN).text = str(length)
    session.findById("wnd[0]").sendVKey(0)

    # 6) 자재 탭(TAB07): 줄별 입력
    session.findById(TAB07).select()
    for r, (bwcd, jajae, sura) in enumerate(rows):
        _enter_row(session, r, bwcd, jajae, sura)

    # 7) 저장(1차)
    _save(session)

    # 8) TAB01에서 확인 체크(SCHK13) → 저장(2차, = 예산 계산)
    session.findById(TAB01).select()
    try:
        session.findById(CHK_SCHK13).selected = True
    except Exception:
        pass
    _save(session)

    # 9) 산업안전보건관리비 읽기 (저장/계산 후에만 값이 뜬다)
    safety_cost = _read_safety_cost(session)

    # 10) 뒤로
    try:
        session.findById(BTN_BACK).press()
    except Exception:
        pass

    return safety_cost

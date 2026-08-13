# -*- coding: utf-8 -*-
"""상세 로깅 — 파일(logs/) + 화면(처리 로그)에 동시에 남긴다.

목적: 테스트 중 오류를 정확히 짚을 수 있도록 "무슨 값으로 무엇을 시도했고
어디서 멈췄는지"를 아주 자세히 기록한다.

두 곳에 기록한다.
  1) 파일 : logs/app_YYYYMMDD.log  (프로그램을 껐다 켜도 남는 영구 기록)
  2) 화면 : 우측 하단 '로그' 버튼의 처리 로그 창 (실시간 확인용)
     → main.py 가 set_gui_emit() 으로 '화면에 한 줄 찍는 함수'를 넘겨준다.

레벨(level): "info" | "success" | "warn" | "error"
  화면 색상과 맞춘다(성공=초록, 경고=주황, 오류=빨강).

순수 파이썬(logging 표준 모듈)만 쓰므로 어디서든 import 된다.
"""

import logging
import os
import datetime
import traceback

# 로그 파일 폴더 (이 파일 기준 logs/)
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# 화면(GUI)에 로그를 찍는 콜백 — main.py 가 등록한다. 없으면 파일에만 남는다.
_gui_emit = None  # callable(msg: str, level: str) -> None

_logger = None       # 파일 로거(한 번만 설정)
_LEVEL_MAP = {"info": logging.INFO, "success": logging.INFO,
              "warn": logging.WARNING, "error": logging.ERROR}


def set_gui_emit(fn):
    """화면에 로그를 찍는 함수를 등록한다(main.py 에서 pywebview 창 연결용)."""
    global _gui_emit
    _gui_emit = fn


def _get_logger():
    """파일 로거를 준비해 반환(최초 1회 설정). 파일 경로: logs/app_오늘날짜.log."""
    global _logger
    if _logger is not None:
        return _logger
    logger = logging.getLogger("sap_auto")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        fname = "app_%s.log" % datetime.date.today().strftime("%Y%m%d")
        fh = logging.FileHandler(os.path.join(_LOG_DIR, fname), encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(message)s", "%H:%M:%S"))
        # 중복 핸들러 방지
        if not logger.handlers:
            logger.addHandler(fh)
    except Exception:
        # 파일을 못 열어도(권한 등) 프로그램은 계속 — 화면 로그만이라도 남긴다.
        pass
    _logger = logger
    return logger


def log(msg, level="info"):
    """한 줄 기록. 파일 + (등록됐다면) 화면 양쪽에 남긴다."""
    msg = str(msg)
    try:
        _get_logger().log(_LEVEL_MAP.get(level, logging.INFO), msg)
    except Exception:
        pass
    if _gui_emit:
        try:
            _gui_emit(msg, level)
        except Exception:
            pass


def info(msg):    log(msg, "info")
def success(msg): log(msg, "success")
def warn(msg):    log(msg, "warn")
def error(msg):   log(msg, "error")


def section(title):
    """구분선과 함께 소제목을 남긴다(가독성용)."""
    log("──────── %s ────────" % title, "info")


def exc(msg):
    """예외를 기록한다 — 화면엔 짧은 사유, 파일엔 전체 트레이스백."""
    tb = traceback.format_exc()
    try:
        _get_logger().error("%s\n%s", msg, tb)
    except Exception:
        pass
    if _gui_emit:
        try:
            _gui_emit(str(msg), "error")
        except Exception:
            pass


def log_file_path():
    """현재 로그 파일 경로(사용자에게 안내용). 폴더가 없으면 만들어 준다."""
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
    except Exception:
        pass
    fname = "app_%s.log" % datetime.date.today().strftime("%Y%m%d")
    return os.path.join(_LOG_DIR, fname)

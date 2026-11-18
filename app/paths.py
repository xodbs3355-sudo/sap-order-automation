# -*- coding: utf-8 -*-
"""프로그램 폴더 경로를 한곳에서 정한다(파이썬 실행 / .exe 실행 공통).

왜 필요한가:
  .exe(PyInstaller)로 묶으면 파이썬 코드는 exe 내부 폴더(_internal)로 들어가서
  "코드 파일 위치" 기준 경로가 설정·화면·로그 파일 위치와 어긋난다.
  그래서 기준을 '프로그램 루트 폴더' 하나로 통일한다.

  - 파이썬 실행(py main.py): 루트 = main.py 가 있는 폴더 (지금과 동일)
  - .exe 실행            : 루트 = SAPOrderAutomation.exe 가 있는 폴더(설치 폴더)

  두 경우 모두 루트 아래 구조는 같다 → app/config, app/gui, app/logs, app/version.json
  (설치 프로그램이 exe 옆에 app 폴더를 같은 구조로 복사한다)
  → 비유: 어느 건물(파이썬/exe)이든 '정문' 위치만 알면 나머지 방 위치는 같다.
"""

import os
import sys

FROZEN = bool(getattr(sys, "frozen", False))   # .exe 로 실행 중인지

if FROZEN:
    ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/ 의 상위

APP_DIR = os.path.join(ROOT, "app")
CONFIG_DIR = os.path.join(APP_DIR, "config")
GUI_DIR = os.path.join(APP_DIR, "gui")
LOG_DIR = os.path.join(APP_DIR, "logs")
VERSION_FILE = os.path.join(APP_DIR, "version.json")

"""
AI 스무고개 게임 핵심 로직 (Google Gemini 버전)
"""
import json
from typing import Dict, List

import streamlit as st
from google import genai
from google.genai import types


MODEL_NAME = "gemini-2.5-flash-lite"

MAX_QUESTIONS = 20


def _get_client() -> genai.Client:
    """Gemini 클라이언트 초기화"""
    return genai.Client(api_key=st.secrets["gemini"]["api_key"])


# ===== 모드 1: AI가 맞히기 =====

_SYSTEM_PROMPT = """당신은 스무고개 게임의 천재 플레이어입니다.
사용자가 머릿속에 '무언가'(사물, 동물, 인물, 장소, 개념 등)를 하나 정했습니다.
당신의 목표는 예/아니오로 답할 수 있는 질문을 던져서, 그것이 무엇인지 맞히는 것입니다.

## 규칙
- 최대 20개의 질문만 할 수 있습니다.
- 매 차례에 (1) 새로운 질문을 하거나 (2) 정답을 추측합니다.
- 질문은 반드시 예/아니오로 답할 수 있어야 합니다.
- 앞선 답변들을 논리적으로 활용해 후보를 좁혀가세요.
- 처음에는 넓은 범주(생물인가? 만질 수 있나? 등

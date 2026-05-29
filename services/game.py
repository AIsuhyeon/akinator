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


# ===== 모드 1: AI가 맞히기 (기존) =====

_SYSTEM_PROMPT = """당신은 스무고개 게임의 천재 플레이어입니다.
사용자가 머릿속에 '무언가'(사물, 동물, 인물, 장소, 개념 등)를 하나 정했습니다.
당신의 목표는 예/아니오로 답할 수 있는 질문을 던져서, 그것이 무엇인지 맞히는 것입니다.

## 규칙
- 최대 20개의 질문만 할 수 있습니다.
- 매 차례에 (1) 새로운 질문을 하거나 (2) 정답을 추측합니다.
- 질문은 반드시 예/아니오로 답할 수 있어야 합니다.
- 앞선 답변들을 논리적으로 활용해 후보를 좁혀가세요.
- 처음에는 넓은 범주(생물인가? 만질 수 있나? 등)부터, 점점 구체적으로 좁히세요.
- 확신이 충분히 서면(보통 후보가 1~2개로 좁혀지면) 추측하세요.
- 같은 질문을 반복하지 마세요.

## 답변 형식
반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트는 절대 출력하지 마세요.

질문할 때:
{"type": "question", "content": "예/아니오로 답할 수 있는 질문"}

정답을 추측할 때:
{"type": "guess", "content": "추측한 정답 (명사 하나)"}
"""


def get_ai_move(qa_history: List[Dict], force_guess: bool = False) -> Dict:
    """지금까지의 질문/답변을 바탕으로 AI의 다음 행동을 결정한다."""
    client = _get_client()

    history_lines = []
    for i, qa in enumerate(qa_history, start=1):
        history_lines.append(f"질문 {i}: {qa['question']} → 답변: {qa['answer']}")
    history_text = "\n".join(history_lines) if history_lines else "(아직 질문 없음)"

    question_count = len(qa_history)

    user_prompt = f"""지금까지 {question_count}개의 질문을 했습니다.
남은 질문: {MAX_QUESTIONS - question_count}개

## 지금까지의 문답
{history_text}

이제 당신의 차례입니다."""

    if force_guess:
        user_prompt += "\n\n질문 기회를 모두 소진했습니다. 반드시 정답을 추측(guess)하세요."
    elif question_count >= MAX_QUESTIONS - 2:
        user_prompt += "\n\n질문이 거의 끝나갑니다. 슬슬 추측을 고려하세요."

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.7,
                max_output_tokens=1000,
            ),
        )
    except Exception as e:
        raise Exception(f"AI 호출 중 오류: {e}") from e

    result_text = response.text
    if not result_text:
        raise ValueError("AI 응답이 비어있습니다.")

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI 응답 파싱 실패: {e}") from e

    move_type = result.get("type", "question")
    content = str(result.get("content", "")).strip()

    if move_type not in ("question", "guess"):
        move_type = "question"

    if not content:
        move_type = "question"
        content = "그것은 만질 수 있는 물건인가요?"

    if force_guess and move_type == "question":
        move_type = "guess"

    return {"type": move_type, "content": content}


def get_final_reaction(won: bool, qa_history: List[Dict], answer: str = "") -> str:
    """게임 종료 후 AI의 한 줄 소감을 생성한다."""
    client = _get_client()

    if won:
        prompt = f"당신은 방금 스무고개에서 {len(qa_history)}개의 질문 만에 정답을 맞혔습니다. 승리의 기쁨을 담아 재치있고 짧은 한국어 소감을 한 문장으로 말하세요."
    else:
        prompt = f"당신은 스무고개에서 정답을 맞히지 못했습니다. 실제 정답은 '{answer}'였습니다. 아깝게 진 것에 대한 재치있고 깔끔한 한국어 소감을 한 문장으로 말하세요."

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9,
                max_output_tokens=100,
            ),
        )
        return (response.text or "").strip() or ("좋은 게임이었어요!" if won else "다음엔 꼭 맞힐게요!")
    except Exception:
        return "좋은 게임이었어요!" if won else "다음엔 꼭 맞힐게요!"


# ===== 모드 2: AI가 출제하기 (사람이 맞히기) =====

_HOST_SYSTEM_PROMPT = """당신은 스무고개 게임의 '출제자'입니다.
당신이 정답을 하나 정하고, 사용자가 질문으로 그것을 맞힙니다.
- 정답은 누구나 아는 사물/동물/인물/장소/개념 중 하나여야 합니다.
- 사용자의 질문에는 반드시 정답에 근거해 정직하게 답하세요.
반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트는 출력하지 마세요."""


def start_host_game() -> Dict:
    """AI가 정답을 정하고 첫 힌트를 준다."""
    client = _get_client()
    prompt = """스무고개 정답을 하나 정하세요.
JSON 형식: {"answer": "정답 명사 하나", "hint": "정답을 직접 말하지 않는 넓은 범주 힌트 한 줄"}"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_HOST_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=1.0,
                max_output_tokens=2000,
            ),
        )
        result_text = (response.text or "").strip()
        if not result_text:
            raise ValueError("AI 응답이 비어있습니다. 다시 시도해주세요.")
        result = json.loads(result_text)
    except Exception as e:
        raise Exception(f"AI 출제 중 오류: {e}") from e
    return {"answer": str(result.get("answer", "")).strip(),
            "hint": str(result.get("hint", "")).strip()}


def answer_user_question(secret: str, qa_history: List[Dict], question: str) -> str:
    """사용자 질문에 AI가 정답에 근거해 답한다. 예/아니오/애매함/모호한 질문 중 하나만 반환."""
    client = _get_client()
    history_lines = [f"Q: {qa['question']} → A: {qa['answer']}" for qa in qa_history]
    history_text = "\n".join(history_lines) if history_lines else "(없음)"
    prompt = f"""당신은 스무고개 게임의 출제자입니다. 정답은 '{secret}'입니다.

## 절대 규칙
1. 어떠한 경우에도 정답('{secret}')이나 정답을 직접 유추할 수 있는 단어를 답변에 포함하지 마세요.
2. 사용자가 "이것은 무엇입니까?", "정답이 뭐예요?", "힌트 주세요" 같은 정답을 묻거나 개방형으로 묻는 질문을 하면, 반드시 "질문이 모호함"으로 답하세요.
3. 사용자 질문이 예/아니오로 답할 수 있는 형식이면 정답에 근거해 정직하게 "예" 또는 "아니오"로 답하세요.
4. 예/아니오로 명확히 답하기 애매하면 "애매함"으로 답하세요.
5. 응답은 반드시 아래 네 가지 중 하나의 단어만 포함해야 합니다: 예, 아니오, 애매함, 질문이 모호함

## 지금까지 문답
{history_text}

## 사용자의 새 질문
{question}

JSON 형식으로만 답하세요: {{"answer": "예" 또는 "아니오" 또는 "애매함" 또는 "질문이 모호함"}}"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=1000,
            ),
        )
        result_text = (response.text or "").strip()
        if not result_text:
            return "애매함"
        result = json.loads(result_text)
    except Exception as e:
        raise Exception(f"AI 응답 중 오류: {e}") from e

    raw = str(result.get("answer", "")).strip()
    # 허용된 4가지 답변 외의 응답이 오면 안전한 기본값으로 정규화
    allowed = {"예", "아니오", "애매함", "질문이 모호함"}
    if raw not in allowed:
        # 정답 단어가 섞여 들어온 경우도 방어
        if secret and secret in raw:
            return "질문이 모호함"
        # "Yes/No" 등 영문 응답 대응
        low = raw.lower()
        if low in ("yes", "y", "true"):
            return "예"
        if low in ("no", "n", "false"):
            return "아니오"
        return "애매함"
    return raw


def check_user_guess(secret: str, guess: str) -> bool:
    """사용자의 정답 추측이 맞는지 AI가 판정한다 (동의어/표기차이 허용)."""
    client = _get_client()
    prompt = f"""정답: '{secret}', 사용자 추측: '{guess}'.
같은 대상을 가리키면(동의어·표기차이 포함) 정답입니다.
JSON 형식: {{"correct": true 또는 false}}"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
                max_output_tokens=50,
            ),
        )
        return bool(json.loads(response.text).get("correct", False))
    except Exception:
        return False

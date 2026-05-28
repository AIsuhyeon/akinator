좋아요, .streamlit/config.toml 완료! 이번엔 게임 두뇌인 game.py예요. 긴 코드지만 통째로 복사-붙여넣기만 하면 돼요.
📄 다시 파일 3: services/game.py
GitHub에서 할 일

Add file ▾ → Create new file
파일이름 칸에 정확히:

   services/game.py
→ ⚠️ services/ 로 시작 (점 아님!)
3. 큰 칸에 아래 코드 전체 붙여넣기:
python"""
AI 스무고개 게임 핵심 로직 (Google Gemini 버전)
"""
import json
from typing import Dict, List

import streamlit as st
from google import genai
from google.genai import types


# Gemini 모델 (최신 무료 모델)
MODEL_NAME = "gemini-2.5-flash"

MAX_QUESTIONS = 20


def _get_client() -> genai.Client:
    """Gemini 클라이언트 초기화 (키는 Streamlit secrets에서 읽음)"""
    return genai.Client(api_key=st.secrets["gemini"]["api_key"])


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
        user_prompt += "\n\n⚠️ 질문 기회를 모두 소진했습니다. 반드시 정답을 추측(guess)하세요."
    elif question_count >= MAX_QUESTIONS - 2:
        user_prompt += "\n\n⏰ 질문이 거의 끝나갑니다. 슬슬 추측을 고려하세요."

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.7,
                max_output_tokens=300,
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
        raise ValueError(f"AI 응답 파싱 실패: {e}\n응답: {result_text[:200]}") from e

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
        prompt = f"""당신은 방금 스무고개에서 {len(qa_history)}개의 질문 만에 정답을 맞혔습니다.
승리의 기쁨을 담아 재치있고 짧은 한국어 소감을 한 문장으로 말하세요. (이모지 1개 포함 가능)"""
    else:
        prompt = f"""당신은 스무고개에서 정답을 맞히지 못했습니다.
실제 정답은 '{answer}'였습니다.
아깝게 진 것에 대한 재치있고 깔끔한 한국어 소감을 한 문장으로 말하세요. (이모지 1개 포함 가능)"""

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

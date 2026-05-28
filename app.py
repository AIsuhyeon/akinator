"""
🔮 AI 스무고개 (AI Akinator)
사용자가 머릿속에 무언가를 정하면 AI가 예/아니오 질문으로 맞히는 게임.
"""
from typing import Dict, List

import streamlit as st

from services.game import MAX_QUESTIONS, get_ai_move, get_final_reaction


st.set_page_config(page_title="AI 스무고개", page_icon="🔮", layout="centered")


def _init_state() -> None:
    defaults = {
        "phase": "start",
        "qa_history": [],
        "current_move": None,
        "result": None,
        "final_answer": "",
        "ai_reaction": "",
        "last_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


def _question_number() -> int:
    return len(st.session_state.qa_history)


def _start_game() -> None:
    st.session_state.phase = "playing"
    st.session_state.qa_history = []
    st.session_state.result = None
    st.session_state.final_answer = ""
    st.session_state.ai_reaction = ""
    st.session_state.last_error = None
    _generate_next_move()


def _generate_next_move() -> None:
    force = _question_number() >= MAX_QUESTIONS - 1
    try:
        with st.spinner("🤔 AI가 생각하는 중..."):
            move = get_ai_move(st.session_state.qa_history, force_guess=force)
        st.session_state.current_move = move
        st.session_state.last_error = None
    except Exception as e:
        st.session_state.current_move = None
        st.session_state.last_error = str(e)


def _answer_question(answer: str) -> None:
    move = st.session_state.current_move
    if not move:
        return
    st.session_state.qa_history.append({"question": move["content"], "answer": answer})
    _generate_next_move()


def _handle_guess_correct() -> None:
    move = st.session_state.current_move
    st.session_state.qa_history.append({"question": f"[추측] {move['content']}", "answer": "정답!"})
    st.session_state.result = "win"
    st.session_state.phase = "result"
    try:
        st.session_state.ai_reaction = get_final_reaction(won=True, qa_history=st.session_state.qa_history)
    except Exception:
        st.session_state.ai_reaction = "맞혔다! 🎉"


def _handle_guess_wrong() -> None:
    move = st.session_state.current_move
    st.session_state.qa_history.append({"question": f"[추측] {move['content']}", "answer": "땡! 틀렸어요"})
    if _question_number() >= MAX_QUESTIONS:
        st.session_state.result = "lose"
        st.session_state.phase = "result"
    else:
        _generate_next_move()


def _finish_as_lose() -> None:
    st.session_state.result = "lose"
    st.session_state.phase = "result"


def render_start() -> None:
    st.title("🔮 AI 스무고개")
    st.markdown("#### AI가 당신의 마음속 정답을 맞혀봅니다")
    st.write("")
    st.markdown(
        """
        **게임 방법**
        1. 머릿속으로 **무언가 하나**를 정하세요 (사물, 동물, 인물, 장소 등)
        2. AI가 **예/아니오 질문**을 던집니다 (최대 20개)
        3. 솔직하게 답해주세요
        4. AI가 **정답을 맞히면 AI 승리**, 20개 안에 못 맞히면 **당신 승리!**
        """
    )
    st.info("💡 예시: '사과', '강아지', '에펠탑', '아인슈타인', '축구공' 등 누구나 아는 것으로 정해보세요.")
    st.write("")
    if st.button("🎮 게임 시작", type="primary", use_container_width=True):
        _start_game()
        st.rerun()


def render_playing() -> None:
    move = st.session_state.current_move
    asked = _question_number()
    st.markdown("### 🔮 AI 스무고개")
    st.progress(min(asked / MAX_QUESTIONS, 1.0), text=f"질문 {asked} / {MAX_QUESTIONS}")

    if move is None:
        st.warning("AI 응답을 불러오지 못했습니다. 다시 시도해주세요.")
        if st.session_state.get("last_error"):
            with st.expander("🔍 오류 상세 내용 보기 (문제 해결용)", expanded=True):
                st.code(st.session_state.last_error, language="text")
        if st.button("🔄 다시 시도"):
            _generate_next_move()
            st.rerun()
        return

    st.write("")

    if move["type"] == "question":
        with st.container(border=True):
            st.markdown(f"#### 🤖 질문 {asked + 1}")
            st.markdown(f"## {move['content']}")
        st.write("")
        st.markdown("##### 당신의 대답은?")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("⭕ 예", use_container_width=True, type="primary"):
                _answer_question("예")
                st.rerun()
        with c2:
            if st.button("❌ 아니오", use_container_width=True):
                _answer_question("아니오")
                st.rerun()
        with c3:
            if st.button("🤷 애매해요", use_container_width=True):
                _answer_question("애매함/부분적으로 그렇다")
                st.rerun()
        with c4:
            if st.button("❓ 모르겠어요", use_container_width=True):
                _answer_question("모르겠음")
                st.rerun()
    else:
        with st.container(border=True):
            st.markdown("#### 🤖 AI의 추측!")
            st.markdown(f"## 혹시... **{move['content']}** 인가요?")
        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🎯 정답이에요!", use_container_width=True, type="primary"):
                _handle_guess_correct()
                st.rerun()
        with c2:
            if st.button("🙅 아니에요", use_container_width=True):
                _handle_guess_wrong()
                st.rerun()

    st.write("")
    with st.expander(f"📜 지금까지의 문답 ({asked}개)"):
        if st.session_state.qa_history:
            for i, qa in enumerate(st.session_state.qa_history, start=1):
                st.markdown(f"**{i}. {qa['question']}**")
                st.caption(f"→ {qa['answer']}")
        else:
            st.caption("아직 답한 질문이 없어요.")

    if st.button("🏳️ 홈으로 돌아가기"):
        _finish_as_lose()
        st.rerun()


def render_result() -> None:
    result = st.session_state.result
    asked = _question_number()
    st.markdown("### 🔮 AI 스무고개")
    st.write("")

    if result == "win":
        st.balloons()
        st.success(f"## 🤖 AI 승리! ({asked}개 질문 만에 정답)")
        if st.session_state.ai_reaction:
            st.markdown(f"> 💬 {st.session_state.ai_reaction}")
    else:
        st.markdown("## 🎉 당신의 승리!")
        st.markdown("AI가 20개 안에 맞히지 못했어요. 어려운 답을 생각하셨네요!")
        if not st.session_state.final_answer:
            answer = st.text_input("정답이 무엇이었나요? (입력하면 AI가 소감을 남겨요)", placeholder="예: 양자컴퓨터")
            if st.button("AI에게 정답 알려주기"):
                if answer.strip():
                    st.session_state.final_answer = answer.strip()
                    try:
                        st.session_state.ai_reaction = get_final_reaction(
                            won=False, qa_history=st.session_state.qa_history, answer=answer.strip()
                        )
                    except Exception:
                        st.session_state.ai_reaction = "아쉽네요, 다음엔 꼭 맞힐게요!"
                    st.rerun()
        else:
            st.markdown(f"**정답: {st.session_state.final_answer}**")
            if st.session_state.ai_reaction:
                st.markdown(f"> 💬 {st.session_state.ai_reaction}")

    st.write("")
    with st.expander(f"📜 전체 문답 다시보기 ({asked}개)", expanded=False):
        for i, qa in enumerate(st.session_state.qa_history, start=1):
            st.markdown(f"**{i}. {qa['question']}**")
            st.caption(f"→ {qa['answer']}")

    st.write("")
    if st.button("🔄 다시 하기", type="primary", use_container_width=True):
        st.session_state.phase = "start"
        st.session_state.current_move = None
        st.rerun()


phase = st.session_state.phase
if phase == "start":
    render_start()
elif phase == "playing":
    render_playing()
else:
    render_result()

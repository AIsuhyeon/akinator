"""
🔮 AI 스무고개 (AI Akinator)
모드 1: AI가 맞히기 / 모드 2: AI가 문제 내기
"""
from typing import Dict, List

import streamlit as st

from services.game import (
    MAX_QUESTIONS,
    get_ai_move,
    get_final_reaction,
    start_host_game,
    answer_user_question,
    check_user_guess,
)


st.set_page_config(
    page_title="AI 스무고개",
    page_icon="🔮",
    layout="centered",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "🔮 AI 스무고개 — 회사 AI 과제 제출용 데모",
    },
)

# 우측 상단 툴바(Share/GitHub) 및 하단 푸터 숨기기
st.markdown(
    """
    <style>
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _init_state() -> None:
    defaults = {
        "mode": None,            # "ai_guess" | "ai_host"
        "phase": "start",
        "qa_history": [],
        "current_move": None,
        "result": None,
        "final_answer": "",
        "ai_reaction": "",
        "last_error": None,
        # 모드 2 전용
        "secret": "",
        "hint": "",
        "host_result": None,     # "win" | "lose" | "lose_guess"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


def _question_number() -> int:
    return len(st.session_state.qa_history)


# ========== 공통: 모드 선택 ==========

def render_mode_select() -> None:
    st.title("🔮 AI 스무고개")
    st.markdown("#### 플레이할 모드를 선택하세요")
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("### 🤖 AI가 맞히기")
            st.caption("당신이 정답을 떠올리면 AI가 질문해서 맞힙니다.")
            if st.button("이 모드로 시작", use_container_width=True, type="primary", key="m1"):
                st.session_state.mode = "ai_guess"
                _start_ai_guess()
                st.rerun()
    with c2:
        with st.container(border=True):
            st.markdown("### 🧑 내가 맞히기")
            st.caption("AI가 정답을 정하면 당신이 질문해서 맞힙니다.")
            if st.button("이 모드로 시작", use_container_width=True, key="m2"):
                st.session_state.mode = "ai_host"
                _start_ai_host()
                st.rerun()


# ========== 모드 1: AI가 맞히기 ==========

def _start_ai_guess() -> None:
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


def render_ai_guess_playing() -> None:
    move = st.session_state.current_move
    asked = _question_number()
    st.markdown("### 🤖 AI가 맞히기")
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

    st.write("")
    if st.button("🏳️ 포기하기", key="guess_giveup"):
        _finish_as_lose()
        st.rerun()


def render_ai_guess_result() -> None:
    result = st.session_state.result
    asked = _question_number()
    st.markdown("### 🤖 AI가 맞히기")
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


# ========== 모드 2: AI가 출제하기 (사람이 맞히기) ==========

def _start_ai_host() -> None:
    st.session_state.phase = "playing"
    st.session_state.qa_history = []
    st.session_state.host_result = None
    st.session_state.secret = ""
    st.session_state.hint = ""
    st.session_state.last_error = None
    try:
        with st.spinner("🤔 AI가 정답을 정하는 중..."):
            data = start_host_game()
        st.session_state.secret = data["answer"]
        st.session_state.hint = data["hint"]
    except Exception as e:
        st.session_state.last_error = str(e)


def render_ai_host_playing() -> None:
    asked = _question_number()
    st.markdown("### 🧑 내가 맞히기")
    st.progress(min(asked / MAX_QUESTIONS, 1.0), text=f"질문 {asked} / {MAX_QUESTIONS}")

    if not st.session_state.secret:
        st.warning("AI가 정답을 정하지 못했습니다. 다시 시도해주세요.")
        if st.session_state.get("last_error"):
            with st.expander("🔍 오류 상세 내용 보기", expanded=True):
                st.code(st.session_state.last_error, language="text")
        if st.button("🔄 다시 시도"):
            _start_ai_host()
            st.rerun()
        return

    st.info(f"💡 힌트: {st.session_state.hint}")
    st.write("")

    with st.container(border=True):
        st.markdown("#### ❓ AI에게 예/아니오 질문하기")
        q = st.text_input("질문 입력", placeholder="예: 그것은 살아있는 생물인가요?", key="user_q")
        if st.button("질문 보내기", type="primary", disabled=(asked >= MAX_QUESTIONS)):
            if q.strip():
                try:
                    with st.spinner("🤔 AI가 답하는 중..."):
                        ans = answer_user_question(st.session_state.secret, st.session_state.qa_history, q.strip())
                    st.session_state.qa_history.append({"question": q.strip(), "answer": ans})
                except Exception as e:
                    st.session_state.last_error = str(e)
                st.rerun()

    if asked >= MAX_QUESTIONS:
        st.warning("질문 20개를 모두 사용했어요! 이제 정답을 입력해보세요.")

    st.write("")

    with st.container(border=True):
        st.markdown("#### 🎯 정답 맞히기")
        guess = st.text_input("정답 입력", placeholder="예: 코끼리", key="user_guess")
        if st.button("정답 제출"):
            if guess.strip():
                with st.spinner("판정 중..."):
                    correct = check_user_guess(st.session_state.secret, guess.strip())
                if correct:
                    st.session_state.host_result = "win"
                    st.session_state.phase = "result"
                else:
                    st.session_state.host_result = "lose_guess"
                    st.session_state.qa_history.append({"question": f"[추측] {guess.strip()}", "answer": "땡!"})
                    if asked >= MAX_QUESTIONS:
                        st.session_state.host_result = "lose"
                        st.session_state.phase = "result"
                st.rerun()

    st.write("")
    with st.expander(f"📜 지금까지의 문답 ({asked}개)"):
        if st.session_state.qa_history:
            for i, qa in enumerate(st.session_state.qa_history, start=1):
                st.markdown(f"**{i}. {qa['question']}**")
                st.caption(f"→ {qa['answer']}")
        else:
            st.caption("아직 질문이 없어요.")

    st.write("")
    if st.button("🏳️ 포기하기", key="host_giveup"):
        st.session_state.host_result = "lose"
        st.session_state.phase = "result"
        st.rerun()


def render_ai_host_result() -> None:
    asked = _question_number()
    st.markdown("### 🧑 내가 맞히기")
    st.write("")
    if st.session_state.host_result == "win":
        st.balloons()
        st.success("## 🎉 정답! 당신의 승리!")
        st.markdown(f"정답은 **{st.session_state.secret}** 였습니다. ({asked}개 질문 사용)")
    else:
        st.markdown("## 🤖 AI 승리!")
        st.markdown(f"아쉽네요! 정답은 **{st.session_state.secret}** 였습니다.")

    st.write("")
    with st.expander(f"📜 전체 문답 다시보기 ({asked}개)", expanded=False):
        for i, qa in enumerate(st.session_state.qa_history, start=1):
            st.markdown(f"**{i}. {qa['question']}**")
            st.caption(f"→ {qa['answer']}")


# ========== 공통 종료/라우팅 ==========

def _reset_to_home() -> None:
    st.session_state.mode = None
    st.session_state.phase = "start"
    st.session_state.current_move = None
    st.session_state.host_result = None
    st.session_state.qa_history = []
    st.session_state.secret = ""
    st.session_state.hint = ""


mode = st.session_state.mode
phase = st.session_state.phase

if mode is None:
    render_mode_select()
elif mode == "ai_guess":
    if phase == "playing":
        render_ai_guess_playing()
    else:
        render_ai_guess_result()
elif mode == "ai_host":
    if phase == "playing":
        render_ai_host_playing()
    else:
        render_ai_host_result()

# 🏠 홈 버튼 — 모드 선택 화면이 아니면 항상 노출
if mode is not None:
    st.write("")
    st.divider()
    if st.button("🏠 홈으로", key="global_home"):
        _reset_to_home()
        st.rerun()

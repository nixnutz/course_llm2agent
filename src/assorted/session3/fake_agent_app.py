"""Fake agent UI mock built with Streamlit.

Pure UI prototype: only the Chaos slider is interactive (without side
effects). Prompt input and Send button are intentionally inert. The
"Thinking" block holds placeholder text for ~4 agents that will be filled
in later by the user.

Run via the make target from the repository root:

    make streamlit-run

Override defaults if needed:

    make streamlit-run STREAMLIT_PORT=8502
"""

from __future__ import annotations

import streamlit as st


AgentThought = tuple[str, str]

AGENT_THOUGHTS: list[AgentThought] = [
    ("Agent 1", "TODO - text to be provided"),
    ("Agent 2", "TODO - text to be provided"),
    ("Agent 3", "TODO - text to be provided"),
    ("Agent 4", "TODO - text to be provided"),
]


def render_chat_list() -> None:
    """Empty, scrollable container that will later hold past chats."""
    st.container(height=400, border=True)


def render_thinking_block(agents: list[AgentThought]) -> None:
    """Multi-agent discussion rendered as a gray-on-white panel."""
    rows = "\n".join(
        f"<div><strong>{name}</strong>: {thought}</div>" for name, thought in agents
    )
    st.markdown(
        f"""
        <div style="background:#ffffff;color:#6b7280;
                    border:1px solid #e5e7eb;border-radius:8px;
                    padding:12px 16px;font-style:italic;line-height:1.6;">
            {rows}
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Fake Agent", layout="wide")
    st.title("Fake Agent (UI mock)")

    left, right = st.columns([1, 2], gap="large")

    with left:
        st.subheader("Chaos")
        st.slider("Chaos level", min_value=1, max_value=5, value=1, step=1)

        st.subheader("Past chats")
        render_chat_list()

    with right:
        st.subheader("Prompt")
        st.text_area(
            "Your prompt",
            value="",
            height=160,
            label_visibility="collapsed",
        )
        st.button("Send")

        st.subheader("Thinking")
        render_thinking_block(AGENT_THOUGHTS)


if __name__ == "__main__":
    main()

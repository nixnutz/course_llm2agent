"""L6 chaos exemplars for ``build_parent_base_graph`` (ADR 0011 / ADR 0012).

Not exhaustive: course/WIP. Two minimal ``reset_peer`` cases on chaos-channel
segments A (provider) and B (edge). Toxiproxy state is global — do not run
chaos tests in parallel with xdist unless ``xdist_group("chaos")`` is honored.
"""

import asyncio

import httpx
from langchain_core.messages import HumanMessage
import openai
import pytest

from src.graphs.parent_base_graph import build_parent_base_graph
from src.llm_handle.local import clear_cache, openai_client_context
from src.llm_nodes.global_state import GlobalState
from src.logging_setup import get_logger
from src.reducer.base_reader import BaseReducerReader
from src.reducer.reducer_session import reducer_session
from src.tests_and_evals.common.toxiproxy import (
    PROXY_EDGE_CHAOS,
    PROXY_PROVIDER_CHAOS_OLLAMA,
    ToxiproxyAdmin,
)

# LiteLLM/Caddy may wrap reset_peer as HTTP 500/502 (InternalServerError) or raw connection errors.
_CONNECTION_ERRORS = (
    openai.APIConnectionError,
    openai.InternalServerError,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
)

_HUMAN_MESSAGE = "Contact alice@example.com for details."

logger = get_logger(__name__, __file__)


def make_reader(get_thread_id):
    return BaseReducerReader(get_thread_id=get_thread_id)


@pytest.fixture(scope="module")
def chaos_model_warmed(chaos_test_model):
    """Warm chaos channel once before ``reset_peer`` tests (module scope).

    Why: the first Ollama chat after idle often includes **model-load latency** that
    is unrelated to any Toxiproxy toxic. Latency-based chaos labs (e.g.
    ``session1/chaos.ipynb``) compare a **baseline** request against a toxic run;
    without warmup, the first measured call can look like a false positive or skew
    duration expectations. These L6 exemplars use ``reset_peer`` only (no latency
    assertion — too flaky for CI) but still need a successful pre-flight so failures
    are clearly Library-tier propagation, not cold-start or 502 from an empty proxy
    table.

    A future latency L6 exemplar could extend this fixture to ``yield`` baseline
    seconds for threshold selection; ``reset_peer`` tests ignore timing.
    """
    ToxiproxyAdmin().reset()

    async def _warm() -> None:
        async with openai_client_context(chaos=True, client_cache_policy="none") as client:
            await client.chat.completions.create(
                model=chaos_test_model,
                messages=[{"role": "user", "content": "Say hi briefly."}],
                temperature=0.0,
            )

    asyncio.run(_warm())


async def _run_graph_expect_connection_failure(
    toxiproxy_admin: ToxiproxyAdmin,
    proxy_name: str,
    model: str,
    *,
    thread_id: str,
) -> None:
    await clear_cache()
    toxiproxy_admin.reset()
    toxiproxy_admin.add_reset_peer(proxy_name)

    bundle = build_parent_base_graph(model, chaos=True, client_cache_policy="none")
    state = GlobalState(messages=[HumanMessage(content=_HUMAN_MESSAGE)])

    with reducer_session(thread_id, factory=make_reader) as session:
        with pytest.raises(_CONNECTION_ERRORS) as exc_info:
            await session.ainvoke(bundle.graph, state)
        exc = exc_info.value
        status_code = getattr(exc, "status_code", None)
        logger.info(
            "Library-tier failure proxy=%s exception=%s status_code=%s message=%s",
            proxy_name,
            type(exc).__name__,
            status_code,
            exc,
        )


@pytest.mark.chaos
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group("chaos")
async def test_parent_graph_chaos_provider_reset_peer_aborts(
    chaos_model_warmed,
    toxiproxy_admin,
    chaos_test_model,
):
    await _run_graph_expect_connection_failure(
        toxiproxy_admin,
        PROXY_PROVIDER_CHAOS_OLLAMA,
        chaos_test_model,
        thread_id="chaos-test-provider",
    )


@pytest.mark.chaos
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group("chaos")
async def test_parent_graph_chaos_edge_reset_peer_aborts(
    chaos_model_warmed,
    toxiproxy_admin,
    chaos_test_model,
):
    await _run_graph_expect_connection_failure(
        toxiproxy_admin,
        PROXY_EDGE_CHAOS,
        chaos_test_model,
        thread_id="chaos-test-edge",
    )

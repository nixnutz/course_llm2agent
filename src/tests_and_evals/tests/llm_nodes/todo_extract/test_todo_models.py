"""Tests for ``TODOItem`` / ``TODOList`` / ``TODOState`` (minimal coverage).

Summary:
- Default empty values and ``extra="forbid"`` on ``BaseState``.
- ``TODOState`` defaults for subgraph input/output fields.

Not exhaustive: course/WIP code. Node wiring is covered in ``test_todo_nodes_mock.py``.
"""

from pydantic import ValidationError
import pytest

from src.llm_nodes.todo_extract.models import TODOItem, TODOList, TODOState


@pytest.mark.unit
def test_minimal_defaults():
    item = TODOItem()
    todo_list = TODOList()

    assert item.who == ""
    assert item.what == ""
    assert item.when == ""
    assert todo_list.items == []


@pytest.mark.unit
def test_todo_item_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        TODOItem(who="E0_a1b2c3d4", what="feed the cat", when="today", unexpected=True)


@pytest.mark.unit
def test_todo_list_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        TODOList(items=[], unexpected=True)


@pytest.mark.unit
def test_todo_state_defaults():
    state = TODOState()

    assert state.text == ""
    assert state.placeholder_allowlist.allowed_tokens == ()
    assert state.todo_list == TODOList()
    assert state.messages == []

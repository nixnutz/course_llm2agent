"""L1 exemplars for bash fence extraction (transport-retry path)."""

import pytest

from src.llm_nodes.tool_node_sysbox_bash.script_extract import (
    extract_bash_fence,
    has_bash_fence,
)


_AWK_SCRIPT = """WHAT='buy a cup of coffee'
echo "$WHAT" | awk '{for (i=NF;i>0;i--) printf "%s%s",$i,(i>1?" ":""); print ""}'"""


@pytest.mark.unit
def test_extract_bash_fence_verbatim_awk():
    text = f"```bash\n{_AWK_SCRIPT}\n```"
    assert extract_bash_fence(text) == _AWK_SCRIPT


@pytest.mark.unit
def test_extract_bash_fence_accepts_sh_label():
    text = f"```sh\n{_AWK_SCRIPT}\n```"
    assert extract_bash_fence(text) == _AWK_SCRIPT


@pytest.mark.unit
def test_extract_bash_fence_returns_none_without_fence():
    assert extract_bash_fence("I'll fix the script") is None
    assert has_bash_fence("I'll fix the script") is False


@pytest.mark.unit
def test_has_bash_fence_true_when_present():
    text = f"prefix\n```bash\necho hi\n```\nsuffix"
    assert has_bash_fence(text) is True

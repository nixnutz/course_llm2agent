"""Chat prompts for the tool_node_sysbox_bash llm_with_bash node."""

from langchain_core.prompts import ChatPromptTemplate

BASH_TOOL_GUIDANCE_SNIPPET = """
The ``bash`` tool runs scripts in an isolated sandbox for this graph invoke only.
The environment is stateful within one invoke (files and installs persist across calls).
Scripts are bounded by timeout and stdout/stderr size limits.
Pass only the ``script`` argument. This is a lab setup, not production-grade isolation.
"""

_tool_node_sysbox_bash_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a deterministic TODO markdown generator. Do not chat, explain, or ask questions.

"""
            + BASH_TOOL_GUIDANCE_SNIPPET.strip()
            + """

Input: JSON with ``items`` — each object has ``who``, ``what``, ``when`` (``when`` may be empty).

Lab task (one ``bash`` call per ``items[]`` entry):
- Use a **multi-line** script (newlines between commands). Never cram ``cat <<'EOF'``
  and later ``echo`` sections onto one line with ``;`` — that breaks the heredoc.
- Set ``WHAT='...'`` from the item's ``what`` string, then derive outputs in bash.
- Forbidden: ``echo`` with hardcoded reversed text, word counts, or probe values.
- Forbidden: copying ASCII art or sandbox values from this prompt's examples.

Script skeleton (fill ``WHAT``, ASCII lines, probe command; keep structure):

WHAT='<what from JSON>'
echo '--- reversed ---'
echo "$WHAT" | awk '{{for (i=NF; i>0; i--) printf "%s%s", $i, (i>1 ? " " : ""); print ""}}'
echo '--- word_count ---'
echo "$WHAT" | wc -w | tr -d ' '
echo '--- ascii_art ---'
cat <<'EOF'
<3-8 lines of ASCII art matching WHAT — coffee cup for coffee, tree for tree, etc.>
EOF
echo '--- sandbox_facts ---'
echo 'label=<plain-English name of what you measured>'
echo "value=$(<one live command>)"

Stdout sections (labels required): ``--- reversed ---``, ``--- word_count ---``,
``--- ascii_art ---``, ``--- sandbox_facts ---`` (with ``label=`` and ``value=`` lines).
- Pick a **different** sandbox probe per item (no repeated ``label`` in one invoke).
  Examples: ``date -u +%Y-%m-%dT%H:%M:%SZ``, ``uname -sr``, ``uname -r``, ``hostname``,
  ``whoami``, ``pwd``, ``awk '{{print int($1)}}' /proc/uptime``,
  ``awk '/VmRSS/ {{print $2}}' /proc/self/status``, ``echo $$``, ``nproc``,
  ``cat /proc/loadavg``, ``df -h /sandbox | tail -1``.
- Build bullet: ``- [ ] <reversed> (<word_count> words) (by <when or today>)``.
- Under each bullet, a 4-space-indented fenced code block with:
  (1) ``ascii_art`` from stdout, blank line, (2) ``sandbox probe — <label>: <value>``.
- One ``# <who>`` section per unique ``who``; copy ``who`` exactly from JSON.

After each tool call, read **ToolMessage** stdout only. If stderr mentions heredoc
warnings or stdout contains literal ``EOF;`` text, the script was wrong — fix and rerun.
Never paste example timestamps or kernel versions from this prompt into output.
On tool failure, write a sensible bullet under the correct ``# <who>`` without inventing data.

Truth rules:
- ``# <who>`` tokens must match JSON exactly (needed for placeholder audit).
- You may reformulate or merge ``what`` text in bullets; trusted finalize checks ``who`` only.

Output shape (markdown only, no preamble):

Example input (illustration only — do not copy tokens into real output):
{{"items": [{{"who": "E0_abc123", "what": "plant a tree", "when": "tomorrow"}}, {{"who": "E0_abc123", "what": "buy milk", "when": "today"}}]}}

Example output:

# E0_abc123
- [ ] tree a plant (3 words) (by tomorrow)
  ```
       |
      /|\\
     / | \\
    |  |  |

  sandbox probe — UTC clock inside the container: <from ToolMessage value= line>
  ```
- [ ] milk buy (2 words) (by today)
  ```
    ( o )
     | |

  sandbox probe — RSS memory of this bash process (kB): <from ToolMessage value= line>
  ```
            """,
        ),
        ("user", "{input}"),
    ]
)

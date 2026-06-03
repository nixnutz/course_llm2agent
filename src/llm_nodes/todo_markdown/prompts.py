"""Chat prompts for the TODO list extraction node."""

from langchain_core.prompts import ChatPromptTemplate

_todo_markdown_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a deterministic TODO list generator. Do not chat, explain, or fix spelling.

Task: Generate a TODO list in Markdown format from the given TODO list items. Items are given in JSON format as list of JSON objects.
Each JSON object has keys "who", "what", "when".

Who: person or masked-email token (e.g. E0_a1b2c3d4 for placeholder E{{n}}_{{salt}}) tasked with the action. If unclear, "UNKNOWN".
What: action to be performed.
When: deadline if stated. If unclear, "UNKNOWN".

Output: page in markdown format with the TODO list items. For each "who" create a new section with the "who" as the section title. 
In the section, list the "what" items for the "who" with the "when" as the item text. Use the following format:

- [ ] <what> (by <when>)

If the "when" is not stated, use "today" as the deadline.

Example input:
{{"items": [{{"who": "E0_a1b2c3d4", "what": "feed the cat", "when": "today"}}, {{"who": "Bob", "what": "feed the cat", "when": "today"}}]}}
Example output:
# E0_a1b2c3d4
- [ ] feed the cat (by today)

# Bob
- [ ] feed the cat (by today)
            """,
        ),
        ("user", "{input}"),
    ]
)

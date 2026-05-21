# Course notebooks (`src/assorted`)

Run with the **dev container** kernel (see `container/compose/README.md`).

If a notebook imports shared code under `src/` (e.g. `src.reducer`), run this once in the first code cell:

```python
import sys
sys.path.insert(0, "/workspace")
```

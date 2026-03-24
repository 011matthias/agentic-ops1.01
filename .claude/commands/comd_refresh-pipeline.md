---
description: Regenerate spec-data.js for the spec pipeline dashboard from live spec files
---

# Refresh Spec Pipeline

Regenerate `workspace/playgrounds/spec-data.js` by scanning all client spec folders and parsing YAML frontmatter.

## Steps

1. Run the generator:

```bash
uv run workspace/playgrounds/generate-spec-data.py
```

2. Report the output (clients found, total specs, any warnings about files with missing frontmatter).

3. Remind the user to reload `spec-pipeline.html` in the browser to see the updated data.

"""
CV Parser Sub-agent.

Extracts skills, experience, and profile from CV text.
Returns COMPACT output to minimize token usage.
"""

CV_PARSER_PROMPT = """You are a CV parser. Extract a COMPACT structured profile.

## Output Format (JSON only, no explanation)
```json
{
    "skills": ["Python", "ML", "PyTorch"],
    "experience_years": 2,
    "titles": ["ML Engineer", "Research Assistant"],
    "summary": "ML researcher with Python/PyTorch, focus on healthcare AI"
}
```

## Rules
- List TOP 10 skills only (most relevant for job search)
- Summary: MAX 30 words
- Titles: MAX 3 recent roles
- Infer skills from context (e.g., "managed team" → add "Leadership")
- Return ONLY the JSON, no other text
"""


def get_cv_parser_config() -> dict:
    """Get CV parser sub-agent config (token-optimized)."""
    return {
        "name": "cv-parser",
        "description": "Extract compact profile from CV. Returns JSON with skills, experience, titles, summary.",
        "system_prompt": CV_PARSER_PROMPT,
        "tools": [],
    }

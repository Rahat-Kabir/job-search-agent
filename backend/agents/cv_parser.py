"""
CV Parser Sub-agent.

Extracts skills, experience, and profile from CV text.
Returns COMPACT output to minimize token usage.
"""

CV_PARSER_PROMPT = """You are a CV parser. Extract a COMPACT structured profile.

Return ONLY this JSON (no markdown, no explanation, no extra text):
{"skills": ["skill1", "skill2"], "experience_years": N, "titles": ["role1"], "summary": "brief bio"}

Rules:
- skills: TOP 10 only, most job-relevant
- experience_years: integer (estimate if unclear)
- titles: MAX 3 recent roles
- summary: MAX 30 words
- Output raw JSON only - no ```json blocks, no prose
"""


def get_cv_parser_config() -> dict:
    """Get CV parser sub-agent config (token-optimized)."""
    return {
        "name": "cv-parser",
        "description": "Extract compact profile from CV. Returns JSON with skills, experience, titles, summary.",
        "system_prompt": CV_PARSER_PROMPT,
        "tools": [],
    }

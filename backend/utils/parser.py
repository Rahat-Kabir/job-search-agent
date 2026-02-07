"""
Robust JSON parser with multiple extraction strategies.

Handles various AI output formats:
- Clean JSON
- JSON in ```json blocks
- JSON in ```blocks (no language tag)
- JSON mixed with text
- Markdown formatted responses (fallback)
"""

import json
import re
from typing import Any


def extract_json(text: str, expect_array: bool = False) -> dict | list | None:
    """
    Extract JSON from AI response using multiple strategies.

    Args:
        text: Raw AI response text
        expect_array: If True, expect a JSON array; if False, expect object

    Returns:
        Parsed JSON (dict or list) or None if extraction fails
    """
    if not text or not text.strip():
        return None

    strategies = [
        _try_clean_json,
        _try_fenced_json,
        _try_fenced_any,
        _try_find_json_bounds,
        _try_line_by_line,
    ]

    for strategy in strategies:
        result = strategy(text)
        if result is not None:
            # Validate type matches expectation
            if expect_array and isinstance(result, list):
                return result
            if not expect_array and isinstance(result, dict):
                return result
            # Type mismatch but valid JSON - might still be useful
            if result:
                return result

    return None


def _try_clean_json(text: str) -> dict | list | None:
    """Try parsing the entire text as JSON."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def _try_fenced_json(text: str) -> dict | list | None:
    """Extract JSON from ```json ... ``` blocks."""
    pattern = r"```json\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    return None


def _try_fenced_any(text: str) -> dict | list | None:
    """Extract JSON from ``` ... ``` blocks (any language or none)."""
    pattern = r"```(?:\w*)\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, text)

    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    return None


def _try_find_json_bounds(text: str) -> dict | list | None:
    """Find JSON by matching brackets/braces."""
    # Try to find array first
    array_start = text.find('[')
    if array_start != -1:
        result = _extract_balanced(text, array_start, '[', ']')
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

    # Try object
    obj_start = text.find('{')
    if obj_start != -1:
        result = _extract_balanced(text, obj_start, '{', '}')
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

    return None


def _extract_balanced(text: str, start: int, open_char: str, close_char: str) -> str | None:
    """Extract balanced brackets/braces starting from position."""
    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def _try_line_by_line(text: str) -> dict | list | None:
    """Try to find JSON by joining lines that look like JSON."""
    lines = text.split('\n')
    json_lines = []
    in_json = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('{', '[')) and not in_json:
            in_json = True
            json_lines = [line]
        elif in_json:
            json_lines.append(line)
            if stripped.endswith(('}', ']')):
                try:
                    return json.loads('\n'.join(json_lines))
                except json.JSONDecodeError:
                    # Keep trying
                    pass

    return None


def parse_profile_response(text: str) -> dict:
    """
    Parse CV profile from AI response.

    Returns dict with: skills, experience_years, titles, summary
    """
    # Try JSON extraction first
    result = extract_json(text, expect_array=False)
    if isinstance(result, dict):
        return _normalize_profile(result)

    # Fallback: parse markdown format
    return _parse_profile_markdown(text)


def _normalize_profile(data: dict) -> dict:
    """Normalize profile data to expected schema."""
    return {
        "skills": data.get("skills", [])[:10],  # Max 10 skills
        "experience_years": data.get("experience_years") or data.get("years") or data.get("exp"),
        "titles": data.get("titles", []) or data.get("job_titles", []) or data.get("roles", []),
        "summary": data.get("summary", "") or data.get("bio", "") or data.get("description", ""),
    }


def _parse_profile_markdown(text: str) -> dict:
    """Fallback: parse markdown formatted profile."""
    result = {"skills": [], "experience_years": None, "titles": [], "summary": ""}

    # Skills: **Skills:** or - Skills: or Skills:
    skills_patterns = [
        r"\*\*Skills?:\*\*\s*([^\n*]+)",
        r"[-•]\s*Skills?:\s*([^\n]+)",
        r"Skills?:\s*([^\n]+)",
    ]
    for pattern in skills_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            skills_str = match.group(1).strip()
            result["skills"] = [s.strip() for s in re.split(r'[,;]', skills_str) if s.strip()]
            break

    # Experience years
    exp_patterns = [
        r"\*\*Experience:\*\*\s*~?(\d+)",
        r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
        r"experience[:\s]+~?(\d+)",
    ]
    for pattern in exp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["experience_years"] = int(match.group(1))
            break

    # Titles
    titles_patterns = [
        r"\*\*Titles?:\*\*\s*([^\n*]+)",
        r"[-•]\s*Titles?:\s*([^\n]+)",
        r"(?:Job\s*)?Titles?:\s*([^\n]+)",
    ]
    for pattern in titles_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            titles_str = match.group(1).strip()
            result["titles"] = [t.strip() for t in re.split(r'[,;]', titles_str) if t.strip()]
            break

    # Summary
    summary_patterns = [
        r"\*\*Summary:\*\*\s*([^\n]+)",
        r"[-•]\s*Summary:\s*([^\n]+)",
        r"Summary:\s*([^\n]+)",
    ]
    for pattern in summary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["summary"] = match.group(1).strip()
            break

    return result


def parse_jobs_response(text: str) -> list[dict]:
    """
    Parse job results from AI response.

    Returns list of dicts with: title, company, score, reason, url, location
    """
    # Try JSON extraction first
    result = extract_json(text, expect_array=True)
    if isinstance(result, list):
        jobs = [_normalize_job(job) for job in result if isinstance(job, dict)]
        # Filter: valid jobs must have URL or meaningful company
        return [j for j in jobs if j.get("url") or (j.get("company") and j["company"] != "Unknown")]

    # Fallback: parse markdown format
    jobs = _parse_jobs_markdown(text)
    # Filter: valid jobs must have URL or meaningful company
    return [j for j in jobs if j.get("url") or (j.get("company") and j["company"] != "Unknown")]


def parse_job_details_response(text: str) -> list[dict]:
    """
    Parse enriched job details from detail-scraper response.

    Returns list of dicts with: url, salary, description, requirements, benefits
    """
    result = extract_json(text, expect_array=True)
    if isinstance(result, list):
        return [_normalize_job_details(d) for d in result if isinstance(d, dict)]
    return []


def _normalize_job_details(data: dict) -> dict:
    """Normalize enriched job detail data."""
    return {
        "url": data.get("url", ""),
        "salary": data.get("salary"),
        "description": data.get("description", ""),
        "requirements": data.get("requirements", []),
        "benefits": data.get("benefits", []),
        "apply_url": data.get("apply_url", ""),
    }


def _normalize_job(data: dict) -> dict:
    """Normalize job data to expected schema."""
    # Handle various score formats
    score = data.get("score", 0)
    if isinstance(score, str):
        score_match = re.search(r'\d+', score)
        score = int(score_match.group()) if score_match else 0

    return {
        "title": data.get("title", "") or data.get("job_title", "") or data.get("position", ""),
        "company": data.get("company", "") or data.get("company_name", "") or data.get("employer", ""),
        "score": score,
        "reason": data.get("reason", "") or data.get("match_reason", "") or data.get("why", ""),
        "url": data.get("url", "") or data.get("link", "") or data.get("posting_url", ""),
        "location": _normalize_location(data.get("location", "")),
    }


def _normalize_location(loc: Any) -> str:
    """Normalize location to: remote, onsite, hybrid, or unknown."""
    if not loc:
        return "unknown"

    loc_str = str(loc).lower()
    if "remote" in loc_str:
        return "remote"
    if "hybrid" in loc_str:
        return "hybrid"
    if "onsite" in loc_str or "on-site" in loc_str or "office" in loc_str:
        return "onsite"
    return "unknown"


def _parse_jobs_markdown(text: str) -> list[dict]:
    """Fallback: parse markdown formatted job results."""
    results = []

    # Split by numbered items: 1. **Title** or ### 1. Title
    job_blocks = re.split(r'\n(?:\d+[\.\)]\s+\*\*|###?\s*\d+)', text)

    for block in job_blocks[1:]:  # Skip first empty split
        job = _parse_single_job_markdown(block)
        if job.get("title"):
            results.append(job)

    # If numbered split didn't work, try bullet points
    if not results:
        job_blocks = re.split(r'\n[-•]\s+\*\*', text)
        for block in job_blocks[1:]:
            job = _parse_single_job_markdown(block)
            if job.get("title"):
                results.append(job)

    return results


def _parse_single_job_markdown(block: str) -> dict:
    """Parse a single job from markdown block."""
    job: dict[str, Any] = {}

    # Title extraction patterns
    title_line = block.split('\n')[0]

    # Pattern: Title** at Company (Score: XX%)
    m = re.match(r"([^*]+)\*\*\s*(?:at\s+([^(]+))?\s*\(Score:\s*(\d+)", title_line)
    if m:
        job["title"] = m.group(1).strip()
        if m.group(2):
            job["company"] = m.group(2).strip()
        job["score"] = int(m.group(3))
    else:
        # Pattern: Title** - Company
        m = re.match(r"([^*]+)\*\*\s*[-–]\s*(.+)", title_line)
        if m:
            job["title"] = m.group(1).strip()
            job["company"] = m.group(2).strip()
        else:
            # Pattern: Just Title**
            m = re.match(r"([^*]+)\*\*", title_line)
            if m:
                job["title"] = m.group(1).strip()

    # Score from separate line
    if "score" not in job:
        score_match = re.search(r"Score:\s*(\d+)", block)
        if score_match:
            job["score"] = int(score_match.group(1))

    # Company from separate line
    if "company" not in job:
        company_match = re.search(r"Company:\s*([^\n]+)", block)
        if company_match:
            job["company"] = company_match.group(1).strip()

    # Reason/Match
    reason_patterns = [
        r"(?:Match|Reason|Why):\s*([^\n]+)",
        r"[-•]\s*(?:Match|Reason):\s*([^\n]+)",
    ]
    for pattern in reason_patterns:
        match = re.search(pattern, block, re.IGNORECASE)
        if match:
            job["reason"] = match.group(1).strip()
            break

    # URL - markdown link or plain
    url_match = re.search(r"\]\((https?://[^\)]+)\)", block)
    if url_match:
        job["url"] = url_match.group(1)
    else:
        url_match = re.search(r"(?:URL|Link)?:?\s*(https?://[^\s\)]+)", block)
        if url_match:
            job["url"] = url_match.group(1).rstrip('.,;')

    # Location
    job["location"] = "unknown"
    if re.search(r"\bremote\b", block, re.IGNORECASE):
        job["location"] = "remote"
    elif re.search(r"\bhybrid\b", block, re.IGNORECASE):
        job["location"] = "hybrid"
    elif re.search(r"\b(?:onsite|on-site|office)\b", block, re.IGNORECASE):
        job["location"] = "onsite"

    # Set defaults
    job.setdefault("title", "")
    job.setdefault("company", "Unknown")
    job.setdefault("score", 0)
    job.setdefault("reason", "")
    job.setdefault("url", "")

    return job

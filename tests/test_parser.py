"""Tests for backend.utils.parser — JSON extraction and profile/job normalization."""

import json

from backend.utils.parser import (
    _normalize_location,
    extract_json,
    parse_profile_response,
)


class TestExtractJson:
    def test_clean_json_object(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_fenced_json_block(self):
        text = '```json\n{"skills": ["Python", "SQL"]}\n```'
        assert extract_json(text) == {"skills": ["Python", "SQL"]}

    def test_empty_input_returns_none(self):
        assert extract_json("") is None
        assert extract_json("   ") is None
        assert extract_json(None) is None


class TestParseProfileResponse:
    def test_valid_json_profile(self):
        raw = (
            '{"skills": ["Python", "Docker"], "experience_years": 5,'
            ' "titles": ["Backend Dev"], "summary": "Senior backend engineer"}'
        )
        result = parse_profile_response(raw)
        assert result["skills"] == ["Python", "Docker"]
        assert result["experience_years"] == 5
        assert result["titles"] == ["Backend Dev"]
        assert "backend" in result["summary"].lower()

    def test_skills_capped_at_ten(self):
        skills = [f"skill{i}" for i in range(15)]
        raw = json.dumps({"skills": skills, "experience_years": 1, "titles": [], "summary": "x"})
        result = parse_profile_response(raw)
        assert len(result["skills"]) == 10


class TestNormalizeLocation:
    def test_remote(self):
        assert _normalize_location("Remote OK") == "remote"

    def test_hybrid(self):
        assert _normalize_location("Hybrid - 2 days office") == "hybrid"

    def test_onsite(self):
        assert _normalize_location("On-site in NYC") == "onsite"

    def test_empty_returns_unknown(self):
        assert _normalize_location("") == "unknown"
        assert _normalize_location(None) == "unknown"

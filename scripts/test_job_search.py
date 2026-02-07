"""
CLI test for job search with 15-job limit + SummarizationMiddleware + Memory.

Tests the full pipeline:
1. Create orchestrator with new middleware
2. Send a profile
3. Trigger job search
4. Auto-approve HITL interrupts
5. Verify we get more jobs than before (target: 10-15)

Usage:
    uv run python scripts/test_job_search.py
"""

import json
import sys
import time

from langgraph.types import Command


def main():
    print("=" * 60)
    print("Job Search Agent — CLI Test (Step 1: 15 jobs + Summarization)")
    print("=" * 60)

    # Step 1: Import and create agent
    print("\n[1/5] Creating orchestrator with SummarizationMiddleware + Memory...")
    t0 = time.time()

    from langgraph.checkpoint.memory import MemorySaver

    from backend.agents.orchestrator import create_orchestrator

    checkpointer = MemorySaver()
    agent = create_orchestrator(checkpointer=checkpointer)

    print(f"  Agent created in {time.time() - t0:.1f}s")

    config = {"configurable": {"thread_id": "cli-test-001"}}

    # Step 2: Send a mock profile
    print("\n[2/5] Sending profile to agent...")
    profile_msg = """Here's my background:
Skills: Python, FastAPI, React, TypeScript, PostgreSQL, Docker, AWS, LangChain
Experience: 5 years as a full-stack developer
Recent Roles: Senior Software Engineer, Backend Developer
Looking for: Remote software engineering positions"""

    t0 = time.time()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": profile_msg}]},
        config=config,
    )
    elapsed = time.time() - t0

    response_msgs = result.get("messages", [])
    agent_reply = getattr(response_msgs[-1], "content", "") if response_msgs else ""
    print(f"  Agent replied in {elapsed:.1f}s")
    print(f"  Response preview: {agent_reply[:200]}...")

    # Check if agent already returned jobs in step 2
    from backend.utils.parser import parse_jobs_response as _early_parse

    early_jobs = _early_parse(agent_reply)
    if early_jobs and len(early_jobs) >= 5:
        print(f"\n  Agent already found {len(early_jobs)} jobs in profile response!")
        print("  Skipping explicit search request (agent was proactive).")
        # Use this result directly
    else:
        # Step 3: Trigger job search explicitly
        print("\n[3/5] Requesting job search...")
        t0 = time.time()
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "Yes, search for jobs matching my profile"}]},
            config=config,
        )
        elapsed = time.time() - t0
        print(f"  Agent responded in {elapsed:.1f}s")

    # Step 4: Auto-approve HITL interrupts
    interrupt_count = 0
    while "__interrupt__" in result and len(result["__interrupt__"]) > 0:
        interrupt_count += 1
        interrupt = result["__interrupt__"][0]
        value = getattr(interrupt, "value", interrupt) if not isinstance(interrupt, dict) else interrupt
        print(f"\n[4/5] HITL Interrupt #{interrupt_count}: {value}")
        print("  Auto-approving...")

        t0 = time.time()
        result = agent.invoke(
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
        )
        elapsed = time.time() - t0
        print(f"  Resumed in {elapsed:.1f}s")

    if interrupt_count == 0:
        print("\n[4/5] No HITL interrupts (agent proceeded directly)")

    # Step 5: Parse and display results
    print("\n[5/5] Parsing results...")
    response_msgs = result.get("messages", [])

    # Collect jobs from ALL assistant messages (agent may spread across messages)
    from backend.utils.parser import parse_jobs_response

    all_jobs = []
    seen_titles = set()
    for msg in response_msgs:
        content = getattr(msg, "content", "")
        if not content:
            continue
        parsed = parse_jobs_response(content)
        for job in parsed:
            # Dedup by normalized title (ignore company since markdown fallback sets "Unknown")
            title_key = job.get("title", "").lower().strip()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                all_jobs.append(job)

    jobs = all_jobs
    last_content = getattr(response_msgs[-1], "content", "") if response_msgs else ""
    print(f"  Last message length: {len(last_content)} chars")
    print(f"  Total messages scanned: {len(response_msgs)}")
    print(f"  Unique jobs found across all messages: {len(jobs)}")

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {len(jobs)} jobs found")
    print(f"{'=' * 60}")

    if jobs:
        for i, job in enumerate(jobs, 1):
            score = job.get("score", 0)
            title = job.get("title", "Unknown")
            company = job.get("company", "Unknown")
            location = job.get("location", "unknown")
            reason = job.get("reason", "")
            url = job.get("url", "")

            # Color code by score
            if score >= 80:
                indicator = "+++"
            elif score >= 60:
                indicator = " ++"
            else:
                indicator = "  +"

            print(f"\n  {indicator} [{score:3d}%] {title}")
            print(f"        Company:  {company}")
            print(f"        Location: {location}")
            print(f"        Reason:   {reason}")
            if url:
                print(f"        URL:      {url}")

        # Summary stats
        scores = [j.get("score", 0) for j in jobs]
        avg_score = sum(scores) / len(scores) if scores else 0
        locations = {}
        for j in jobs:
            loc = j.get("location", "unknown")
            locations[loc] = locations.get(loc, 0) + 1

        print(f"\n{'=' * 60}")
        print(f"STATS")
        print(f"  Total jobs:     {len(jobs)}")
        print(f"  Avg score:      {avg_score:.0f}%")
        print(f"  Score range:    {min(scores)}-{max(scores)}%")
        print(f"  Locations:      {json.dumps(locations)}")
        print(f"  Target met:     {'YES' if len(jobs) >= 10 else 'NO'} (target: >= 10)")
        print(f"{'=' * 60}")
    else:
        print("\n  No jobs parsed from response.")
        print(f"  Raw response:\n{last_content[:500]}")

    # Verdict
    if len(jobs) >= 10:
        print("\nVERDICT: PASS — Got 10+ jobs!")
        return 0
    elif len(jobs) >= 5:
        print(f"\nVERDICT: PARTIAL — Got {len(jobs)} jobs (target was 10+)")
        return 0
    else:
        print(f"\nVERDICT: NEEDS WORK — Only got {len(jobs)} jobs")
        return 1


if __name__ == "__main__":
    sys.exit(main())

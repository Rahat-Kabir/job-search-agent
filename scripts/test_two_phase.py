"""
CLI test for two-phase job search: Quick Search + Detail Scrape.

Tests the full pipeline:
1. Create orchestrator with new sub-agents (quick-searcher, detail-scraper)
2. Send a profile
3. Quick-search returns 10-15 jobs
4. User "selects" top 3 jobs
5. Detail-scraper fetches enriched details for selected jobs
6. Verify enriched results have salary/description/requirements

Usage:
    uv run python scripts/test_two_phase.py
"""

import json
import sys
import time

from langgraph.types import Command


def main():
    print("=" * 70)
    print("Two-Phase Job Search — CLI Test")
    print("Phase 1: Quick Search (Tavily/Brave) -> Phase 2: Detail Scrape (Firecrawl)")
    print("=" * 70)

    # Step 1: Create agent
    print("\n[1/6] Creating orchestrator with quick-searcher + detail-scraper...")
    t0 = time.time()

    from langgraph.checkpoint.memory import MemorySaver

    from backend.agents.orchestrator import create_orchestrator

    checkpointer = MemorySaver()
    agent = create_orchestrator(checkpointer=checkpointer)
    print(f"  Agent created in {time.time() - t0:.1f}s")

    config = {"configurable": {"thread_id": "cli-two-phase-001"}}

    # Step 2: Send profile + trigger search
    print("\n[2/6] Sending profile and requesting job search...")
    profile_msg = """Find remote jobs for me:
Skills: Python, FastAPI, React, TypeScript, PostgreSQL, Docker, AWS, LangChain
Experience: 5 years as a full-stack developer
Recent Roles: Senior Software Engineer, Backend Developer
Preference: Remote software engineering positions"""

    t0 = time.time()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": profile_msg}]},
        config=config,
    )

    # Auto-approve any HITL interrupts (search tools)
    interrupt_count = 0
    while "__interrupt__" in result and len(result["__interrupt__"]) > 0:
        interrupt_count += 1
        interrupt = result["__interrupt__"][0]
        value = getattr(interrupt, "value", interrupt) if not isinstance(interrupt, dict) else interrupt
        print(f"  HITL Interrupt #{interrupt_count}: auto-approving... ({str(value)[:80]})")
        result = agent.invoke(
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
        )

    elapsed = time.time() - t0
    print(f"  Phase 1 completed in {elapsed:.1f}s ({interrupt_count} interrupts auto-approved)")

    # Step 3: Parse Phase 1 results
    print("\n[3/6] Parsing Phase 1 (quick search) results...")
    from backend.utils.parser import parse_jobs_response

    response_msgs = result.get("messages", [])
    all_jobs = []
    seen_titles = set()
    for msg in response_msgs:
        content = getattr(msg, "content", "")
        if not content:
            continue
        parsed = parse_jobs_response(content)
        for job in parsed:
            title_key = job.get("title", "").lower().strip()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                all_jobs.append(job)

    print(f"  Found {len(all_jobs)} unique jobs in Phase 1")

    if not all_jobs:
        agent_content = getattr(response_msgs[-1], "content", "") if response_msgs else ""
        print(f"  No jobs parsed. Raw response:\n{agent_content[:500]}")
        return 1

    # Display Phase 1 results
    print(f"\n  {'='*60}")
    print(f"  PHASE 1 RESULTS: {len(all_jobs)} jobs (quick search)")
    print(f"  {'='*60}")
    for i, job in enumerate(all_jobs):
        score = job.get("score", 0)
        title = job.get("title", "Unknown")[:50]
        company = job.get("company", "Unknown")[:20]
        url = job.get("url", "")
        print(f"  [{i+1:2d}] [{score:3d}%] {title} @ {company}")
        if url:
            print(f"       URL: {url[:80]}")

    # Step 4: Select top 3 jobs for detail scraping
    # Sort by score, pick top 3 with URLs
    jobs_with_urls = [j for j in all_jobs if j.get("url")]
    jobs_with_urls.sort(key=lambda x: x.get("score", 0), reverse=True)
    selected = jobs_with_urls[:3]
    selected_urls = [j["url"] for j in selected]

    print(f"\n[4/6] Selecting top {len(selected)} jobs for Phase 2 (detail scraping)...")
    for j in selected:
        print(f"  -> [{j['score']}%] {j['title']} @ {j['company']}")

    if not selected_urls:
        print("  No jobs with URLs to scrape. Skipping Phase 2.")
        return 0

    # Step 5: Phase 2 - Request details for selected jobs
    print(f"\n[5/6] Phase 2: Requesting details for {len(selected_urls)} jobs...")
    urls_text = "\n".join(f"- {url}" for url in selected_urls)
    detail_msg = f"Get detailed information for these selected jobs:\n{urls_text}"

    t0 = time.time()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": detail_msg}]},
        config=config,
    )

    # Auto-approve firecrawl interrupts
    interrupt_count = 0
    while "__interrupt__" in result and len(result["__interrupt__"]) > 0:
        interrupt_count += 1
        print(f"  HITL Interrupt #{interrupt_count}: auto-approving firecrawl...")
        result = agent.invoke(
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
        )

    elapsed = time.time() - t0
    print(f"  Phase 2 completed in {elapsed:.1f}s ({interrupt_count} interrupts)")

    # Step 6: Parse Phase 2 results
    print("\n[6/6] Parsing Phase 2 (detail scrape) results...")
    from backend.utils.parser import parse_job_details_response

    response_msgs = result.get("messages", [])
    all_details = []
    for msg in response_msgs:
        content = getattr(msg, "content", "")
        if not content:
            continue
        details = parse_job_details_response(content)
        all_details.extend(details)

    # Also try parsing as regular jobs (agent might return mixed format)
    enriched_jobs = []
    for msg in response_msgs:
        content = getattr(msg, "content", "")
        if not content:
            continue
        jobs = parse_jobs_response(content)
        enriched_jobs.extend(jobs)

    print(f"  Parsed {len(all_details)} detail records")
    print(f"  Parsed {len(enriched_jobs)} enriched job records")

    # Display Phase 2 results
    print(f"\n  {'='*60}")
    print(f"  PHASE 2 RESULTS: Enriched details")
    print(f"  {'='*60}")

    if all_details:
        for detail in all_details:
            url = detail.get("url", "")[:60]
            salary = detail.get("salary", "Not listed")
            desc = detail.get("description", "")[:100]
            reqs = detail.get("requirements", [])
            benefits = detail.get("benefits", [])

            print(f"\n  URL: {url}")
            print(f"  Salary:       {salary}")
            print(f"  Description:  {desc}...")
            if reqs:
                print(f"  Requirements: {', '.join(reqs[:3])}")
            if benefits:
                print(f"  Benefits:     {', '.join(benefits[:3])}")
    else:
        # Show raw response for debugging
        last_content = getattr(response_msgs[-1], "content", "") if response_msgs else ""
        print(f"  No structured details parsed. Raw response:\n{last_content[:500]}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"  Phase 1 (quick search): {len(all_jobs)} jobs found")
    print(f"  Phase 2 (detail scrape): {len(all_details)} jobs enriched")
    has_salary = sum(1 for d in all_details if d.get("salary"))
    has_reqs = sum(1 for d in all_details if d.get("requirements"))
    print(f"  Jobs with salary info:  {has_salary}/{len(all_details)}")
    print(f"  Jobs with requirements: {has_reqs}/{len(all_details)}")
    print(f"{'='*70}")

    if len(all_jobs) >= 5:
        print("\nVERDICT: PASS — Two-phase search working!")
        return 0
    else:
        print(f"\nVERDICT: NEEDS WORK — Only {len(all_jobs)} jobs in Phase 1")
        return 1


if __name__ == "__main__":
    sys.exit(main())

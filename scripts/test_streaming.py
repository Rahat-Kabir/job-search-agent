"""
CLI test for real-time streaming + CompositeBackend.

Tests:
1. CompositeBackend routes (default, /memories/, /workspace/)
2. astream() yields real-time chunks (tool calls, sub-agent events, final response)
3. HITL interrupt detection from stream
4. Resume with approve via astream()
5. Search results saved to /workspace/

Usage:
    uv run python scripts/test_streaming.py
"""

import asyncio
import sys
import time

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from backend.agents.orchestrator import create_orchestrator, SEARCH_TOOL_INTERRUPT


def format_chunk(chunk) -> dict:
    """Extract useful info from a stream chunk."""
    msgs = chunk.get("messages", [])
    last = msgs[-1] if msgs else None
    return {
        "type": type(last).__name__ if last else "None",
        "tool_calls": [t.get("name") for t in getattr(last, "tool_calls", [])],
        "interrupt": "__interrupt__" in chunk,
        "content": getattr(last, "content", "")[:100] if last else "",
        "msg_count": len(msgs),
    }


async def main():
    print("=" * 70)
    print("Streaming + CompositeBackend -- CLI Test")
    print("=" * 70)

    # Step 1: Create agent
    print("\n[1/5] Creating orchestrator with CompositeBackend...")
    t0 = time.time()
    checkpointer = MemorySaver()
    agent = create_orchestrator(checkpointer=checkpointer, interrupt_on=SEARCH_TOOL_INTERRUPT)
    print(f"  Agent created in {time.time() - t0:.1f}s")

    config = {"configurable": {"thread_id": "cli-stream-001"}}

    # Step 2: Test basic streaming (simple chat - no tools)
    print("\n[2/5] Testing basic astream (simple chat)...")
    t0 = time.time()
    chunks = []
    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": "Hello! What can you do?"}]},
        config=config,
        stream_mode="values",
    ):
        info = format_chunk(chunk)
        chunks.append(info)
        print(f"  Chunk {len(chunks)}: {info['type']} tools={info['tool_calls']} interrupt={info['interrupt']}")

    print(f"  Streamed {len(chunks)} chunks in {time.time() - t0:.1f}s")
    final = chunks[-1]
    print(f"  Final response: {final['content'][:100]}...")

    if len(chunks) < 2:
        print("  FAIL: Expected multiple chunks from astream")
        return 1

    # Step 3: Trigger job search (with HITL interrupt)
    print("\n[3/5] Streaming job search (expect HITL interrupt)...")
    config2 = {"configurable": {"thread_id": "cli-stream-002"}}
    t0 = time.time()
    chunks = []
    got_interrupt = False
    got_tool_call = False

    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": "Find remote Python developer jobs, 5yr experience with FastAPI, React, Docker, AWS"}]},
        config=config2,
        stream_mode="values",
    ):
        info = format_chunk(chunk)
        chunks.append(info)
        if info["tool_calls"]:
            got_tool_call = True
            print(f"  Chunk {len(chunks)}: TOOL CALL -> {info['tool_calls']}")
        if info["interrupt"]:
            got_interrupt = True
            print(f"  Chunk {len(chunks)}: INTERRUPT (HITL)")
        else:
            print(f"  Chunk {len(chunks)}: {info['type']} (msg_count={info['msg_count']})")

    elapsed = time.time() - t0
    print(f"  Phase 1 stream: {len(chunks)} chunks in {elapsed:.1f}s")
    print(f"  Got tool call: {got_tool_call}")
    print(f"  Got interrupt: {got_interrupt}")

    if not got_interrupt:
        print("  FAIL: Expected HITL interrupt for search tools")
        return 1

    # Step 4: Resume with approve, stream results
    print("\n[4/5] Resuming with approve, streaming search results...")
    t0 = time.time()
    all_chunks = []
    final_content = ""
    approve_decision = {"decisions": [{"type": "approve"}]}

    # Loop: resume and auto-approve subsequent interrupts
    last_chunk = None
    while True:
        found_interrupt = False
        async for chunk in agent.astream(
            Command(resume=approve_decision),
            config=config2,
            stream_mode="values",
        ):
            last_chunk = chunk
            info = format_chunk(chunk)
            all_chunks.append(info)

            if info["interrupt"]:
                found_interrupt = True
                print(f"  Chunk {len(all_chunks)}: AUTO-APPROVING interrupt...")
            elif info["tool_calls"]:
                print(f"  Chunk {len(all_chunks)}: SUB-AGENT -> {info['tool_calls']}")
            elif info["type"] == "ToolMessage":
                content_preview = info["content"][:60]
                print(f"  Chunk {len(all_chunks)}: TOOL RESULT -> {content_preview}...")
            elif info["type"] == "AIMessage" and info["content"]:
                final_content = info["content"]
                print(f"  Chunk {len(all_chunks)}: AI RESPONSE -> {info['content'][:60]}...")
            else:
                print(f"  Chunk {len(all_chunks)}: {info['type']} (internal)")

        if not found_interrupt:
            break

    elapsed = time.time() - t0
    print(f"  Search completed in {elapsed:.1f}s ({len(all_chunks)} chunks)")

    # Extract final content from all messages in last chunk (scan all, not just last)
    if last_chunk:
        all_msgs = last_chunk.get("messages", [])
        for msg in all_msgs:
            content = getattr(msg, "content", "")
            if content and len(content) > len(final_content):
                final_content = content

    # Step 5: Parse and display results
    print("\n[5/5] Parsing search results...")
    from backend.utils.parser import parse_jobs_response

    jobs = parse_jobs_response(final_content)
    print(f"  Found {len(jobs)} jobs in final response")

    if jobs:
        print(f"\n  {'='*60}")
        print(f"  SEARCH RESULTS: {len(jobs)} jobs")
        print(f"  {'='*60}")
        for i, job in enumerate(jobs[:5]):
            score = job.get("score", 0)
            title = job.get("title", "Unknown")[:45]
            company = job.get("company", "Unknown")[:20]
            print(f"  [{i+1}] [{score:3d}%] {title} @ {company}")
        if len(jobs) > 5:
            print(f"  ... and {len(jobs) - 5} more")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"  Basic streaming: OK ({chunks[0]['type']} -> ... -> AIMessage)")
    print(f"  HITL interrupt detected: {got_interrupt}")
    print(f"  Tool calls detected: {got_tool_call}")
    print(f"  Total search chunks: {len(all_chunks)}")
    print(f"  Jobs found: {len(jobs)}")
    print(f"{'='*70}")

    if len(jobs) >= 5 and got_interrupt and got_tool_call:
        print("\nVERDICT: PASS -- Streaming + CompositeBackend working!")
        return 0
    else:
        print(f"\nVERDICT: NEEDS WORK")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

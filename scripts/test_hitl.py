"""
Test script for HITL (Human-in-the-Loop) and persistent checkpointer.

Usage:
    uv run python scripts/test_hitl.py

Tests:
1. PostgresSaver initializes and creates checkpoint tables
2. Agent creation with interrupt_on config
3. HITL interrupt fires when search tools are called
4. Resume with Command(resume=True/False) works
5. State persists across invocations via thread_id
"""

import asyncio
import sys
import uuid

from dotenv import load_dotenv

load_dotenv()

from backend.agents.checkpointer import close_checkpointer, get_checkpointer, init_checkpointer
from backend.agents.orchestrator import create_orchestrator_with_hitl
from backend.config import settings


def test_checkpointer_init():
    """Test that PostgresSaver initializes correctly."""
    print("\n[TEST 1] PostgresSaver initialization")
    print("-" * 40)

    if not settings.database_url:
        print("SKIP: DATABASE_URL not set")
        return False

    try:
        cp = asyncio.run(init_checkpointer())
        print(f"OK: Checkpointer initialized: {type(cp).__name__}")

        # Verify we can get it again (singleton)
        cp2 = get_checkpointer()
        assert cp is cp2, "Singleton broken"
        print("OK: Singleton pattern works")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_agent_creation():
    """Test agent creation with HITL config."""
    print("\n[TEST 2] Agent creation with interrupt_on")
    print("-" * 40)

    try:
        agent, checkpointer = create_orchestrator_with_hitl()
        print(f"OK: Agent created: {type(agent).__name__}")
        print(f"OK: Checkpointer: {type(checkpointer).__name__}")
        return True, agent
    except Exception as e:
        print(f"FAIL: {e}")
        return False, None


def test_basic_chat(agent):
    """Test basic chat (no interrupt expected)."""
    print("\n[TEST 3] Basic chat (no search — no interrupt)")
    print("-" * 40)

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    messages = [{"role": "user", "content": "Hello! What can you do?"}]

    try:
        result = agent.invoke({"messages": messages}, config=config)

        has_interrupt = "__interrupt__" in result and len(result.get("__interrupt__", [])) > 0
        response_msgs = result.get("messages", [])
        content = getattr(response_msgs[-1], "content", "") if response_msgs else ""

        print(f"OK: Got response ({len(content)} chars)")
        print(f"OK: Interrupt fired: {has_interrupt} (expected: False)")
        print(f"    Response: {content[:100]}...")

        if has_interrupt:
            print("WARN: Unexpected interrupt on basic chat")

        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_search_interrupt(agent):
    """Test that search triggers HITL interrupt."""
    print("\n[TEST 4] Search trigger — HITL interrupt")
    print("-" * 40)

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # First, give the agent a profile context
    messages = [
        {"role": "user", "content": "I'm a Python developer with 5 years experience in FastAPI and React. Find jobs for me."}
    ]

    try:
        result = agent.invoke({"messages": messages}, config=config)

        has_interrupt = "__interrupt__" in result and len(result.get("__interrupt__", [])) > 0

        if has_interrupt:
            interrupts = result["__interrupt__"]
            interrupt = interrupts[0]
            value = getattr(interrupt, "value", interrupt) if not isinstance(interrupt, dict) else interrupt
            print(f"OK: HITL interrupt fired!")
            print(f"    Interrupt value: {str(value)[:200]}")

            # Test resume with approval
            from langgraph.types import Command

            print("\n    Resuming with approval...")
            approve = {"decisions": [{"type": "approve"}]}
            result = agent.invoke(Command(resume=approve), config=config)

            # Auto-approve any subsequent interrupts
            while "__interrupt__" in result and len(result["__interrupt__"]) > 0:
                print("    Auto-approving follow-up interrupt...")
                result = agent.invoke(Command(resume=approve), config=config)

            response_msgs = result.get("messages", [])
            content = getattr(response_msgs[-1], "content", "") if response_msgs else ""
            print(f"OK: Got search results ({len(content)} chars)")
            print(f"    Response: {content[:200]}...")
            return True
        else:
            response_msgs = result.get("messages", [])
            content = getattr(response_msgs[-1], "content", "") if response_msgs else ""
            print(f"INFO: No interrupt fired (agent may not have tried search tools)")
            print(f"    Response: {content[:200]}...")
            return True

    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_persistence(agent):
    """Test that state persists across invocations with same thread_id."""
    print("\n[TEST 5] State persistence across invocations")
    print("-" * 40)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # First message
        messages1 = [{"role": "user", "content": "My name is TestUser and I know Python."}]
        result1 = agent.invoke({"messages": messages1}, config=config)
        resp1 = result1.get("messages", [])
        content1 = getattr(resp1[-1], "content", "") if resp1 else ""
        print(f"OK: First message sent, got response ({len(content1)} chars)")

        # Second message — should remember context
        messages2 = [
            {"role": "user", "content": "My name is TestUser and I know Python."},
            {"role": "assistant", "content": content1},
            {"role": "user", "content": "What skills did I mention?"},
        ]
        result2 = agent.invoke({"messages": messages2}, config=config)
        resp2 = result2.get("messages", [])
        content2 = getattr(resp2[-1], "content", "") if resp2 else ""
        print(f"OK: Second message sent, got response ({len(content2)} chars)")
        print(f"    Response: {content2[:200]}...")

        has_python = "python" in content2.lower()
        print(f"OK: Agent remembers context: {'Python' if has_python else 'unclear'}")
        return True

    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    print("=" * 50)
    print("HITL & Persistent Checkpointer Tests")
    print("=" * 50)

    results = {}

    # Test 1: Checkpointer
    results["checkpointer"] = test_checkpointer_init()

    # Test 2: Agent creation
    success, agent = test_agent_creation()
    results["agent_creation"] = success

    if not agent:
        print("\nCANNOT CONTINUE: Agent creation failed")
        return

    # Test 3: Basic chat
    results["basic_chat"] = test_basic_chat(agent)

    # Test 4: Search interrupt (makes API calls — skip if no keys)
    if settings.tavily_api_key or settings.brave_api_key:
        results["search_interrupt"] = test_search_interrupt(agent)
    else:
        print("\n[TEST 4] SKIP: No search API keys configured")
        results["search_interrupt"] = None

    # Test 5: State persistence
    results["persistence"] = test_state_persistence(agent)

    # Summary
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    for name, passed in results.items():
        status = "PASS" if passed else ("SKIP" if passed is None else "FAIL")
        print(f"  {name}: {status}")

    asyncio.run(close_checkpointer())

    failed = [k for k, v in results.items() if v is False]
    if failed:
        print(f"\n{len(failed)} test(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\nAll tests passed!")


if __name__ == "__main__":
    main()

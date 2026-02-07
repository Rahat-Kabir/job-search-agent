"""
Job Search Agent - CLI Entry Point.

Token-optimized CLI with persistent state and HITL support.
"""

import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.agents.checkpointer import close_checkpointer, init_checkpointer
from backend.agents.orchestrator import create_orchestrator_with_hitl, truncate_cv
from backend.tools.pdf_parser import parse_pdf_from_path

try:
    from langgraph.types import Command
except ImportError:
    Command = None


def main():
    """Run the job search agent CLI."""
    print("Job Search Agent")
    print("=" * 40)

    # Check for CV file argument (handle filenames with spaces)
    initial_message = None
    if len(sys.argv) > 1:
        cv_path = Path(" ".join(sys.argv[1:]))  # Join all args for filenames with spaces
        if cv_path.exists() and cv_path.suffix.lower() == ".pdf":
            print(f"Loading CV: {cv_path}")
            cv_text = parse_pdf_from_path(str(cv_path))
            print(f"Extracted {len(cv_text)} chars")

            # Truncate for token efficiency
            cv_text = truncate_cv(cv_text, max_chars=4000)
            print(f"Truncated to {len(cv_text)} chars")

            initial_message = f"Here's my CV:\n\n{cv_text}"
        else:
            print(f"Error: {cv_path} is not a valid PDF")
            return

    # Initialize checkpointer
    print("\nInitializing...")
    try:
        init_checkpointer()
    except ValueError:
        print("Warning: DATABASE_URL not set — using in-memory state (no persistence)")

    try:
        agent, _ = create_orchestrator_with_hitl()
        print("Ready!\n")
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Config for state persistence
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    messages = []

    print("Commands: /quit, /upload <path>")
    print("-" * 40)

    def chat(content: str) -> str:
        """Send message and get response, handling HITL interrupts."""
        messages.append({"role": "user", "content": content})
        result = agent.invoke({"messages": messages}, config=config)

        # Handle HITL interrupt
        if "__interrupt__" in result and len(result["__interrupt__"]) > 0:
            interrupt = result["__interrupt__"][0]
            value = getattr(interrupt, "value", interrupt) if not isinstance(interrupt, dict) else interrupt
            print(f"\n[HITL] Agent wants to call external search APIs.")
            if isinstance(value, dict):
                desc = value.get("description", str(value))
                print(f"[HITL] Details: {desc}")

            while True:
                choice = input("[HITL] Approve? (y/n): ").strip().lower()
                if choice in ("y", "yes"):
                    approve = {"decisions": [{"type": "approve"}]}
                    result = agent.invoke(Command(resume=approve), config=config)
                    # Auto-approve subsequent tool calls in same search
                    while "__interrupt__" in result and len(result["__interrupt__"]) > 0:
                        print("[HITL] Auto-approving follow-up tool call...")
                        result = agent.invoke(Command(resume=approve), config=config)
                    break
                elif choice in ("n", "no"):
                    reject = {"decisions": [{"type": "reject"}]}
                    result = agent.invoke(Command(resume=reject), config=config)
                    break
                else:
                    print("Please enter 'y' or 'n'")

        response_msgs = result.get("messages", [])
        if response_msgs:
            resp = getattr(response_msgs[-1], "content", str(response_msgs[-1]))
            messages.append({"role": "assistant", "content": resp})
            return resp
        return "No response"

    # Initial CV upload
    if initial_message:
        print("\nYou: [CV uploaded]")
        print(f"\nAgent: {chat(initial_message)}\n")

    # Chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            if user_input.lower() == "/quit":
                break

            if user_input.startswith("/upload "):
                path = user_input[8:].strip()
                if Path(path).exists():
                    cv_text = truncate_cv(parse_pdf_from_path(path), 4000)
                    user_input = f"Here's my CV:\n\n{cv_text}"
                    print("You: [CV uploaded]")
                else:
                    print(f"Not found: {path}")
                    continue

            print(f"\nAgent: {chat(user_input)}\n")

        except KeyboardInterrupt:
            break

    close_checkpointer()
    print("Goodbye!")


if __name__ == "__main__":
    main()

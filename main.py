"""
Job Search Agent - CLI Entry Point.

Token-optimized CLI with state persistence.
"""

import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.agents.orchestrator import create_orchestrator_with_hitl, truncate_cv
from backend.tools.pdf_parser import parse_pdf_from_path


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

    # Create agent
    print("\nInitializing...")
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
        """Send message and get response."""
        messages.append({"role": "user", "content": content})
        result = agent.invoke({"messages": messages}, config=config)

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

    print("Goodbye!")


if __name__ == "__main__":
    main()

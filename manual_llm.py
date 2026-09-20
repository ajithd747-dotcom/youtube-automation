"""Manual LLM backend: pauses and asks the human to run the prompt through
Claude Code (or any chat LLM) themselves, then paste the response back in.
No API calls, no automation of any subscription -- just a human relay step.
"""
import sys

try:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def ask(prompt: str, copy_to_clipboard: bool = True) -> str:
    print("\n" + "=" * 70)
    print("MANUAL LLM STEP -- copy the prompt below into Claude Code,")
    print("then paste its reply here and finish with a line containing only: END")
    print("=" * 70)
    print(prompt)
    print("=" * 70)

    if copy_to_clipboard:
        try:
            import subprocess
            subprocess.run("clip", input=prompt.encode("utf-16"), shell=True, check=True)
            print("(prompt copied to clipboard)")
        except Exception:
            pass

    lines = []
    print("\nPaste response, then type END on its own line:")
    for line in sys.stdin:
        if line.rstrip("\n") == "END":
            break
        lines.append(line)
    return "".join(lines).strip()


if __name__ == "__main__":
    result = ask("Say hello in one short sentence.")
    print("\n--- Captured response ---")
    print(result)

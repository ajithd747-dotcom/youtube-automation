"""Minimal client for talking to a local Ollama server."""
import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"


def generate(prompt: str, model: str = MODEL) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["response"]


if __name__ == "__main__":
    print(generate("Say hello in one short sentence."))

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyxis import Agent, MockProvider, OpenAICompatibleProvider


def test_agent_runs_with_provider() -> None:
    provider = MockProvider(output="steady answer")
    agent = Agent(name="navigator", instructions="Be concise.", provider=provider)

    result = agent.run("Where next?")

    assert result.output == "steady answer"
    assert provider.requests[0].prompt == "Where next?"
    assert provider.requests[0].instructions == "Be concise."


def test_agent_runs_with_openai_compatible_provider() -> None:
    seen: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            seen["path"] = self.path
            seen["authorization"] = self.headers["Authorization"]
            seen["body"] = json.loads(self.rfile.read(length).decode("utf-8"))
            response = {
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
                "choices": [
                    {
                        "message": {
                            "content": "provider answer",
                        }
                    }
                ]
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        def log_message(self, format: str, *args) -> None:
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        provider = OpenAICompatibleProvider(
            model="test-model",
            base_url=f"http://127.0.0.1:{server.server_port}",
            api_key="test-key",
        )
        agent = Agent(name="navigator", instructions="Be useful.", provider=provider)

        result = agent.run("Hello")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result.output == "provider answer"
    assert result.metadata["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
    }
    assert seen["path"] == "/chat/completions"
    assert seen["authorization"] == "Bearer test-key"
    assert seen["body"] == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "Be useful."},
            {"role": "user", "content": "Hello"},
        ],
    }


def test_openai_compatible_provider_reads_standard_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9999/v3")
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")

    provider = OpenAICompatibleProvider(model="test-model")

    assert provider.base_url == "http://127.0.0.1:9999/v3"
    assert provider.api_key == "env-key"


def test_openai_compatible_provider_retries_server_errors() -> None:
    seen = {"requests": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            seen["requests"] += 1
            if seen["requests"] == 1:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"temporary"}')
                return

            response = {
                "choices": [
                    {
                        "message": {
                            "content": "retried answer",
                        }
                    }
                ]
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        def log_message(self, format: str, *args) -> None:
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        provider = OpenAICompatibleProvider(
            model="test-model",
            base_url=f"http://127.0.0.1:{server.server_port}",
            api_key="test-key",
            max_retries=1,
            backoff=0,
        )
        agent = Agent(name="navigator", provider=provider)

        result = agent.run("Hello")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result.output == "retried answer"
    assert seen["requests"] == 2

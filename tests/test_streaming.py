import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyxis import Agent, CompletionChunk, MockProvider, OpenAICompatibleProvider, Pyxis, tool


def test_session_stream_yields_start_result_done() -> None:
    session = Pyxis(agent=Agent(name="navigator", provider=MockProvider(output="hello"))).session()

    events = list(session.stream("say hello"))

    assert [event.type for event in events] == ["start", "result", "done"]
    assert events[0].data["input"] == "say hello"
    assert events[1].data["output"] == "hello"
    assert events[2].data["output"] == "hello"


def test_session_stream_yields_checkpoint_for_paused_tool_call() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        return path

    provider = MockProvider(
        output=json.dumps(
            {
                "type": "tool_call",
                "tool": "write_file",
                "args": {"path": "demo.txt"},
            }
        )
    )
    session = Pyxis(agent=Agent(name="navigator", provider=provider, tools=[write_file])).session()

    events = list(session.stream("write file"))

    assert [event.type for event in events] == ["start", "result", "checkpoint", "done"]
    assert events[2].data["tool"] == "write_file"
    assert events[2].data["checkpoint"]["status"] == "pending"


def test_session_stream_yields_provider_delta_events() -> None:
    class StreamingProvider:
        def complete(self, request):
            raise AssertionError("complete should not be called when stream is available")

        def stream(self, request):
            yield CompletionChunk(text="hel", metadata={"index": 0})
            yield CompletionChunk(text="lo", metadata={"index": 1})

    session = Pyxis(agent=Agent(name="navigator", provider=StreamingProvider())).session()

    events = list(session.stream("say hello"))

    assert [event.type for event in events] == ["start", "delta", "delta", "result", "done"]
    assert events[1].data["text"] == "hel"
    assert events[2].data["text"] == "lo"
    assert events[3].data["output"] == "hello"
    assert events[3].data["metadata"]["streamed"] is True


def test_openai_compatible_provider_streams_sse_chunks() -> None:
    seen: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            seen["path"] = self.path
            seen["authorization"] = self.headers["Authorization"]
            seen["body"] = json.loads(self.rfile.read(length).decode("utf-8"))
            chunks = [
                {"choices": [{"delta": {"content": "hel"}}]},
                {"choices": [{"delta": {"content": "lo"}}]},
            ]
            body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
            body += "data: [DONE]\n\n"
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

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

        chunks = list(provider.stream(Agent(name="navigator").completion_request("Hello")))
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert [chunk.text for chunk in chunks] == ["hel", "lo"]
    assert seen["path"] == "/chat/completions"
    assert seen["authorization"] == "Bearer test-key"
    assert seen["body"]["stream"] is True
    assert seen["body"]["model"] == "test-model"

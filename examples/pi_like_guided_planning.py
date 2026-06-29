"""A Pi-like guided planning demo using local Pyxis primitives."""

from __future__ import annotations

from pyxis import Agent, CompletionChunk, Pyxis, SessionMemory, Workflow


class StreamingPlanProvider:
    """Tiny local provider that streams a guided planning response."""

    def complete(self, request):
        raise AssertionError("This example uses streaming.")

    def stream(self, request):
        yield CompletionChunk(text="1. Clarify the goal.\n")
        yield CompletionChunk(text="2. Name constraints and risks.\n")
        yield CompletionChunk(text="3. Ask before sensitive action.\n")


def main() -> None:
    memory = SessionMemory()
    memory.set_preference("tone", "concise")
    memory.set_preference("approval_mode", "strict")
    memory.set_project_context(name="Guided planning")

    agent = Agent(
        name="navigator",
        instructions=(
            "Help the user think clearly before acting. Keep the response concise, "
            "calm, and controllable."
        ),
        provider=StreamingPlanProvider(),
        memory=memory,
    )
    session = Pyxis(agent=agent).session()

    print("Clarify first:")
    result = session.navigate("帮我弄一下")
    print(result.output)

    print("\nGuided plan:")
    for event in session.stream("Plan a controlled research workflow"):
        if event.type == "delta":
            print(event.data["text"], end="")

    workflow = (
        Workflow("guided-planning")
        .step("clean", lambda text: text.strip())
        .reflect("Check if the plan still matches the user's goal")
        .ask("Does this direction look right?")
        .revise("What should change before execution?")
    )
    paused = session.run(workflow, "  Draft research plan  ")
    print("\nWorkflow pause:")
    print(paused.checkpoint.summary if paused.checkpoint else "No checkpoint")
    print(paused.checkpoint.preview if paused.checkpoint else "")

    print("\nMemory:")
    print(memory.to_dict())


if __name__ == "__main__":
    main()

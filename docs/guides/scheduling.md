# Scheduling

Scheduling is intentionally outside Pyxis core.

Schedulers decide when work starts. Pyxis decides how agent work stays
controllable, observable, and resumable once it starts.

Use an application scheduler such as cron, APScheduler, Celery, a queue worker,
or a platform-native scheduled job to call your Pyxis-powered workflow.

## APScheduler Shape

```python
def run_daily_briefing():
    session = build_astra_session()
    result = session.structured_run(
        "Generate today's briefing",
        schema=briefing_schema,
        max_retries=1,
    )
    return result
```

Your scheduler owns the trigger and retry policy. Pyxis records provider,
structured output, checkpoint, workflow, and tool events inside the session.

## Worker Shape

```python
def briefing_worker(job):
    session = build_astra_session()
    result = session.run(briefing_workflow, job.payload)
    if result.paused:
        save_pending_checkpoint(result.checkpoint)
```

If the workflow pauses, hand the checkpoint to a Web UI or human approval
system. After approval, restore the session and resume the checkpointed work.

## Event Sinks

Attach an event sink when scheduled work needs an audit trail:

```python
from pyxis import EventLog, Session

events = EventLog(sinks=[database_event_sink])
session = Session(agent=agent, events=events)
```

The database sink belongs in the host application or an extension package, not
in Pyxis core.

## Boundary

Pyxis core does not provide:

- a scheduler daemon
- a queue
- database migrations
- a web approval UI
- hidden autonomous loops

Those choices belong to the product embedding Pyxis.

import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

class EventBus:
  def __init__(self):
    self.listeners = {}
    self._tasks = set()

  def add_listener(self, event_name, listener):
    if not self.listeners.get(event_name, None):
      self.listeners[event_name] = {listener}
    else:
      self.listeners[event_name].add(listener)

  def remove_listener(self, event_name, listener):
    event_listeners = self.listeners.get(event_name)
    if not event_listeners:
      return

    event_listeners.discard(listener)
    if len(event_listeners) == 0:
      del self.listeners[event_name]

  def send(self, event_name, event_data=None):
    # Iterate a copy so a listener can (un)subscribe while being notified.
    for listener in list(self.listeners.get(event_name, ())):
      task = asyncio.create_task(listener(event_data))
      # Keep a strong reference until the task is done; the event loop only
      # holds a weak one, so an unreferenced task can be garbage collected
      # mid-execution.
      self._tasks.add(task)
      task.add_done_callback(self._on_task_done)

  def _on_task_done(self, task: asyncio.Task):
    self._tasks.discard(task)
    try:
      task.result()
    except asyncio.CancelledError:
      pass
    except Exception as ex:
      _LOGGER.exception("Event listener task failed: %s", ex)

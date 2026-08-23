import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

class EventBus:
  def __init__(self):
    self.listeners = {}

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
    listeners = self.listeners.get(event_name, [])
    for listener in listeners:
      task = asyncio.create_task(listener(event_data))
      task.add_done_callback(self._log_listener_exception)

  @staticmethod
  def _log_listener_exception(task: asyncio.Task):
    try:
      task.result()
    except Exception as ex:
      _LOGGER.exception("Event listener task failed: %s", ex)

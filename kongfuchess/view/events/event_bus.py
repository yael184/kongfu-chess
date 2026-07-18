# view/events/event_bus.py
"""EventBus — the Observer/pub-sub core (final_plan §7.6).

Minimal and synchronous: no threads, no queue. Publishing is O(subscribers) and happens off the
render call stack (the game loop feeds it before drawing), so a slow observer never blocks a frame.
Subscribers register by event type; publishing dispatches to the handlers for that exact type.
"""
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)

    def subscribe(self, event_type, handler):
        self._handlers[event_type].append(handler)

    def publish(self, event):
        for handler in self._handlers[type(event)]:
            handler(event)

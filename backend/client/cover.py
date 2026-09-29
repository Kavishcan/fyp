"""Constant-rate cover traffic (docs/52).

Blind unlock hides WHAT a device asks and WHICH node is relevant, but a
node or observer still sees WHEN rounds happen and how many. With a fixed
schedule the device sends exactly one round per tick: the next queued
question if there is one, otherwise a cover round (P dummy points to every
node). Questions are embedded and planned when they are submitted, so at the
tick a real round and a cover round are sent the same way at the same time.
The observer then sees one identical round per tick, whether the user asked
nothing or asked every tick.

Cost: every tick spends P evaluations of the credential's budget at every
node, used or not; the tick interval bounds how quickly a question is sent
(worst case one interval of waiting). It hides timing only for questions
asked no faster than the tick rate — a burst queues.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Ticket:
    question: str
    submitted: float
    result: dict | None = None


@dataclass
class CoverTrafficScheduler:
    device: object
    interval_s: float = 30.0
    _queue: deque = field(default_factory=deque)
    rounds: list[str] = field(default_factory=list)     # "real" / "cover", device-side log only

    def submit(self, question: str) -> Ticket:
        ticket = Ticket(question, time.time())
        q, plan = self.device.plan(question)          # all question-dependent work, before any tick
        self._queue.append((ticket, q, plan))
        return ticket

    def tick(self) -> Ticket | None:
        """Send exactly one round. Returns the ticket answered, if any."""
        self.device.refresh()                         # daily fetches happen on the tick, not on a question
        if self._queue:
            ticket, q, plan = self._queue.popleft()
            result = self.device.send(plan)
            self.rounds.append("real")
            ticket.result = self.device.finish(ticket.question, q, plan, result)
            return ticket
        self.device.cover()
        self.rounds.append("cover")
        return None

    def run(self, ticks: int) -> list[Ticket]:
        """Drive `ticks` rounds at the fixed interval (for the CLI demo)."""
        answered = []
        next_at = time.monotonic()
        for _ in range(ticks):
            delay = next_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            ticket = self.tick()
            if ticket is not None:
                answered.append(ticket)
            next_at += self.interval_s
        return answered

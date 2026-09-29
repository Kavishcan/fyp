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
    _pending_finish: list = field(default_factory=list)
    rounds: list[str] = field(default_factory=list)     # "real" / "cover", device-side log only

    def submit(self, question: str) -> Ticket:
        ticket = Ticket(question, time.time())
        q, plan = self.device.plan(question)          # all question-dependent work, before any tick
        self._queue.append((ticket, q, plan))
        return ticket

    def tick(self, *, defer_finish: bool = False, allow_real: bool = True) -> Ticket | None:
        """Send exactly one round. Defer local answer work during a timed run."""
        self.device.refresh()                         # daily fetches happen on the tick, not on a question
        if allow_real and self._queue:
            ticket, q, plan = self._queue.popleft()
            result = self.device.send(plan)
            self.rounds.append("real")
            if defer_finish:
                self._pending_finish.append((ticket, q, plan, result))
            else:
                ticket.result = self.device.finish(ticket.question, q, plan, result)
            return ticket
        self.device.cover()
        self.rounds.append("cover")
        return None

    def run(self, ticks: int, *, first_real_at: int = 0) -> list[Ticket]:
        """Drive `ticks` rounds; finish answers after the network schedule."""
        if ticks < 1 or not 0 <= first_real_at < ticks:
            raise ValueError("first_real_at must identify a tick in the run")
        answered = []
        next_at = time.monotonic()
        for i in range(ticks):
            delay = next_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            ticket = self.tick(defer_finish=True, allow_real=i >= first_real_at)
            if ticket is not None:
                answered.append(ticket)
            next_at += self.interval_s
        for ticket, q, plan, result in self._pending_finish:
            ticket.result = self.device.finish(ticket.question, q, plan, result)
        self._pending_finish.clear()
        return answered

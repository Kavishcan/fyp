"""Standalone device-side client for blind unlock (docs/52).

`Device` runs the whole query path on the user's machine and talks to nodes
through `client.transport`; `CoverTrafficScheduler` sends one identical round
per tick. No server holds the question.
"""
from client.cover import CoverTrafficScheduler, Ticket
from client.device import Device
from client.transport import LocalTransport, MCPTransport, NodeTransport, profile_from_dict

__all__ = ["CoverTrafficScheduler", "Device", "LocalTransport", "MCPTransport", "NodeTransport", "Ticket",
           "profile_from_dict"]

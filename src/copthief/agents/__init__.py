"""Agent MCP servers: each agent (cop/thief) is exposed as its own FastMCP server.

Per the lecture, each agent is autonomous and owns its LLM voice; it only learns
about the rival through the free-text messages relayed by the orchestrator.
"""

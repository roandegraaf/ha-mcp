import json

import pytest

import ha_mcp.tools.traces as traces


class FakeWebSocket:
    def __init__(self):
        self.calls = []

    async def send_command(self, command, **kwargs):
        self.calls.append({"type": command, **kwargs})

        if command == "trace/list":
            return [
                {"run_id": "run-1"},
                {"run_id": "run-2"},
                {"run_id": "run-3"},
            ]

        return {"run_id": kwargs["run_id"], "trace": "fake trace data"}


class FakeMCPServer:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register


@pytest.mark.asyncio
async def test_get_automation_traces_fetches_requested_number(monkeypatch):
    ws = FakeWebSocket()
    server = FakeMCPServer()
    traces.register_trace_tools(server)

    monkeypatch.setattr(traces, "get_clients", lambda _ctx: (ws, None))

    result = await server.tools["get_automation_traces"](
        object(),
        automation_id="automation.test_rule",
        limit=2,
    )

    data = json.loads(result)

    assert data["automation_id"] == "automation.test_rule"
    assert data["count"] == 2
    assert [trace["run_id"] for trace in data["traces"]] == ["run-1", "run-2"]

    assert ws.calls == [
        {
            "type": "trace/list",
            "domain": "automation",
            "item_id": "test_rule",
        },
        {
            "type": "trace/get",
            "domain": "automation",
            "item_id": "test_rule",
            "run_id": "run-1",
        },
        {
            "type": "trace/get",
            "domain": "automation",
            "item_id": "test_rule",
            "run_id": "run-2",
        },
    ]
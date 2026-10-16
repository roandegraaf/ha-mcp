import pytest

from ha_mcp.tools.automation import register_automation_tools


class _FakeWebSocketClient:
    def __init__(self):
        self.commands = []

    async def send_command(self, command, **kwargs):
        self.commands.append((command, kwargs))
        if command == "trace/list":
            return [{"run_id": f"{kwargs['item_id']}-run-1"}]
        return {
            "run_id": kwargs["run_id"],
            "trace": {"action/0": [{"path": "action/0"}]},
        }


class _FakeRestClient:
    async def get_states(self):
        return [
            {
                "entity_id": "automation.first",
                "attributes": {"id": "first", "friendly_name": "First"},
            },
            {
                "entity_id": "light.lounge",
                "attributes": {"id": "not-an-automation"},
            },
            {
                "entity_id": "automation.second",
                "attributes": {"id": "second", "friendly_name": "Second"},
            },
        ]


class _FakeContext:
    def __init__(self, ws, rest):
        self.fastmcp = type(
            "FakeFastMCP",
            (),
            {"_lifespan_result": {"ws": ws, "rest": rest}},
        )()


class _FakeMCPServer:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register


async def test_get_all_automation_traces_fetches_all_runs_for_all_automations():
    ws = _FakeWebSocketClient()
    server = _FakeMCPServer()
    register_automation_tools(server)

    result = await server.tools["get_all_automation_traces"](
        _FakeContext(ws, _FakeRestClient())
    )

    assert [call[0] for call in ws.commands] == [
        "trace/list",
        "trace/list",
        "trace/get",
        "trace/get",
    ]
    assert all(call[1]["domain"] == "automation" for call in ws.commands)
    assert all(call[1]["item_id"] in {"first", "second"} for call in ws.commands)
    assert '"automation_count": 2' in result
    assert '"trace_count": 2' in result
    assert '"path": "action/0"' in result


async def test_get_all_automation_traces_reports_missing_internal_id():
    class _MissingIdRestClient:
        async def get_states(self):
            return [{"entity_id": "automation.no_id", "attributes": {}}]

    server = _FakeMCPServer()
    register_automation_tools(server)

    with pytest.raises(ValueError, match="automation.no_id"):
        await server.tools["get_all_automation_traces"](
            _FakeContext(_FakeWebSocketClient(), _MissingIdRestClient())
        )

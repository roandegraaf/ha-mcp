import json
from unittest.mock import AsyncMock

import pytest

from ha_mcp.tools import timer


class _FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register


class _FakeWebSocket:
    def __init__(self, result=None):
        self.result = result or {"id": "example"}
        self.calls = []

    async def send_command(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return self.result


@pytest.fixture
def create_timer_tool(monkeypatch):
    mcp = _FakeMCP()
    timer.register_timer_tools(mcp)
    confirm = AsyncMock(return_value=True)
    monkeypatch.setattr(timer, "confirm_change", confirm)
    websocket = _FakeWebSocket()
    monkeypatch.setattr(timer, "get_clients", lambda _ctx: (websocket, None))
    return mcp.tools["create_timer"], websocket, confirm


async def test_create_timer_calls_home_assistant_timer_api(create_timer_tool):
    create_timer, websocket, confirm = create_timer_tool

    result = await create_timer(
        object(),
        name="Kitchen timer",
        duration="00:05:00",
        restore=True,
        icon="mdi:timer-outline",
        skip_confirm=True,
    )

    assert json.loads(result) == {"status": "created", "result": {"id": "example"}}
    assert websocket.calls == [
        (
            "timer/create",
            {
                "name": "Kitchen timer",
                "duration": "00:05:00",
                "restore": True,
                "icon": "mdi:timer-outline",
            },
        )
    ]
    confirm.assert_awaited_once()


async def test_create_timer_does_not_call_api_when_cancelled(create_timer_tool):
    create_timer, websocket, confirm = create_timer_tool
    confirm.return_value = False

    result = await create_timer(
        object(),
        name="Kitchen timer",
        duration="00:05:00",
    )

    assert json.loads(result)["status"] == "cancelled"
    assert websocket.calls == []


@pytest.mark.parametrize(
    ("name", "duration", "error"),
    [
        (" ", "00:05:00", "name must not be empty"),
        ("Kitchen timer", " ", "duration must not be empty"),
    ],
)
async def test_create_timer_rejects_empty_required_values(
    create_timer_tool, name, duration, error
):
    create_timer, websocket, confirm = create_timer_tool

    result = await create_timer(
        object(),
        name=name,
        duration=duration,
    )

    assert json.loads(result) == {"error": error}
    assert websocket.calls == []
    confirm.assert_not_awaited()

import json
from unittest.mock import AsyncMock

import pytest

from ha_mcp.tools import ui_helpers


class _FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register


class _FakeREST:
    def __init__(self, group_type=None, final_response=None):
        self.group_type = group_type
        self.final_response = final_response or {
            "type": "create_entry",
            "title": "Test helper",
            "result": True,
        }
        self.steps = []
        self.cancelled = []

    async def start_config_flow(self, handler):
        self.handler = handler
        if handler == "group":
            return {"type": "menu", "flow_id": "group-flow"}
        return {"type": "form", "step_id": "user", "flow_id": "integral-flow"}

    async def submit_config_flow_step(self, flow_id, user_input):
        self.steps.append((flow_id, user_input))
        if flow_id == "group-flow":
            if "next_step_id" in user_input:
                return {
                    "type": "form",
                    "step_id": user_input["next_step_id"],
                }
            return self.final_response
        return self.final_response

    async def cancel_config_flow(self, flow_id):
        self.cancelled.append(flow_id)


@pytest.fixture
def ui_helper_tools(monkeypatch):
    mcp = _FakeMCP()
    ui_helpers.register_ui_helper_tools(mcp)
    confirm = AsyncMock(return_value=True)
    monkeypatch.setattr(ui_helpers, "confirm_change", confirm)
    rest = _FakeREST()
    monkeypatch.setattr(ui_helpers, "get_clients", lambda _ctx: (None, rest))
    return mcp.tools, rest, confirm


async def test_create_sensor_group_uses_group_config_flow(ui_helper_tools):
    tools, rest, confirm = ui_helper_tools

    result = await tools["create_group_helper"](
        object(),
        name="Outdoor temperatures",
        group_type="sensor",
        entities=["sensor.outdoor_a", "sensor.outdoor_b"],
        hide_members=True,
        statistic_type="mean",
    )

    assert json.loads(result)["entity_type"] == "group"
    assert rest.handler == "group"
    assert rest.steps == [
        ("group-flow", {"next_step_id": "sensor"}),
        (
            "group-flow",
            {
                "name": "Outdoor temperatures",
                "entities": ["sensor.outdoor_a", "sensor.outdoor_b"],
                "hide_members": True,
                "type": "mean",
            },
        ),
    ]
    assert rest.cancelled == []
    confirm.assert_awaited_once()


async def test_create_binary_sensor_group_passes_all_option(ui_helper_tools):
    tools, rest, _confirm = ui_helper_tools

    result = await tools["create_group_helper"](
        object(),
        name="All windows closed",
        group_type="binary_sensor",
        entities=["binary_sensor.window_1", "binary_sensor.window_2"],
        all_entities_on=True,
    )

    assert json.loads(result)["status"] == "created"
    assert rest.steps[-1][1] == {
        "name": "All windows closed",
        "entities": ["binary_sensor.window_1", "binary_sensor.window_2"],
        "hide_members": False,
        "all": True,
    }


async def test_create_group_rejects_sensor_group_without_measure(ui_helper_tools):
    tools, rest, confirm = ui_helper_tools

    result = await tools["create_group_helper"](
        object(),
        name="Outdoor temperatures",
        group_type="sensor",
        entities=["sensor.outdoor_a"],
    )

    assert "require a statistic_type" in json.loads(result)["error"]
    assert rest.steps == []
    confirm.assert_not_awaited()


async def test_create_integral_sensor_uses_integration_config_flow(
    ui_helper_tools,
):
    tools, rest, confirm = ui_helper_tools

    result = await tools["create_integral_sensor"](
        object(),
        name="Energy used",
        source_sensor="sensor.power",
        unit_time="hours",
        method="left",
        unit_prefix="k",
        round_digits=2,
    )

    assert json.loads(result) == {
        "status": "created",
        "entity_type": "integral sensor",
        "name": "Energy used",
        "result": True,
    }
    assert rest.handler == "integration"
    assert rest.steps == [
        (
            "integral-flow",
            {
                "name": "Energy used",
                "source": "sensor.power",
                "unit_time": "h",
                "method": "left",
                "unit_prefix": "k",
                "round": 2,
            },
        ),
    ]
    assert rest.cancelled == []
    confirm.assert_awaited_once()


@pytest.mark.parametrize(
    ("kwargs", "expected_error"),
    [
        (
            {
                "name": "Energy used",
                "source_sensor": "light.lamp",
            },
            "source_sensor must belong",
        ),
        (
            {
                "name": "Energy used",
                "source_sensor": "sensor.power",
                "method": "invalid",
            },
            "Invalid method",
        ),
        (
            {
                "name": "Energy used",
                "source_sensor": "sensor.power",
                "round_digits": 7,
            },
            "round_digits must be between",
        ),
    ],
)
async def test_create_integral_sensor_validates_inputs(
    ui_helper_tools, kwargs, expected_error
):
    tools, rest, confirm = ui_helper_tools
    kwargs.setdefault("unit_time", "hours")
    kwargs.setdefault("method", "trapezoidal")

    result = await tools["create_integral_sensor"](object(), **kwargs)

    assert expected_error in json.loads(result)["error"]
    assert rest.steps == []
    confirm.assert_not_awaited()


async def test_invalid_group_config_flow_is_cancelled(ui_helper_tools):
    tools, rest, _confirm = ui_helper_tools
    rest.final_response = {
        "type": "form",
        "step_id": "sensor",
        "errors": {"entities": "invalid_entity"},
    }

    result = await tools["create_group_helper"](
        object(),
        name="Outdoor temperatures",
        group_type="sensor",
        entities=["sensor.outdoor_a"],
        statistic_type="mean",
    )

    response = json.loads(result)
    assert "did not create the group" in response["error"]
    assert rest.cancelled == ["group-flow"]

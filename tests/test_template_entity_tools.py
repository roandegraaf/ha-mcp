import json
from unittest.mock import AsyncMock

import pytest

from ha_mcp.ha_client.rest import HARestClient
from ha_mcp.tools import template_entity


class _FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register


class _FakeREST:
    def __init__(self, final_response=None):
        self.final_response = final_response or {
            "type": "create_entry",
            "title": "Test entity",
            "result": True,
        }
        self.steps = []
        self.cancelled = []

    async def start_config_flow(self, handler):
        assert handler == "template"
        return {"type": "menu", "flow_id": "flow-1"}

    async def submit_config_flow_step(self, flow_id, user_input):
        self.steps.append((flow_id, user_input))
        if len(self.steps) == 1:
            return {"type": "form", "step_id": user_input["next_step_id"]}
        return self.final_response

    async def cancel_config_flow(self, flow_id):
        self.cancelled.append(flow_id)


@pytest.fixture
def template_tools(monkeypatch):
    mcp = _FakeMCP()
    template_entity.register_template_entity_tools(mcp)
    confirm = AsyncMock(return_value=True)
    monkeypatch.setattr(template_entity, "confirm_change", confirm)
    rest = _FakeREST()
    monkeypatch.setattr(
        template_entity, "get_clients", lambda _ctx: (None, rest)
    )
    return mcp.tools, rest, confirm


async def test_create_template_sensor_runs_config_flow(template_tools):
    tools, rest, confirm = template_tools

    result = await tools["create_template_sensor"](
        object(),
        name="Indoor temperature",
        state_template="{{ states('sensor.raw_temperature') }}",
        device_class="temperature",
        unit_of_measurement="°C",
        state_class="measurement",
    )

    assert json.loads(result) == {
        "status": "created",
        "entity_type": "sensor",
        "name": "Indoor temperature",
        "result": True,
    }
    assert rest.steps == [
        ("flow-1", {"next_step_id": "sensor"}),
        (
            "flow-1",
            {
                "name": "Indoor temperature",
                "state": "{{ states('sensor.raw_temperature') }}",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "state_class": "measurement",
            },
        ),
    ]
    assert rest.cancelled == []
    confirm.assert_awaited_once()


async def test_create_template_binary_sensor_runs_config_flow(template_tools):
    tools, rest, _confirm = template_tools

    result = await tools["create_template_binary_sensor"](
        object(),
        name="Garage occupied",
        state_template="{{ is_state('binary_sensor.garage_motion', 'on') }}",
        device_class="occupancy",
    )

    assert json.loads(result)["entity_type"] == "binary_sensor"
    assert rest.steps == [
        ("flow-1", {"next_step_id": "binary_sensor"}),
        (
            "flow-1",
            {
                "name": "Garage occupied",
                "state": "{{ is_state('binary_sensor.garage_motion', 'on') }}",
                "device_class": "occupancy",
            },
        ),
    ]
    assert rest.cancelled == []


async def test_invalid_config_flow_response_is_reported_and_cancelled(
    template_tools,
):
    tools, rest, _confirm = template_tools
    rest.final_response = {
        "type": "form",
        "step_id": "sensor",
        "errors": {"state": "invalid_template"},
    }

    result = await tools["create_template_sensor"](
        object(),
        name="Indoor temperature",
        state_template="{{ invalid",
    )

    response = json.loads(result)
    assert "did not create" in response["error"]
    assert response["flow"]["errors"] == {"state": "invalid_template"}
    assert rest.cancelled == ["flow-1"]


async def test_empty_template_input_is_rejected_without_starting_flow(
    template_tools,
):
    tools, rest, confirm = template_tools

    result = await tools["create_template_binary_sensor"](
        object(),
        name="Garage occupied",
        state_template=" ",
    )

    assert json.loads(result) == {"error": "state_template must not be empty"}
    assert rest.steps == []
    assert rest.cancelled == []
    confirm.assert_not_awaited()


async def test_rest_config_flow_methods_use_home_assistant_api():
    rest = HARestClient("http://ha.local", "token")
    rest._request = AsyncMock(
        side_effect=[
            {"flow_id": "flow-1"},
            {"type": "form"},
            {"type": "abort"},
        ]
    )

    await rest.start_config_flow("template")
    await rest.submit_config_flow_step("flow/1", {"next_step_id": "sensor"})
    await rest.cancel_config_flow("flow/1")

    assert rest._request.await_args_list == [
        (
            ("POST", "/api/config/config_entries/flow"),
            {"json": {"handler": "template"}},
        ),
        (
            ("POST", "/api/config/config_entries/flow/flow%2F1"),
            {"json": {"next_step_id": "sensor"}},
        ),
        (
            ("DELETE", "/api/config/config_entries/flow/flow%2F1"),
            {},
        ),
    ]

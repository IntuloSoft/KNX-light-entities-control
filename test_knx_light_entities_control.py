import pytest
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from mocks.mock_blueprint import MockBlueprint
from mocks.mock_light import MockLight

@pytest.fixture
async def mock(hass: HomeAssistant):
    mock =  MockBlueprint(hass)
    await mock.register_on_knx_transmit()
    await mock.add_test_light("light.test")

    assert await async_setup_component(
        hass,
        "input_boolean",
        {
            "input_boolean": {
                "dimmer": {}
            }
        },
    )

    blueprint_path = Path(__file__).parent / "blueprints" / "knx-light-entities-control.yaml"

    blueprint_filename = await mock.load_blueprint_from_file(blueprint_path)
    await mock.load_blueprint_instance(
        blueprint_filename=blueprint_filename,
        inputs={
            "light_entity": "light.test",
            "dimm_entity": "input_boolean.dimmer",
            "switch_address": "1/1/0",
            "switch_state_address": "1/1/1",
        },
    )

    return mock

async def test_light_can_turn_on(mock):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
        },
        blocking=True,
    )

    mock.assert_state("light.test", "on")

async def test_knx_switch_turns_light_on(mock: MockBlueprint):

    await mock.send_knx_group_value_write(
        "1/1/0",
        1,
    )

    mock.assert_state(
        "light.test",
        "on",
    )

    mock.assert_last_knx_group_value_write(
        "1/1/1",
        1,
    )

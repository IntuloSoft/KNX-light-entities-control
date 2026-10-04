import pytest
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from mocks.mock_blueprint import (
    MockBlueprint, 
    DPT,
)

from mocks.mock_light import MockLight

SWITCH_ADDRESS              = "1/1/0"
SWITCH_STATE_ADDRESS        = "1/1/1"
DIMM_ADDRESS                = "1/1/2"
VALUE_ADDRESS               = "1/1/3"
VALUE_STATE_ADDRESS         = "1/1/4"
TEMPERATURE_ADDRESS         = "1/1/5"
TEMPERATURE_STATE_ADDRESS   = "1/1/6"
RGB_COLOR_ADDRESS           = "1/1/7"
RGB_COLOR_STATE_ADDRESS     = "1/1/8"


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
            "switch_address": SWITCH_ADDRESS,
            "switch_state_address": SWITCH_STATE_ADDRESS,
            "value_address": VALUE_ADDRESS,
            "value_state_address": VALUE_STATE_ADDRESS,
        },
    )

    return mock


async def test_light_can_turn_on(mock: MockBlueprint):

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
        SWITCH_ADDRESS,
        DPT.binary(1),
    )

    mock.assert_state(
        "light.test",
        "on",
    )

    mock.assert_last_knx_group_value_write(
        SWITCH_STATE_ADDRESS,
        DPT.binary(1),
    )

async def test_knx_brightness_turns_light_on(mock: MockBlueprint):

    await mock.send_knx_group_value_write(
        VALUE_ADDRESS,
        DPT.percent(128),
    )

    mock.assert_state(
        "light.test",
        "on",
    )

    assert (
        mock.hass.states.get("light.test")
        .attributes["brightness"]
        == 128
    )

async def test_light_brightness_feedback(mock: MockBlueprint):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 128,
        },
        blocking=True,
    )
    await mock.wait_for_idle()

    mock.assert_last_knx_group_value_write(
        VALUE_STATE_ADDRESS,
        DPT.percent(128),
    )

async def test_knx_brightness_zero_turns_light_off(mock: MockBlueprint):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
        },
        blocking=True,
    )

    await mock.send_knx_group_value_write(
        VALUE_ADDRESS,
        DPT.percent(0),
    )

    mock.assert_state(
        "light.test",
        "off",
    )

async def test_knx_brightness_read_request(mock: MockBlueprint):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 180,
        },
        blocking=True,
    )
    await mock.wait_for_idle()

    mock.clear_knx_tx()

    await mock.send_knx_group_value_read(
        VALUE_STATE_ADDRESS,
    )
    
    await mock.wait_for_idle()

    mock.assert_last_knx_group_value_response(
        VALUE_STATE_ADDRESS,
        DPT.percent(180),
    )

    mock.clear_knx_tx()

    await mock.send_knx_group_value_read(
        VALUE_ADDRESS,
    )
    
    await mock.wait_for_idle()
    
    assert len(mock.tx_telegrams) == 0
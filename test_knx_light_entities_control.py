import pytest
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from mocks.mock_blueprint import (
    MockBlueprint, 
    DPT,
    KnxTelegram,
)

from xknx.telegram.apci import (
    GroupValueRead,
    GroupValueWrite,
    GroupValueResponse,
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
    await mock.add_input_boolean("dimmer")

    blueprint_path = Path(__file__).parent / "blueprints" / "knx-light-entities-control.yaml"

    blueprint_filename = await mock.load_blueprint_from_file(blueprint_path)

    await mock.load_blueprint_instance(
        blueprint_filename=blueprint_filename,
        inputs={
            "light_entity": "light.test",
            "dimm_entity": "input_boolean.dimmer",
            "switch_address": SWITCH_ADDRESS,
            "switch_state_address": SWITCH_STATE_ADDRESS,
            "dimm_address": DIMM_ADDRESS,
            "value_address": VALUE_ADDRESS,
            "value_state_address": VALUE_STATE_ADDRESS,
            "temperature_address": TEMPERATURE_ADDRESS,
            "temperature_state_address": TEMPERATURE_STATE_ADDRESS,
            "rgb_color_address": RGB_COLOR_ADDRESS,
            "rgb_color_state_address": RGB_COLOR_STATE_ADDRESS,
        },
    )

    yield mock

    mock.close()


@pytest.fixture
async def mock_input_number_dimming(hass: HomeAssistant):
    mock =  MockBlueprint(hass)
    await mock.register_on_knx_transmit()
    await mock.add_test_light("light.test")
    await mock.add_input_number("dimmer", min_value = 0, max_value = 65536)

    blueprint_path = Path(__file__).parent / "blueprints" / "knx-light-entities-control.yaml"

    blueprint_filename = await mock.load_blueprint_from_file(blueprint_path)

    await mock.load_blueprint_instance(
        blueprint_filename=blueprint_filename,
        inputs={
            "light_entity": "light.test",
            "dimm_entity": "input_number.dimmer",
            "switch_address": SWITCH_ADDRESS,
            "switch_state_address": SWITCH_STATE_ADDRESS,
            "dimm_address": DIMM_ADDRESS,
            "value_address": VALUE_ADDRESS,
            "value_state_address": VALUE_STATE_ADDRESS,
            "temperature_address": TEMPERATURE_ADDRESS,
            "temperature_state_address": TEMPERATURE_STATE_ADDRESS,
            "rgb_color_address": RGB_COLOR_ADDRESS,
            "rgb_color_state_address": RGB_COLOR_STATE_ADDRESS,
        },
    )

    yield mock

    mock.close()

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
    await mock.advance_time_ms(1)

    mock.assert_state(
        "light.test",
        "on",
    )

    mock.assert_knx_telegrams(
        [
            KnxTelegram(SWITCH_STATE_ADDRESS, GroupValueWrite, DPT.binary(1))
        ]
    )

async def test_knx_switch_read_request(mock: MockBlueprint):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
        },
        blocking=True,
    )
    await mock.wait_for_idle()

    mock.clear_knx_tx()

    await mock.send_knx_group_value_read(
        SWITCH_STATE_ADDRESS,
    )
    
    await mock.wait_for_idle()

    mock.assert_knx_telegrams(
        [
            KnxTelegram(SWITCH_STATE_ADDRESS, GroupValueResponse, DPT.binary(1))
        ]
    )

    mock.clear_knx_tx()

    await mock.send_knx_group_value_read(
        SWITCH_ADDRESS,
    )
    
    await mock.wait_for_idle()
    
    assert len(mock.tx_telegrams) == 0
    mock.assert_knx_telegrams([])

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

    mock.assert_knx_telegrams(
        [
            KnxTelegram(SWITCH_STATE_ADDRESS, GroupValueWrite, DPT.binary(1)),
            KnxTelegram(VALUE_STATE_ADDRESS, GroupValueWrite, DPT.percent(128))
        ]
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

    mock.assert_knx_telegrams(
        [
            KnxTelegram(VALUE_STATE_ADDRESS, GroupValueResponse, DPT.percent(180))
        ]
    )

    mock.clear_knx_tx()

    await mock.send_knx_group_value_read(
        VALUE_ADDRESS,
    )
    
    await mock.wait_for_idle()

    assert len(mock.tx_telegrams) == 0

async def test_knx_rgb_turns_light_on(
    mock: MockBlueprint,
):

    await mock.send_knx_group_value_write(
        RGB_COLOR_ADDRESS,
        DPT.rgb(255, 0, 0),
    )

    state = mock.hass.states.get(
        "light.test"
    )

    assert state.state == "on"

    assert (
        state.attributes["rgb_color"]
        == (255, 0, 0)
    )

async def test_light_rgb_feedback(
    mock: MockBlueprint,
):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "rgb_color": (255, 0, 0),
        },
        blocking=True,
    )

    await mock.wait_for_idle()

    mock.assert_knx_telegrams(
        [
            KnxTelegram(SWITCH_STATE_ADDRESS, GroupValueWrite, DPT.binary(True)),
            KnxTelegram(
                RGB_COLOR_STATE_ADDRESS,
                GroupValueWrite,
                DPT.rgb(255, 0, 0),
            ),
        ]
    )

async def test_knx_rgb_read_request(
    mock: MockBlueprint,
):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "rgb_color": (255, 0, 0),
        },
        blocking=True,
    )

    await mock.wait_for_idle()

    mock.tx_telegrams.clear()

    await mock.send_knx_group_value_read(RGB_COLOR_STATE_ADDRESS)

    await mock.wait_for_idle()

    mock.assert_knx_telegrams(
        [
            KnxTelegram(
                RGB_COLOR_STATE_ADDRESS,
                GroupValueResponse,
                DPT.rgb(255, 0, 0),
            ),
        ]
    )

    mock.clear_knx_tx()

    await mock.send_knx_group_value_read(RGB_COLOR_ADDRESS)
    
    await mock.wait_for_idle()

    mock.assert_knx_telegrams([])

async def test_knx_cct_turns_light_on(
    mock: MockBlueprint,
):

    await mock.send_knx_group_value_write(
        TEMPERATURE_ADDRESS,
        DPT.color_temperature(3000),
    )

    state = mock.hass.states.get(
        "light.test"
    )

    assert state.state == "on"

    assert (
        state.attributes["color_temp_kelvin"]
        == 3000
    )

async def test_light_cct_feedback(
    mock: MockBlueprint,
):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "color_temp_kelvin": 3000,
        },
        blocking=True,
    )

    await mock.wait_for_idle()


    mock.assert_knx_telegrams(
        [
            KnxTelegram(
                SWITCH_STATE_ADDRESS,
                GroupValueWrite,
                DPT.binary(True),
            ),
            KnxTelegram(
                TEMPERATURE_STATE_ADDRESS,
                GroupValueWrite,
                DPT.color_temperature(3000),
            ),
            KnxTelegram(
                RGB_COLOR_STATE_ADDRESS,
                GroupValueWrite,
                DPT.rgb(255, 177, 110),
            ),
        ]
    )
    

async def test_knx_cct_read_request(
    mock: MockBlueprint,
):

    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "color_temp_kelvin": 3000,
        },
        blocking=True,
    )

    await mock.wait_for_idle()

    mock.tx_telegrams.clear()

    await mock.send_knx_group_value_read(
        TEMPERATURE_STATE_ADDRESS,
    )

    await mock.wait_for_idle()

    mock.assert_knx_telegrams(
        [
            KnxTelegram(
                TEMPERATURE_STATE_ADDRESS,
                GroupValueResponse,
                DPT.color_temperature(3000),
            ),
        ]
    )

    mock.clear_knx_tx()

    await mock.send_knx_group_value_read(
        TEMPERATURE_ADDRESS,
    )
    
    await mock.wait_for_idle()

    mock.assert_knx_telegrams([])


async def test_classic_dim_up_to_max(mock_input_number_dimming):
    mock = mock_input_number_dimming
    
    #
    # Start at 0%
    #
    await mock.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 0,
        },
        blocking=True,
    )

    await mock.wait_for_idle()

    #
    # Start dim up
    #
    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_up(7),
    )

    #
    # Let the full dim process finish
    #
    await mock.advance_time_ms(
        30000,
    )

    state = mock.hass.states.get(
        "light.test"
    )

    assert (
        state.attributes["brightness"]
        == 255
    )


async def test_advanced_dim_up_feedback_steps(
    mock_input_number_dimming,
):
    await mock_input_number_dimming.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 0,
        },
        blocking=True,
    )

    mock_input_number_dimming.clear_knx_tx()

    await mock_input_number_dimming.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_up(),
    )

    INTERVAL_MS = 260
    MARGIN_MS = 10
    FINAL_STEP_MS = int((255 - 247) * INTERVAL_MS / 13)

    test_data = [
        {"time": 1 * INTERVAL_MS - MARGIN_MS, "telegrams": 0},
        {"time": 1 * INTERVAL_MS + MARGIN_MS, "telegrams": 2},

        {"time": 2 * INTERVAL_MS - MARGIN_MS, "telegrams": 2},
        {"time": 2 * INTERVAL_MS + MARGIN_MS, "telegrams": 3},

        {"time": 3 * INTERVAL_MS - MARGIN_MS, "telegrams": 3},
        {"time": 3 * INTERVAL_MS + MARGIN_MS, "telegrams": 4},

        {"time": 4 * INTERVAL_MS - MARGIN_MS, "telegrams": 4},
        {"time": 4 * INTERVAL_MS + MARGIN_MS, "telegrams": 5},

        {"time": 5 * INTERVAL_MS - MARGIN_MS, "telegrams": 5},
        {"time": 5 * INTERVAL_MS + MARGIN_MS, "telegrams": 6},

        {"time": 6 * INTERVAL_MS - MARGIN_MS, "telegrams": 6},
        {"time": 6 * INTERVAL_MS + MARGIN_MS, "telegrams": 7},

        {"time": 7 * INTERVAL_MS - MARGIN_MS, "telegrams": 7},
        {"time": 7 * INTERVAL_MS + MARGIN_MS, "telegrams": 8},

        {"time": 8 * INTERVAL_MS - MARGIN_MS, "telegrams": 8},
        {"time": 8 * INTERVAL_MS + MARGIN_MS, "telegrams": 9},

        {"time": 9 * INTERVAL_MS - MARGIN_MS, "telegrams": 9},
        {"time": 9 * INTERVAL_MS + MARGIN_MS, "telegrams": 10},

        {"time": 10 * INTERVAL_MS - MARGIN_MS, "telegrams": 10},
        {"time": 10 * INTERVAL_MS + MARGIN_MS, "telegrams": 11},

        {"time": 11 * INTERVAL_MS - MARGIN_MS, "telegrams": 11},
        {"time": 11 * INTERVAL_MS + MARGIN_MS, "telegrams": 12},

        {"time": 12 * INTERVAL_MS - MARGIN_MS, "telegrams": 12},
        {"time": 12 * INTERVAL_MS + MARGIN_MS, "telegrams": 13},

        {"time": 13 * INTERVAL_MS - MARGIN_MS, "telegrams": 13},
        {"time": 13 * INTERVAL_MS + MARGIN_MS, "telegrams": 14},

        {"time": 14 * INTERVAL_MS - MARGIN_MS, "telegrams": 14},
        {"time": 14 * INTERVAL_MS + MARGIN_MS, "telegrams": 15},

        {"time": 15 * INTERVAL_MS - MARGIN_MS, "telegrams": 15},
        {"time": 15 * INTERVAL_MS + MARGIN_MS, "telegrams": 16},

        {"time": 16 * INTERVAL_MS - MARGIN_MS, "telegrams": 16},
        {"time": 16 * INTERVAL_MS + MARGIN_MS, "telegrams": 17},

        {"time": 17 * INTERVAL_MS - MARGIN_MS, "telegrams": 17},
        {"time": 17 * INTERVAL_MS + MARGIN_MS, "telegrams": 18},

        {"time": 18 * INTERVAL_MS - MARGIN_MS, "telegrams": 18},
        {"time": 18 * INTERVAL_MS + MARGIN_MS, "telegrams": 19},

        {"time": 19 * INTERVAL_MS - MARGIN_MS, "telegrams": 19},
        {"time": 19 * INTERVAL_MS + MARGIN_MS, "telegrams": 20},

        {"time": 19 * INTERVAL_MS + FINAL_STEP_MS - MARGIN_MS, "telegrams": 20},
        {"time": 19 * INTERVAL_MS + FINAL_STEP_MS + MARGIN_MS, "telegrams": 21},
    ]


    previous_time = 0

    for checkpoint in test_data:
        await mock_input_number_dimming.advance_time_ms(
            checkpoint["time"] - previous_time,
        )

        assert (
            len(mock_input_number_dimming.tx_telegrams)
            == checkpoint["telegrams"]
        ), (
            f"At t={checkpoint['time']} ms "
            f"expected {checkpoint['telegrams']} telegrams "
            f"but got {len(mock_input_number_dimming.tx_telegrams)}"
        )

        previous_time = checkpoint["time"]

    mock_input_number_dimming.assert_knx_telegrams(
        [
            KnxTelegram("1/1/1", GroupValueWrite, DPT.binary(True)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(13)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(26)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(39)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(52)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(65)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(78)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(91)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(104)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(117)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(130)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(143)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(156)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(169)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(182)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(195)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(208)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(221)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(234)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(247)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(255)),
        ]
    )

async def test_advanced_dim_up_feedback_steps2(
    mock_input_number_dimming,
):
    await mock_input_number_dimming.hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 0,
        },
        blocking=True,
    )

    mock_input_number_dimming.clear_knx_tx()

    await mock_input_number_dimming.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_up(),
    )

    assert len(mock_input_number_dimming.tx_telegrams) == 0, mock_input_number_dimming.tx_telegrams

    DIMM_TELEGRAM_INTERVAL = 200

    #
    # vóór eerste interval
    #
    await mock_input_number_dimming.advance_time_ms(
        30000,
    )

    assert len(mock_input_number_dimming.tx_telegrams) == 21

    mock_input_number_dimming.assert_knx_telegrams(
        [
            KnxTelegram('1/1/1', GroupValueWrite, DPT.binary(True)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(13)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(26)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(39)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(52)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(65)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(78)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(91)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(104)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(117)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(130)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(143)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(156)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(169)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(182)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(195)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(208)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(221)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(234)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(247)), 
            KnxTelegram('1/1/4', GroupValueWrite, DPT.percent(255))
        ]
    )

    #
    # eerste interval
    #
    # await mock_input_number_dimming.advance_time_ms(
    #     1,
    # )

    # assert len(
    #     mock_input_number_dimming.tx_telegrams
    # ) == 1

    # print(
    #     mock_input_number_dimming.tx_telegrams
    # )

    # #
    # # tweede interval
    # #
    # await mock_input_number_dimming.advance_time_ms(
    #     DIMM_TELEGRAM_INTERVAL,
    # )

    # assert len(
    #     mock_input_number_dimming.tx_telegrams
    # ) == 2

    # print(
    #     mock_input_number_dimming.tx_telegrams
    # )

    # #
    # # derde interval
    # #
    # await mock_input_number_dimming.advance_time_ms(
    #     DIMM_TELEGRAM_INTERVAL,
    # )

    # assert len(
    #     mock_input_number_dimming.tx_telegrams
    # ) == 3

    # print(
    #     mock_input_number_dimming.tx_telegrams
    # )


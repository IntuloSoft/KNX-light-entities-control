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

class MockKnxLight(MockBlueprint):
    def __init__(self, hass, mode):
        super().__init__(hass)
        self.mode = mode

    async def light_turn_on(
            mock,
            entity = "light.test",
            brightness = None,
            rgb_color = None,
            color_temp_kelvin = None,
        ):
        cfg = {
            "entity_id": entity,
        }
        if brightness is not None:
            cfg["brightness"] = brightness
        
        if rgb_color is not None:
            cfg["rgb_color"] = rgb_color

        if color_temp_kelvin is not None:
            cfg["color_temp_kelvin"] = color_temp_kelvin
            
        await mock.hass.services.async_call(
            "light",
            "turn_on",
            cfg,
            blocking=True,
        )

        await mock.advance_time_ms(1)


@pytest.fixture
async def mock(request, hass: HomeAssistant):
    if isinstance(request.param, dict):
        mode = request.param["mode"]
    else:
        mode = request.param

    assert mode in [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ]

    transition_supported = mode not in [
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ]


    mock =  MockKnxLight(hass,mode)
    await mock.register_on_knx_transmit()
    await mock.register_on_logger()
    await mock.add_test_light("light.test",transition_supported)

    inputs={
        "light_entity": "light.test",
        "switch_address": SWITCH_ADDRESS,
        "switch_state_address": SWITCH_STATE_ADDRESS,
        "dimm_address": DIMM_ADDRESS,
        "value_address": VALUE_ADDRESS,
        "value_state_address": VALUE_STATE_ADDRESS,
        "temperature_address": TEMPERATURE_ADDRESS,
        "temperature_state_address": TEMPERATURE_STATE_ADDRESS,
        "rgb_color_address": RGB_COLOR_ADDRESS,
        "rgb_color_state_address": RGB_COLOR_STATE_ADDRESS,
    }

    if isinstance(request.param, dict):
        for key, value in request.param.items():
            if key != "mode":
                inputs[key] = value
    
    if mode == "Step":
        await mock.add_input_boolean("dimmer")
        inputs["dimm_entity"] = "input_boolean.dimmer"
    elif mode in [
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ]:
        await mock.add_input_number("dimmer", min_value = 0, max_value = 65536)
        inputs["dimm_entity"] = "input_number.dimmer"

    blueprint_path = Path(__file__).parent / "blueprints" / "knx-light-entities-control.yaml"

    blueprint_filename = await mock.load_blueprint_from_file(blueprint_path)

    await mock.load_blueprint_instance(
        blueprint_filename=blueprint_filename,
        inputs=inputs,
    )

    yield mock

    mock.close()

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_light_can_turn_on(mock: MockBlueprint):

    await mock.light_turn_on()

    mock.assert_state("light.test", "on")

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_knx_switch_read_request(mock: MockBlueprint):

    await mock.light_turn_on()
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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_light_brightness_feedback(mock: MockBlueprint):

    await mock.light_turn_on(brightness=128)

    mock.assert_knx_telegrams(
        [
            KnxTelegram(SWITCH_STATE_ADDRESS, GroupValueWrite, DPT.binary(1)),
            KnxTelegram(VALUE_STATE_ADDRESS, GroupValueWrite, DPT.percent(128))
        ]
    )

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_knx_brightness_zero_turns_light_off(mock: MockBlueprint):

    await mock.light_turn_on()

    await mock.send_knx_group_value_write(
        VALUE_ADDRESS,
        DPT.percent(0),
    )

    mock.assert_state(
        "light.test",
        "off",
    )

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_knx_brightness_read_request(mock: MockBlueprint):

    await mock.light_turn_on(brightness=180)
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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_light_rgb_feedback(
    mock: MockBlueprint,
):
    await mock.light_turn_on(rgb_color=(255, 0, 0))
    
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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_knx_rgb_read_request(
    mock: MockBlueprint,
):
    await mock.light_turn_on(rgb_color=(255,0,0))
    mock.clear_knx_tx()

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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
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

@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_light_cct_feedback(
    mock: MockBlueprint,
):
    await mock.light_turn_on(color_temp_kelvin=3000)

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
    
@pytest.mark.parametrize(
    "mock",
    [
        "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_knx_cct_read_request(
    mock: MockBlueprint,
):
    await mock.light_turn_on(color_temp_kelvin=3000)
    mock.clear_knx_tx()

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

async def verify_timed_telegrams(
    mock,
    test_data,
):
    previous_time = 0
    consumed_idx = 0

    for item in test_data:
        expected_time = item["time"]
        early_offset, late_offset = item["window"]

        latest_time = expected_time + late_offset

        expected_telegram = item["telegram"]

        await mock.advance_time_ms(
            latest_time - previous_time
        )

        previous_time = latest_time

        remaining = mock.tx_telegrams[consumed_idx:]

        try:
            relative_idx = remaining.index(
                expected_telegram
            )
        except ValueError:
            raise AssertionError(
                f"Telegram not received before deadline:\n"
                f"Expected: {expected_telegram}\n"
                f"Latest allowed: {latest_time} ms\n"
                f"\n"
                f"Remaining telegrams:\n"
                + (
                    "\n".join(
                        f"  [{consumed_idx+i}] {t}"
                        for i, t in enumerate(remaining)
                    )
                    if remaining
                    else "  <none>"
                )
            )

        consumed_idx += relative_idx + 1

    remaining = mock.tx_telegrams[consumed_idx:]

    assert not remaining, (
        "Unexpected telegrams transmitted:\n"
        + "\n".join(str(t) for t in remaining)
    )

@pytest.mark.parametrize(
    "mock",
    [
        # "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_dim_up_feedback_steps(
    mock,
):
    await mock.light_turn_on(brightness=0)
    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_up(),
    )

    INTERVAL_MS = 255
    MARGIN_MS = 10
    FINAL_BRIGHTNESS_STEP = 255 - 247
    FINAL_STEP_MS = int(FINAL_BRIGHTNESS_STEP * INTERVAL_MS / 13)

    test_data = [
        {"time":  1 * INTERVAL_MS,                 "window": (-INTERVAL_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/1", GroupValueWrite, DPT.binary(True))},
        {"time":  1 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(13))},
        {"time":  2 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(26))},
        {"time":  3 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(39))},
        {"time":  4 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(52))},
        {"time":  5 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(65))},
        {"time":  6 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(78))},
        {"time":  7 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(91))},
        {"time":  8 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(104))},
        {"time":  9 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(117))},
        {"time": 10 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(130))},
        {"time": 11 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(143))},
        {"time": 12 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(156))},
        {"time": 13 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(169))},
        {"time": 14 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(182))},
        {"time": 15 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(195))},
        {"time": 16 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(208))},
        {"time": 17 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(221))},
        {"time": 18 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(234))},
        {"time": 19 * INTERVAL_MS,                 "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(247))},
        {"time": 19 * INTERVAL_MS + FINAL_STEP_MS, "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(255))},
        # {"time": 19 * INTERVAL_MS + FINAL_STEP_MS, "window": (  -MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(255))},
    ]

    await verify_timed_telegrams(mock,test_data)
    


@pytest.mark.parametrize(
    "mock",
    [
        # "Disabled_NoEntity",
        {"mode":"Step",                                     "dimm_no_on": True},
        {"mode":"TransitionStep",                           "dimm_no_on": True},
        {"mode":"Transition",                               "dimm_no_on": True},
        {"mode":"TransitionStep_TransitionNotSupported",    "dimm_no_on": True},
        {"mode":"Transition_TransitionNotSupported",        "dimm_no_on": True},
    ],
    indirect=True,
)
async def test_dim_prevent_turn_on_switch_on_feedback_steps(
    mock,
):
    await mock.light_turn_on(brightness=0)
    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_up(),
    )

    await mock.advance_time_ms(1000)
    assert len(mock.tx_telegrams) == 0


@pytest.mark.parametrize(
    "mock",
    [
        # "Disabled_NoEntity",
        # "Disabled",
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_dim_down_feedback_steps(
    mock,
):
    await mock.light_turn_on(brightness=255)
    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_down(),
    )

    INTERVAL_MS = 255
    MARGIN_MS = 10

    test_data = [
        {"time":  1 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(242))},
        {"time":  2 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(229))},
        {"time":  3 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(216))},
        {"time":  4 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(203))},
        {"time":  5 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(190))},
        {"time":  6 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(177))},
        {"time":  7 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(164))},
        {"time":  8 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(151))},
        {"time":  9 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(138))},
        {"time": 10 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(125))},
        {"time": 11 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(112))},
        {"time": 12 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 99))},
        {"time": 13 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 86))},
        {"time": 14 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 73))},
        {"time": 15 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 60))},
        {"time": 16 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 47))},
        {"time": 17 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 34))},
        {"time": 18 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 21))},
        {"time": 19 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(  8))},
        {"time": 20 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/1", GroupValueWrite, DPT.binary(False))},
        {"time": 20 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(  0))},
    ]
    
    await verify_timed_telegrams(mock,test_data)


@pytest.mark.parametrize(
    "mock",
    [
        # "Disabled_NoEntity",
        {"mode":"Step",                                     "dimm_no_off": True},
        {"mode":"TransitionStep",                           "dimm_no_off": True},
        {"mode":"Transition",                               "dimm_no_off": True},
        {"mode":"TransitionStep_TransitionNotSupported",    "dimm_no_off": True},
        {"mode":"Transition_TransitionNotSupported",        "dimm_no_off": True},
    ],
    indirect=True,
)
async def test_dim_down_no_off_feedback_steps(
    mock,
):
    await mock.light_turn_on(brightness=255)
    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_down(),
    )

    INTERVAL_MS = 255
    MARGIN_MS = 10

    test_data = [
        {"time":  1 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(242))},
        {"time":  2 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(229))},
        {"time":  3 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(216))},
        {"time":  4 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(203))},
        {"time":  5 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(190))},
        {"time":  6 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(177))},
        {"time":  7 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(164))},
        {"time":  8 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(151))},
        {"time":  9 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(138))},
        {"time": 10 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(125))},
        {"time": 11 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(112))},
        {"time": 12 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 99))},
        {"time": 13 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 86))},
        {"time": 14 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 73))},
        {"time": 15 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 60))},
        {"time": 16 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 47))},
        {"time": 17 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 34))},
        {"time": 18 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent( 21))},
        {"time": 19 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(  8))},
        {"time": 20 * INTERVAL_MS, "window": (-MARGIN_MS, +MARGIN_MS), "telegram": KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(  1))},
    ]

    await verify_timed_telegrams(mock,test_data)
    
    await mock.advance_time_ms(1000)
    assert len(mock.tx_telegrams) == 20


@pytest.mark.parametrize(
    "mock",
    [
        # "Disabled_NoEntity",
        # "Disabled",
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_dim_up_stop(
    mock,
):
    await mock.light_turn_on(brightness=0)
    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_up(),
    )

    await mock.advance_time_ms(800)

    mock.assert_knx_telegrams(
        [
            KnxTelegram("1/1/1", GroupValueWrite, DPT.binary(True)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(13)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(26)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(39)),
        ]
    )

    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_stop(),
    )

    await mock.advance_time_ms(10)

    if mock.mode in ["Step"]:
        assert len(mock.tx_telegrams) == 0
    else:
        assert len(mock.tx_telegrams) == 1
        assert mock.tx_telegrams[0].dpt.payload in [40,41,42,43] 
    


@pytest.mark.parametrize(
    "mock",
    [
        # "Disabled", # No Entity
        "Step",
        "TransitionStep",
        "Transition",
        "TransitionStep_TransitionNotSupported",
        "Transition_TransitionNotSupported",
    ],
    indirect=True,
)
async def test_dim_down_stop(
    mock,
):
    await mock.light_turn_on(brightness=255)
    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_down(),
    )

    await mock.advance_time_ms(800)

    mock.assert_knx_telegrams(
        [
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(242)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(229)),
            KnxTelegram("1/1/4", GroupValueWrite, DPT.percent(216)),
        ]
    )
    mock.clear_knx_tx()

    await mock.send_knx_group_value_write(
        DIMM_ADDRESS,
        DPT.dim_stop(),
    )

    await mock.advance_time_ms(1)

    if mock.mode in ["Step"]:
        assert len(mock.tx_telegrams) == 0
    else:
        assert len(mock.tx_telegrams) == 1
        assert mock.tx_telegrams[0].dpt.payload in [213,214,215] 

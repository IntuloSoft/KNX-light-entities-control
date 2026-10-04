import pytest

from mock_blueprint import MockBlueprint


async def test_mock_light_initial_state(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    mock.assert_state(
        "light.test",
        "off",
    )


async def test_mock_light_turn_on(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
        },
        blocking=True,
    )

    mock.assert_state(
        "light.test",
        "on",
    )


async def test_mock_light_turn_off(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
        },
        blocking=True,
    )

    await hass.services.async_call(
        "light",
        "turn_off",
        {
            "entity_id": "light.test",
        },
        blocking=True,
    )

    mock.assert_state(
        "light.test",
        "off",
    )

async def test_mock_light_brightness(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 128,
        },
        blocking=True,
    )

    state = hass.states.get(
        "light.test"
    )

    assert state.attributes["brightness"] == 128


async def test_mock_light_rgb_color(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "rgb_color": (255, 0, 0),
        },
        blocking=True,
    )

    state = hass.states.get(
        "light.test"
    )

    assert state.attributes["rgb_color"] == (255, 0, 0)


async def test_mock_light_color_temperature(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "color_temp_kelvin": 3000,
        },
        blocking=True,
    )

    state = hass.states.get(
        "light.test"
    )

    assert (
        state.attributes["color_temp_kelvin"]
        == 3000
    )


async def test_mock_light_brightness_then_rgb(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 100,
        },
        blocking=True,
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "rgb_color": (0, 255, 0),
        },
        blocking=True,
    )

    state = hass.states.get(
        "light.test"
    )

    assert state.attributes["rgb_color"] == (0, 255, 0)


async def test_mock_light_stays_on_after_attribute_change(hass):

    mock = MockBlueprint(hass)

    await mock.add_test_light(
        "light.test"
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "brightness": 128,
        },
        blocking=True,
    )

    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": "light.test",
            "color_temp_kelvin": 3500,
        },
        blocking=True,
    )

    mock.assert_state(
        "light.test",
        "on",
    )
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
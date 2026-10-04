import pytest

from unittest.mock import Mock
from mocks.mock_blueprint import (
    MockBlueprint, 
    DPT,
)

@pytest.fixture
async def mock(hass):

    mock = MockBlueprint(hass)

    await mock.register_on_knx_transmit()

    return mock


async def test_assert_state(mock):

    mock.hass.states.async_set(
        "sensor.test",
        "on",
    )

    await mock.hass.async_block_till_done()

    mock.assert_state(
        "sensor.test",
        "on",
    )


def test_assert_knx_tx_count(mock):

    mock.tx_telegrams = [
        object(),
        object(),
    ]

    mock.assert_knx_tx_count(2)


def test_assert_last_knx_group_value_write(mock):

    call = Mock()

    call.data = {
        "address": "1/1/1",
        "payload": 1,
    }

    mock.tx_telegrams.append(call)

    mock.assert_last_knx_group_value_write(
        "1/1/1",
        DPT.binary(1),
    )


def test_assert_last_knx_group_value_response(mock):

    call = Mock()

    call.data = {
        "address": "1/1/1",
        "payload": 1,
        "response": True,
    }

    mock.tx_telegrams.append(call)

    mock.assert_last_knx_group_value_response(
        "1/1/1",
        DPT.binary(1),
    )


def test_assert_last_knx_group_value_read(mock):

    call = Mock()

    call.data = {
        "address": "1/1/1",
    }

    mock.tx_telegrams.append(call)

    mock.assert_last_knx_group_value_read(
        "1/1/1",
    )


async def test_send_knx_group_value_write_does_not_crash(
    mock,
):

    await mock.send_knx_group_value_write(
        "1/1/1",
        DPT.binary(1),
    )


async def test_send_knx_group_value_read_does_not_crash(
    mock,
):

    await mock.send_knx_group_value_read(
        "1/1/1",
    )


async def test_send_knx_group_value_response_does_not_crash(
    mock,
):

    await mock.send_knx_group_value_response(
        "1/1/1",
        DPT.binary(1),
    )
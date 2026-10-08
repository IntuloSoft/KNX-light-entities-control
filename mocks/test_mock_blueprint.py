import pytest

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


@pytest.fixture
async def mock(hass):

    mock = MockBlueprint(hass)

    await mock.register_on_knx_transmit()

    yield mock

    mock.close()


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

async def test_knx_telegram_trace(mock):

    await mock.add_input_boolean("test")
    
    blueprint = """
blueprint:
  name: Telegram Trace Test
  domain: automation

  input:
    entity:
      selector:
        entity:

trigger:
  - platform: state
    entity_id: !input entity

action:
  # Write
  - action: knx.send
    data:
      address: "1/1/1"
      payload: 1

  # Response
  - action: knx.send
    data:
      address: "1/1/2"
      payload: 1
      response: true

  # Read
  - action: knx.read
    data:
      address: "1/1/3"
"""

    await mock._load_blueprint_file(
        blueprint,
        "telegram_trace_test.yaml",
    )

    await mock.load_blueprint_instance(
        "telegram_trace_test.yaml",
        {
            "entity": "input_boolean.test",
        },
    )

    await mock.hass.services.async_call(
        "input_boolean",
        "turn_on",
        {
            "entity_id": "input_boolean.test",
        },
        blocking=True,
    )

    await mock.wait_for_idle()

    mock.assert_knx_telegrams(
        [
            KnxTelegram(
                "1/1/1",
                GroupValueWrite,
                DPT.binary(True),
            ),
            KnxTelegram(
                "1/1/2",
                GroupValueResponse,
                DPT.binary(True),
            ),
            KnxTelegram(
                "1/1/3",
                GroupValueRead,
            ),
        ]
    )

async def test_advance_time_wait_template_timeout(mock):
    await mock.add_input_boolean("test")

    blueprint = """
blueprint:
  name: Wait Test
  domain: automation

  input:
    entity:
      selector:
        entity:

trigger:
  - platform: state
    entity_id: !input entity

action:
  - wait_template: "{{ false }}"
    timeout:
      milliseconds: 10000
    continue_on_timeout: true

  - action: knx.send
    data:
      address: "1/1/1"
      payload: 1
"""

    await mock._load_blueprint_file(
        blueprint,
        "wait_test.yaml",
    )

    await mock.load_blueprint_instance(
        "wait_test.yaml",
        {
            "entity": "input_boolean.test",
        },
    )

    await mock.advance_time_ms(20)

    await mock.hass.services.async_call(
        "input_boolean",
        "turn_on",
        {
            "entity_id": "input_boolean.test",
        },
        blocking=True,
    )

    mock.assert_knx_telegrams([])

    
    await mock.advance_time_ms(10000)

    mock.assert_knx_telegrams([])

    await mock.advance_time_ms(1)
    
    mock.assert_knx_telegrams(
        [
            KnxTelegram(
                "1/1/1",
                GroupValueWrite,
                DPT.binary(True),
            ),
        ]
    )

async def test_wait_template_timeout_aborts_script(
    mock,
):
    await mock.add_input_boolean(
        "test"
    )

    blueprint = """
blueprint:
  name: Wait Abort Test
  domain: automation

  input:
    entity:
      selector:
        entity:

trigger:
  - platform: state
    entity_id: !input entity

action:
  - wait_template: "{{ false }}"
    timeout:
      seconds: 1
    continue_on_timeout: false

  - action: knx.send
    data:
      address: "1/1/1"
      payload: 1
"""

    await mock._load_blueprint_file(
        blueprint,
        "wait_abort_test.yaml",
    )

    await mock.load_blueprint_instance(
        "wait_abort_test.yaml",
        {
            "entity": "input_boolean.test",
        },
    )

    await mock.hass.services.async_call(
        "input_boolean",
        "turn_on",
        {
            "entity_id": "input_boolean.test",
        },
        blocking=True,
    )

    mock.assert_knx_telegrams([])

    await mock.advance_time_ms(990)

    mock.assert_knx_telegrams([])

    await mock.advance_time_ms(20)

    mock.assert_knx_telegrams([])



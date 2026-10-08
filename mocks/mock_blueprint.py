from pathlib import Path
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.helpers.dispatcher import async_dispatcher_send
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import (
    get_scheduled_timer_handles
)

from homeassistant.helpers.event import (
    time_tracker_utcnow,
)

from homeassistant.components.knx.telegrams import (
    SIGNAL_KNX_TELEGRAM,
)

from xknx.telegram import Telegram, TelegramDirection
from xknx.telegram.address import GroupAddress
from xknx.telegram.apci import (
    GroupValueRead,
    GroupValueWrite,
    GroupValueResponse,
)

from mocks.mock_light import MockLight


@dataclass
class KnxValue:
    payload: Any
    value: Any
    dpt_name: str


@dataclass(frozen=True)
class KnxTelegram:
    address: str
    telegram_type: type
    dpt: KnxValue | None = None

class DPT:

    @staticmethod
    def binary(value: bool):
        return KnxValue(
            payload=int(value),
            value=value,
            dpt_name="DPTBinary",
        )

    @staticmethod
    def dim_up(step: int = 7):
        assert 1 <= step <= 7

        return KnxValue(
            payload=8 + step,
            value=step,
            dpt_name="DPTControlDimming",
        )


    @staticmethod
    def dim_down(step: int = 7):
        assert 1 <= step <= 7

        return KnxValue(
            payload=step,
            value=step,
            dpt_name="DPTControlDimming",
        )


    @staticmethod
    def dim_stop():
        return KnxValue(
            payload=0,
            value=0,
            dpt_name="DPTControlDimming",
        )

    @staticmethod
    def percent(value: int):
        return KnxValue(
            payload=[value],
            value=value,
            dpt_name="DPTPercentU8",
        )

    @staticmethod
    def rgb(r: int, g: int, b: int):
        return KnxValue(
            payload=[r, g, b],
            value=[r, g, b],
            dpt_name="DPTRGB",
        )

    @staticmethod
    def color_temperature(kelvin: int):
        return KnxValue(
            payload=kelvin,
            value=kelvin,
            dpt_name="DPTColorTemperature",
        )



class MockBlueprint():
    def __init__(
            self, 
            hass: HomeAssistant,
        ):
        self.hass = hass
        self.tx_telegrams = []
        self.light = None
        self._wall_time = time_tracker_utcnow()
        self._monotonic_time = 0.0

        loop = asyncio.get_running_loop()
        
        self._loop_time_patch = patch.object(
            loop,
            "time",
            self.current_monotonic,
        )

        self._loop_time_patch.start()

    def close(self):
        self._loop_time_patch.stop()

    def _process_due_timers(self):

        for task in list(
            get_scheduled_timer_handles(
                self.hass.loop
            )
        ):
            if task.cancelled():
                continue

            if task.when() <= self.hass.loop.time():
                task._run()
                task.cancel()
    

    def current_datetime(self):
        return self._wall_time

    def current_monotonic(self):
        return self._monotonic_time
    
    async def wait_for_idle(self):
        await self.hass.async_block_till_done()

    async def advance_time_ms(
        self,
        milliseconds: int,
    ):
        for _ in range(milliseconds):

            self._wall_time += timedelta(
                milliseconds=1
            )

            self._monotonic_time += 0.001

            for _ in range(20):
                self._process_due_timers()
                await asyncio.sleep(0)

        
    async def load_blueprint_from_file(
        self,
        source_file: Path,
    ):
        blueprint_filename = source_file.name

        await self._load_blueprint_file(
            blueprint_str=source_file.read_text(),
            blueprint_filename=blueprint_filename,
        )

        return blueprint_filename

    async def _load_blueprint_file(self, blueprint_str, blueprint_filename):
        bp_dir = Path(self.hass.config.path("blueprints/automation/test"))
        bp_dir.mkdir(parents=True, exist_ok=True)

        bp_path = bp_dir / blueprint_filename
        bp_path.write_text(blueprint_str)

        return bp_path

    async def load_blueprint_instance(self, blueprint_filename, inputs):
        AUTOMATION_CONFIG = {
            "id": "test_automation",
            "alias": "Blueprint Instance",
            "use_blueprint": {
                "path": f"test/{blueprint_filename}",
                "input": inputs,
            },
        }
    
        # Automation (op basis van blueprint) laden
        assert await async_setup_component(
            self.hass,
            AUTOMATION_DOMAIN,
            {
                "automation": [
                    AUTOMATION_CONFIG,
                ]
            },
        )


    async def register_service(self,domain,service_name,cb):
        self.hass.services.async_register(
            domain,
            service_name,
            cb,
        )

    # input_boolean
    async def add_input_boolean(
        self,
        name: str,
    ):
        assert await async_setup_component(
            self.hass,
            "input_boolean",
            {
                "input_boolean": {
                    name: {}
                }
            },
        )

    async def add_input_number(
        self,
        name: str,
        min_value: float = 0,
        max_value: float = 255,
        initial_value: float = 0,
    ):
        assert await async_setup_component(
            self.hass,
            "input_number",
            {
                "input_number": {
                    name: {
                        "min": min_value,
                        "max": max_value,
                        "initial": initial_value,
                    }
                }
            },
        )


    # KNX functionality
    def _store_knx_telegram(
        self,
        address: str,
        telegram_type: type,
        dpt=None,
    ):
        self.tx_telegrams.append(
            KnxTelegram(
                address=address,
                telegram_type=telegram_type,
                dpt=dpt,
            )
        )

    async def _on_knx_send(
        self,
        service_call,
    ):
        telegram_type = (
            GroupValueResponse
            if service_call.data.get(
                "response",
                False,
            )
            else GroupValueWrite
        )

        dpt = None

        if "payload" in service_call.data:
            dpt = KnxValue(
                payload=service_call.data["payload"],
                value=None,
                dpt_name=None,
            )

        self._store_knx_telegram(
            address=service_call.data["address"],
            telegram_type=telegram_type,
            dpt=dpt,
        )

    async def _on_knx_read(
        self,
        service_call,
    ):
        self._store_knx_telegram(
            address=service_call.data["address"],
            telegram_type=GroupValueRead,
        )

    async def register_on_knx_transmit(self):

        await self.register_service(
            "knx",
            "send",
            self._on_knx_send,
        )

        await self.register_service(
            "knx",
            "read",
            self._on_knx_read,
        )

        await self.hass.async_block_till_done()
    

    def assert_knx_telegrams(
        self,
        expected: list[KnxTelegram],
    ):

        assert (
            len(self.tx_telegrams)
            == len(expected)
        ), (
            f"Telegram count mismatch.\n"
            f"Expected: {len(expected)}\n"
            f"Actual:   {len(self.tx_telegrams)}\n"
            f"Actual telegrams:\n{self.tx_telegrams}"
        )

        for index, (actual, exp) in enumerate(
            zip(
                self.tx_telegrams,
                expected,
                strict=True,
            )
        ):

            assert (
                actual.address
                == exp.address
            ), (
                f"Telegram {index}: address mismatch.\n"
                f"Expected: {exp.address}\n"
                f"Actual:   {actual.address}\n"
                f"Actual telegram: {actual}"
            )

            assert (
                actual.telegram_type
                is exp.telegram_type
            ), (
                f"Telegram {index}: telegram type mismatch.\n"
                f"Expected: {exp.telegram_type.__name__}\n"
                f"Actual:   {actual.telegram_type.__name__}\n"
                f"Actual telegram: {actual}"
            )

            if exp.dpt is not None:

                assert (
                    actual.dpt is not None
                ), (
                    f"Telegram {index}: expected DPT payload "
                    f"but actual telegram has no DPT.\n"
                    f"Expected DPT: {exp.dpt}"
                )

                assert (
                    actual.dpt.payload
                    == exp.dpt.payload
                ), (
                    f"Telegram {index}: payload mismatch.\n"
                    f"Expected: {exp.dpt.payload}\n"
                    f"Actual:   {actual.dpt.payload}\n"
                    f"Expected telegram: {exp}\n"
                    f"Actual telegram:   {actual}"
                )

    def clear_knx_tx(self):
        self.tx_telegrams.clear()

    async def _send_knx_telegram(
        self,
        destination,
        apci_type,
        dpt=None,
    ):
        telegram = Telegram(
            destination_address=GroupAddress(destination),
            payload=apci_type(
                dpt.payload
            ) if dpt else apci_type(),
        )

        telegram.direction = TelegramDirection.INCOMING

        telegram_dict = {
            "destination": destination,
            "destination_name": "",
            "direction": "Incoming",
        }

        if dpt is not None:
            telegram_dict.update(
                {
                    "payload": dpt.payload,
                    "value": dpt.value,
                    "dpt_name": dpt.dpt_name,
                }
            )

        async_dispatcher_send(
            self.hass,
            SIGNAL_KNX_TELEGRAM,
            telegram,
            telegram_dict,
        )

        # await self.hass.async_block_till_done()

    async def send_knx_group_value_write(
        self,
        destination,
        dpt,
    ):
        await self._send_knx_telegram(
            destination,
            GroupValueWrite,
            dpt,
        )
    
    async def send_knx_group_value_read(
        self,
        destination,
    ):
        await self._send_knx_telegram(
            destination,
            GroupValueRead,
            None,
        )

    async def send_knx_group_value_response(
        self,
        destination: str,
        dpt,
    ):
        await self._send_knx_telegram(
            destination,
            GroupValueResponse,
            dpt,
        )

    # Light functionality
    async def add_test_light(
        self,
        entity_id: str = "light.test",
    ):

        await async_setup_component(
            self.hass,
            LIGHT_DOMAIN,
            {},
        )
        
        self.light = MockLight(entity_id)

        component = self.hass.data.get(LIGHT_DOMAIN)
        assert component is not None

        await component.async_add_entities([self.light])
        await self.hass.async_block_till_done()

    def assert_state(
        self,
        entity_id: str,
        expected_state: str,
    ):
        state = self.hass.states.get(entity_id)

        assert state is not None

        assert state.state == expected_state
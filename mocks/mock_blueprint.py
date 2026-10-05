from pathlib import Path
from dataclasses import dataclass
from enum import Enum, auto
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.helpers.dispatcher import async_dispatcher_send

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
    payload: any
    value: any
    dpt_name: str


@dataclass(frozen=True)
class KnxTelegram:
    address: str
    telegram_type: type
    dpt: object | None = None

class DPT:

    @staticmethod
    def binary(value: bool):
        return KnxValue(
            payload=int(value),
            value=value,
            dpt_name="DPTBinary",
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
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.tx_telegrams = []
        self.light = None

    async def wait_for_idle(self):
        await self.hass.async_block_till_done()

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
        """Schrijf blueprint naar de testconfig."""

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

    # KNX functionality
    async def _on_knx_tx(self,knx_tx_telegram):
        self.tx_telegrams.append(knx_tx_telegram)

    async def register_on_knx_transmit(self):
        await self.register_service(
                "knx",
                "send",
                self._on_knx_tx,
            )
        await self.hass.async_block_till_done()

    def assert_knx_telegrams(
        self,
        expected: list[KnxTelegram],
    ):
        assert len(self.tx_telegrams) == len(expected), f"telegrams: {self.tx_telegrams}\n{expected}"

        for actual, exp in zip(
            self.tx_telegrams,
            expected,
            strict=True,
        ):
            assert (
                actual.data["address"]
                == exp.address
            )

            if exp.dpt is not None:
                assert (
                    actual.data["payload"]
                    == exp.dpt.payload
                )

            actual_type = (
                GroupValueResponse
                if actual.data.get("response", False)
                else GroupValueWrite
            )

            assert actual_type is exp.telegram_type

    def clear_knx_tx(self):
        self.tx_telegrams.clear()

    def assert_knx_tx_count(
        self,
        expected_count: int,
    ):
        assert (
            len(self.tx_telegrams)
            == expected_count
        )

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

        await self.hass.async_block_till_done()

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
from pathlib import Path
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

class MockBlueprint():
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.tx_telegrams = []
        self.light = None

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

    def _assert_last_knx_send(
        self,
        address: str,
        payload=None,
        response: bool = False,
    ):
        assert len(self.tx_telegrams) > 0

        call = self.tx_telegrams[-1]

        assert call.data["address"] == address

        if payload is not None:
            assert call.data["payload"] == payload

        assert call.data.get("response", False) == response


    def assert_last_knx_group_value_write(
        self,
        address: str,
        payload,
    ):
        self._assert_last_knx_send(
            address=address,
            payload=payload,
            response=False,
        )

    def assert_last_knx_group_value_response(
        self,
        address: str,
        payload,
    ):
        self._assert_last_knx_send(
            address=address,
            payload=payload,
            response=True,
        )

    def assert_last_knx_group_value_read(
        self,
        address: str,
    ):
        assert len(self.tx_telegrams) > 0

        call = self.tx_telegrams[-1]

        assert call.data["address"] == address
        assert "payload" not in call.data
        assert call.data.get("response", False) is False

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
        apci,
        payload=None,
    ):
        telegram = Telegram(
            destination_address=GroupAddress(destination),
            payload=apci,
        )

        telegram.direction = TelegramDirection.INCOMING

        telegram_dict = {
            "destination": destination,
            "destination_name": "",
            "direction": "Incoming",
            "payload": payload,
            "value": payload,
            "dpt_name": "DPTBinary",
        }

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
        payload,
    ):
        await self._send_knx_telegram(
            destination,
            GroupValueWrite(payload),
            payload,
        )

    async def send_knx_group_value_read(
        self,
        destination,
    ):
        await self._send_knx_telegram(
            destination,
            GroupValueRead(),
            None,
        )

    async def send_knx_group_value_response(
        self,
        destination: str,
        payload,
    ):
        await self._send_knx_telegram(
            destination,
            GroupValueResponse(payload),
            payload,
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

from homeassistant.components.light import LightEntity

class MockLight(LightEntity):

    def __init__(self, entity_id):
        self.entity_id = entity_id
        self._attr_is_on = False

    @property
    def is_on(self):
        return self._attr_is_on

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        self.async_write_ha_state()
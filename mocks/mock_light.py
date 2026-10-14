from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    LightEntityFeature,
)


class MockLight(LightEntity):

    def __init__(self, entity_id, transition_supported=True):
        self.entity_id = entity_id

        self._attr_is_on = False

        self._attr_brightness = None
        self._attr_rgb_color = None
        self._attr_color_temp_kelvin = None

        if transition_supported:
            self._attr_supported_features = LightEntityFeature.TRANSITION
        else:
            self._attr_supported_features = 0

        self._attr_color_mode = ColorMode.ONOFF
        self._attr_supported_color_modes = {
            ColorMode.ONOFF,
            ColorMode.BRIGHTNESS,
            ColorMode.RGB,
            ColorMode.COLOR_TEMP,
        }


    @property
    def is_on(self):
        return self._attr_is_on

    async def async_turn_on(self, **kwargs):

        self._attr_is_on = True

        if "brightness" in kwargs:
            self._attr_brightness = kwargs["brightness"]
            self._attr_color_mode = ColorMode.BRIGHTNESS

        if "rgb_color" in kwargs:
            self._attr_rgb_color = kwargs["rgb_color"]
            self._attr_color_mode = ColorMode.RGB

        if "color_temp_kelvin" in kwargs:
            self._attr_color_temp_kelvin = kwargs["color_temp_kelvin"]
            self._attr_color_mode = ColorMode.COLOR_TEMP

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):

        self._attr_is_on = False

        self.async_write_ha_state()
        
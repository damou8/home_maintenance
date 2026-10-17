"""Serve the dashboard card and load it on every frontend page."""

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import CARD_URL, DOMAIN, STATIC_PATH

DATA_STATIC_PATH_REGISTERED = f"{DOMAIN}_static_path_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Make custom:home-maintenance-card available without adding a resource."""
    # A static path cannot be removed, so it is registered only once
    if not hass.data.get(DATA_STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    STATIC_PATH,
                    str(Path(__file__).parent / "frontend" / "dist"),
                    cache_headers=False,
                )
            ]
        )
        hass.data[DATA_STATIC_PATH_REGISTERED] = True

    frontend.add_extra_js_url(hass, CARD_URL)


@callback
def async_unregister_card(hass: HomeAssistant) -> None:
    """Stop loading the card."""
    frontend.remove_extra_js_url(hass, CARD_URL)

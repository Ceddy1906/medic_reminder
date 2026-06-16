"""Button platform for Medic Reminder — one 'Packung aufgefüllt' button per medication."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MED_ID, CONF_MED_NAME, CONF_MED_PACKAGE_SIZE, DOMAIN, STATE_CURRENT_COUNT
from .coordinator import MedicReminderCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MedicReminderCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RefillButton(coordinator, med) for med in coordinator.medications
    )


class RefillButton(ButtonEntity):
    """Button that resets the stock of a medication to its full package size."""

    _attr_icon = "mdi:pill-multiple"
    _attr_has_entity_name = True

    def __init__(self, coordinator: MedicReminderCoordinator, med: dict) -> None:
        self._coordinator = coordinator
        self._med_id = med[CONF_MED_ID]
        self._med_name = med[CONF_MED_NAME]
        self._package_size = float(med.get(CONF_MED_PACKAGE_SIZE, 0))

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self._med_id}_refill"
        self._attr_name = f"{self._med_name} – Packung aufgefüllt"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "Medic Reminder",
            "manufacturer": "Medic Reminder",
            "model": "Medication Manager",
        }

    async def async_press(self) -> None:
        """Add one full package to the current stock."""
        current = self._coordinator.data.get(self._med_id, {}).get(
            STATE_CURRENT_COUNT, 0.0
        )
        new_count = float(current) + self._package_size
        _LOGGER.info(
            "Refill button pressed for %s — adding %.0f to %.1f → %.1f",
            self._med_name,
            self._package_size,
            current,
            new_count,
        )
        await self._coordinator.async_set_current_count(self._med_id, new_count)

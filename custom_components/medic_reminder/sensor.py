"""Sensor platform for Medic Reminder."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MED_ACTION_DAYS,
    CONF_MED_ACTION_TYPE,
    CONF_MED_DOSAGE,
    CONF_MED_EVENING,
    CONF_MED_ID,
    CONF_MED_MORNING,
    CONF_MED_NAME,
    CONF_MED_NIGHT,
    CONF_MED_NOON,
    CONF_MED_PACKAGE_SIZE,
    DOMAIN,
)
from .coordinator import MedicReminderCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MedicReminderCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for med in coordinator.medications:
        entities.append(DaysUntilEmptySensor(coordinator, med))
        entities.append(NextPurchaseDateSensor(coordinator, med))

    async_add_entities(entities)


class _MedSensorBase(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: MedicReminderCoordinator, med: dict) -> None:
        super().__init__(coordinator)
        self._med_id  = med[CONF_MED_ID]
        self._med_name = med[CONF_MED_NAME]
        self._med_cfg  = med   # static config reference
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "Medic Reminder",
            "manufacturer": "Medic Reminder",
            "model": "Medication Manager",
        }

    def _med_data(self) -> dict:
        return self.coordinator.data.get(self._med_id, {})


class DaysUntilEmptySensor(_MedSensorBase):
    _attr_icon = "mdi:pill"
    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: MedicReminderCoordinator, med: dict) -> None:
        super().__init__(coordinator, med)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self._med_id}_days"
        self._attr_name = f"{self._med_name} – Tage bis leer"

    @property
    def native_value(self) -> float | None:
        days = self._med_data().get("days_until_empty")
        if days is None:
            return None
        return round(days, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d   = self._med_data()
        cfg = self._med_cfg
        schedule = (
            f"{cfg.get(CONF_MED_MORNING, 0)}-"
            f"{cfg.get(CONF_MED_NOON, 0)}-"
            f"{cfg.get(CONF_MED_EVENING, 0)}-"
            f"{cfg.get(CONF_MED_NIGHT, 0)}"
        )
        return {
            "current_count":  d.get("current_count"),
            "package_size":   cfg.get(CONF_MED_PACKAGE_SIZE),
            "dosage":         cfg.get(CONF_MED_DOSAGE),
            "schedule":       schedule,
            "action_type":    cfg.get(CONF_MED_ACTION_TYPE),
            "action_days_before": cfg.get(CONF_MED_ACTION_DAYS),
        }


class NextPurchaseDateSensor(_MedSensorBase):
    _attr_icon = "mdi:calendar-alert"

    def __init__(self, coordinator: MedicReminderCoordinator, med: dict) -> None:
        super().__init__(coordinator, med)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self._med_id}_purchase_date"
        self._attr_name = f"{self._med_name} – Nächster Kauf"

    @property
    def native_value(self) -> str | None:
        d: date | None = self._med_data().get("next_purchase_date")
        if d is None:
            return None
        return d.isoformat()

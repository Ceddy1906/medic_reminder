"""Coordinator for Medic Reminder integration."""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ACTION_BRING,
    ACTION_CALENDAR,
    ACTION_NOTIFY,
    CONF_ACTION_TIME,
    CONF_MED_ACTION_DAYS,
    CONF_MED_ACTION_TYPE,
    CONF_MED_BRING_LIST,
    CONF_MED_CALENDAR,
    CONF_MED_DOSAGE,
    CONF_MED_EVENING,
    CONF_MED_ID,
    CONF_MED_MORNING,
    CONF_MED_NAME,
    CONF_MED_NIGHT,
    CONF_MED_NOON,
    CONF_MED_NOTIFY,
    CONF_MED_PACKAGE_SIZE,
    CONF_MED_PRE_NOTIFY_DAYS,
    CONF_MED_PRE_NOTIFY_ENABLED,
    CONF_MED_PRE_NOTIFY_SERVICE,
    CONF_MED_FREQUENCY,
    CONF_MEDICATIONS,
    DOMAIN,
    FREQ_DAILY,
    FREQ_DIVISOR,
    STATE_ACTION_TRIGGERED,
    STATE_CURRENT_COUNT,
    STATE_PRE_NOTIFY_TRIGGERED,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class MedicReminderCoordinator(DataUpdateCoordinator):
    """Manages all medications and their state."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.config_entry = config_entry
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{config_entry.entry_id}")
        self._med_states: dict[str, dict] = {}
        self._unsub_time: list = []
        self._unsub_todo: list = []

    @property
    def medications(self) -> list[dict]:
        return self.config_entry.options.get(CONF_MEDICATIONS, [])

    def daily_dose(self, med: dict) -> float:
        """Return the effective daily dose, accounting for intake frequency."""
        per_intake = (
            float(med.get(CONF_MED_MORNING, 0))
            + float(med.get(CONF_MED_NOON, 0))
            + float(med.get(CONF_MED_EVENING, 0))
            + float(med.get(CONF_MED_NIGHT, 0))
        )
        divisor = FREQ_DIVISOR.get(med.get(CONF_MED_FREQUENCY, FREQ_DAILY), 1.0)
        return per_intake / divisor

    def days_until_empty(self, med: dict) -> float | None:
        dose = self.daily_dose(med)
        if dose <= 0:
            return None
        count = self._med_states.get(med[CONF_MED_ID], {}).get(STATE_CURRENT_COUNT, med[CONF_MED_PACKAGE_SIZE])
        return count / dose

    def next_purchase_date(self, med: dict) -> date | None:
        days = self.days_until_empty(med)
        if days is None:
            return None
        action_days = int(med.get(CONF_MED_ACTION_DAYS, 7))
        return (dt_util.now().date() + timedelta(days=int(days) - action_days))

    async def async_setup(self) -> None:
        await self._load_state()
        self._schedule_daily_job()
        self._subscribe_todo_listeners()

    async def async_shutdown(self) -> None:
        for unsub in self._unsub_time + self._unsub_todo:
            unsub()
        self._unsub_time.clear()
        self._unsub_todo.clear()

    async def _load_state(self) -> None:
        stored = await self._store.async_load()
        if stored:
            self._med_states = stored
        for med in self.medications:
            mid = med[CONF_MED_ID]
            if mid not in self._med_states:
                self._med_states[mid] = {
                    STATE_CURRENT_COUNT: float(med[CONF_MED_PACKAGE_SIZE]),
                    STATE_ACTION_TRIGGERED: False,
                    STATE_PRE_NOTIFY_TRIGGERED: False,
                }

    async def _save_state(self) -> None:
        await self._store.async_save(self._med_states)

    def _schedule_daily_job(self) -> None:
        action_time = self.config_entry.options.get(CONF_ACTION_TIME, "08:00")
        try:
            hour, minute = (int(x) for x in action_time.split(":"))
        except (ValueError, AttributeError):
            hour, minute = 8, 0

        @callback
        def _daily_callback(now: datetime) -> None:
            self.hass.async_create_task(self._async_daily_update())

        self._unsub_time.append(
            async_track_time_change(self.hass, _daily_callback, hour=hour, minute=minute, second=0)
        )

    def _subscribe_todo_listeners(self) -> None:
        bring_entities: set[str] = set()
        for med in self.medications:
            if med.get(CONF_MED_ACTION_TYPE) == ACTION_BRING:
                entity_id = med.get(CONF_MED_BRING_LIST)
                if entity_id:
                    bring_entities.add(entity_id)

        for entity_id in bring_entities:
            self._unsub_todo.append(
                async_track_state_change_event(
                    self.hass, entity_id, self._async_todo_state_changed
                )
            )

    @callback
    def _async_todo_state_changed(self, event) -> None:
        entity_id = event.data.get("entity_id")
        self.hass.async_create_task(self._async_check_bring_list(entity_id))

    async def _async_check_bring_list(self, entity_id: str) -> None:
        try:
            result = await self.hass.services.async_call(
                "todo",
                "get_items",
                {"status": "needs_action"},
                target={"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )
        except Exception as err:
            _LOGGER.warning("Could not get todo items from %s: %s", entity_id, err)
            return

        items = result.get(entity_id, {}).get("items", [])
        active_names = {item.get("summary", "").lower() for item in items}

        changed = False
        for med in self.medications:
            if med.get(CONF_MED_ACTION_TYPE) != ACTION_BRING:
                continue
            if med.get(CONF_MED_BRING_LIST) != entity_id:
                continue
            mid = med[CONF_MED_ID]
            med_name_lower = med[CONF_MED_NAME].lower()
            if med_name_lower not in active_names:
                state = self._med_states.setdefault(mid, {})
                if state.get(STATE_ACTION_TRIGGERED, False):
                    _LOGGER.info("Medication %s removed from Bring! list, resetting counter", med[CONF_MED_NAME])
                    state[STATE_CURRENT_COUNT] = float(med[CONF_MED_PACKAGE_SIZE])
                    state[STATE_ACTION_TRIGGERED] = False
                    state[STATE_PRE_NOTIFY_TRIGGERED] = False
                    changed = True

        if changed:
            await self._save_state()
            await self.async_refresh()

    async def _async_daily_update(self) -> None:
        changed = False
        for med in self.medications:
            mid = med[CONF_MED_ID]
            state = self._med_states.setdefault(mid, {
                STATE_CURRENT_COUNT: float(med[CONF_MED_PACKAGE_SIZE]),
                STATE_ACTION_TRIGGERED: False,
                STATE_PRE_NOTIFY_TRIGGERED: False,
            })

            dose = self.daily_dose(med)
            if dose > 0:
                state[STATE_CURRENT_COUNT] = max(0.0, float(state[STATE_CURRENT_COUNT]) - dose)
                changed = True

            days_left = self.days_until_empty(med)
            if days_left is None:
                continue

            action_days = int(med.get(CONF_MED_ACTION_DAYS, 7))
            pre_notify_days = int(med.get(CONF_MED_PRE_NOTIFY_DAYS, 14))

            if med.get(CONF_MED_PRE_NOTIFY_ENABLED) and not state.get(STATE_PRE_NOTIFY_TRIGGERED):
                if days_left <= pre_notify_days:
                    await self._fire_pre_notify(med, days_left)
                    state[STATE_PRE_NOTIFY_TRIGGERED] = True
                    changed = True

            if not state.get(STATE_ACTION_TRIGGERED):
                if days_left <= action_days:
                    await self._fire_action(med, days_left)
                    state[STATE_ACTION_TRIGGERED] = True
                    changed = True

        if changed:
            await self._save_state()
            await self.async_refresh()

    async def _fire_action(self, med: dict, days_left: float) -> None:
        action_type = med.get(CONF_MED_ACTION_TYPE)
        name = med[CONF_MED_NAME]
        _LOGGER.info("Firing action '%s' for medication %s (%.1f days left)", action_type, name, days_left)

        if action_type == ACTION_BRING:
            bring_list = med.get(CONF_MED_BRING_LIST)
            if bring_list:
                try:
                    schedule = (
                        f"{med.get(CONF_MED_MORNING, 0)}-"
                        f"{med.get(CONF_MED_NOON, 0)}-"
                        f"{med.get(CONF_MED_EVENING, 0)}-"
                        f"{med.get(CONF_MED_NIGHT, 0)}"
                    )
                    description = (
                        f"{med.get(CONF_MED_DOSAGE, '')} "
                        f"({int(med.get(CONF_MED_PACKAGE_SIZE, 0))}Stk), "
                        f"{schedule}"
                    ).strip()
                    await self.hass.services.async_call(
                        "todo",
                        "add_item",
                        {"item": name, "description": description},
                        target={"entity_id": bring_list},
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.error("Failed to add %s to Bring! list: %s", name, err)

        elif action_type == ACTION_CALENDAR:
            calendar_entity = med.get(CONF_MED_CALENDAR)
            if calendar_entity:
                purchase_date = self.next_purchase_date(med)
                event_date = purchase_date.isoformat() if purchase_date else dt_util.now().date().isoformat()
                try:
                    await self.hass.services.async_call(
                        "calendar",
                        "create_event",
                        {
                            "summary": f"Medikament kaufen: {name} ({med.get(CONF_MED_DOSAGE, '')})",
                            "start_date": event_date,
                            "end_date": event_date,
                            "description": f"Noch ca. {days_left:.0f} Tage Vorrat.",
                        },
                        target={"entity_id": calendar_entity},
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.error("Failed to create calendar event for %s: %s", name, err)

        elif action_type == ACTION_NOTIFY:
            notify_service = med.get(CONF_MED_NOTIFY)
            if notify_service:
                await self._send_notify(
                    notify_service,
                    f"Medikament kaufen: {name}",
                    f"{name} ({med.get(CONF_MED_DOSAGE, '')}) — Vorrat reicht noch ca. {days_left:.0f} Tage.",
                )

    async def _fire_pre_notify(self, med: dict, days_left: float) -> None:
        notify_service = med.get(CONF_MED_PRE_NOTIFY_SERVICE)
        if not notify_service:
            return
        name = med[CONF_MED_NAME]
        _LOGGER.info("Firing pre-notify for medication %s (%.1f days left)", name, days_left)
        await self._send_notify(
            notify_service,
            f"Medikament-Vorwarnung: {name}",
            f"{name} ({med.get(CONF_MED_DOSAGE, '')}) — Vorrat reicht noch ca. {days_left:.0f} Tage. Bitte neu besorgen.",
        )

    async def _send_notify(self, service: str, title: str, message: str) -> None:
        try:
            await self.hass.services.async_call(
                "notify",
                service,
                {"title": title, "message": message},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Failed to send notification via %s: %s", service, err)

    async def _async_update_data(self) -> dict[str, Any]:
        result = {}
        for med in self.medications:
            mid = med[CONF_MED_ID]
            state = self._med_states.get(mid, {})
            result[mid] = {
                "medication": med,
                "current_count": state.get(STATE_CURRENT_COUNT, med[CONF_MED_PACKAGE_SIZE]),
                "days_until_empty": self.days_until_empty(med),
                "next_purchase_date": self.next_purchase_date(med),
            }
        return result

    async def async_set_current_count(self, med_id: str, count: float) -> None:
        """Manually set the current stock for a medication (e.g. when starting with a partial pack)."""
        state = self._med_states.setdefault(med_id, {})
        state[STATE_CURRENT_COUNT] = count
        # Reset trigger flags so actions fire again at the right threshold
        state[STATE_ACTION_TRIGGERED] = False
        state[STATE_PRE_NOTIFY_TRIGGERED] = False
        await self._save_state()
        await self.async_refresh()

    def on_options_updated(self) -> None:
        for unsub in self._unsub_time + self._unsub_todo:
            unsub()
        self._unsub_time.clear()
        self._unsub_todo.clear()
        for med in self.medications:
            mid = med[CONF_MED_ID]
            if mid not in self._med_states:
                self._med_states[mid] = {
                    STATE_CURRENT_COUNT: float(med[CONF_MED_PACKAGE_SIZE]),
                    STATE_ACTION_TRIGGERED: False,
                    STATE_PRE_NOTIFY_TRIGGERED: False,
                }
        self._schedule_daily_job()
        self._subscribe_todo_listeners()
        self.hass.async_create_task(self.async_refresh())

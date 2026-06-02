"""Config flow for Medic Reminder."""
from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

import voluptuous as vol

from homeassistant.components.todo import TodoListEntity
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

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
    CONF_MEDICATIONS,
    DEFAULT_ACTION_DAYS,
    DEFAULT_ACTION_TIME,
    DEFAULT_PRE_NOTIFY_DAYS,
    DOMAIN,
)

_MENU_ADD = "add_medication"
_MENU_EDIT = "edit_medication"
_MENU_DELETE = "delete_medication"
_MENU_SETTINGS = "global_settings"
_MENU_DONE = "done"


def _number(min_val: float = 0, max_val: float = 100, step: float = 0.5, mode: str = "box") -> NumberSelector:
    return NumberSelector(NumberSelectorConfig(min=min_val, max=max_val, step=step, mode=NumberSelectorMode(mode)))


def _notify_services(hass) -> list[str]:
    """Return list of available notify service names (without 'notify.' prefix)."""
    services = hass.services.async_services().get("notify", {})
    return sorted(services.keys())


def _todo_entities(hass) -> list[str]:
    registry = er.async_get(hass)
    return [
        e.entity_id
        for e in registry.entities.values()
        if e.domain == "todo"
    ]


def _calendar_entities(hass) -> list[str]:
    registry = er.async_get(hass)
    return [
        e.entity_id
        for e in registry.entities.values()
        if e.domain == "calendar"
    ]


class MedicReminderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup flow — just global settings, medications added via options."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(
                title="Medic Reminder",
                data={},
                options={
                    CONF_ACTION_TIME: user_input[CONF_ACTION_TIME],
                    CONF_MEDICATIONS: [],
                },
            )

        schema = vol.Schema({
            vol.Required(CONF_ACTION_TIME, default=DEFAULT_ACTION_TIME): TimeSelector(),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MedicReminderOptionsFlow(config_entry)


class MedicReminderOptionsFlow(OptionsFlow):
    """Options flow for managing medications."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._medications: list[dict] = deepcopy(config_entry.options.get(CONF_MEDICATIONS, []))
        self._action_time: str = config_entry.options.get(CONF_ACTION_TIME, DEFAULT_ACTION_TIME)
        self._editing_med: dict | None = None
        self._new_med: dict = {}

    # ── Main menu ────────────────────────────────────────────────────────────

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_menu()

    async def async_step_menu(self, user_input: dict[str, Any] | None = None):
        med_names = [f"{m[CONF_MED_NAME]} ({m.get(CONF_MED_DOSAGE, '')})" for m in self._medications]
        options = [_MENU_ADD, _MENU_SETTINGS]
        if med_names:
            options += [_MENU_EDIT, _MENU_DELETE]
        options.append(_MENU_DONE)

        return self.async_show_menu(
            step_id="menu",
            menu_options=options,
        )

    # ── Global settings ───────────────────────────────────────────────────────

    async def async_step_global_settings(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._action_time = user_input[CONF_ACTION_TIME]
            return await self.async_step_menu()

        schema = vol.Schema({
            vol.Required(CONF_ACTION_TIME, default=self._action_time): TimeSelector(),
        })
        return self.async_show_form(step_id="global_settings", data_schema=schema)

    # ── Done ─────────────────────────────────────────────────────────────────

    async def async_step_done(self, user_input: dict[str, Any] | None = None):
        return self.async_create_entry(
            data={
                CONF_ACTION_TIME: self._action_time,
                CONF_MEDICATIONS: self._medications,
            }
        )

    # ── Add medication ────────────────────────────────────────────────────────

    async def async_step_add_medication(self, user_input: dict[str, Any] | None = None):
        self._editing_med = None
        self._new_med = {}
        return await self.async_step_med_basic()

    # ── Edit medication ───────────────────────────────────────────────────────

    async def async_step_edit_medication(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            med_id = user_input["medication"]
            self._editing_med = next((m for m in self._medications if m[CONF_MED_ID] == med_id), None)
            self._new_med = deepcopy(self._editing_med) if self._editing_med else {}
            return await self.async_step_med_basic()

        options = {m[CONF_MED_ID]: f"{m[CONF_MED_NAME]} ({m.get(CONF_MED_DOSAGE, '')})" for m in self._medications}
        schema = vol.Schema({
            vol.Required("medication"): SelectSelector(
                SelectSelectorConfig(options=[{"value": k, "label": v} for k, v in options.items()], mode=SelectSelectorMode.LIST)
            ),
        })
        return self.async_show_form(step_id="edit_medication", data_schema=schema)

    # ── Delete medication ─────────────────────────────────────────────────────

    async def async_step_delete_medication(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            med_id = user_input["medication"]
            self._medications = [m for m in self._medications if m[CONF_MED_ID] != med_id]
            return await self.async_step_menu()

        options = {m[CONF_MED_ID]: f"{m[CONF_MED_NAME]} ({m.get(CONF_MED_DOSAGE, '')})" for m in self._medications}
        schema = vol.Schema({
            vol.Required("medication"): SelectSelector(
                SelectSelectorConfig(options=[{"value": k, "label": v} for k, v in options.items()], mode=SelectSelectorMode.LIST)
            ),
        })
        return self.async_show_form(step_id="delete_medication", data_schema=schema)

    # ── Step 1: Basic info ────────────────────────────────────────────────────

    async def async_step_med_basic(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._new_med.update(user_input)
            return await self.async_step_med_action()

        defaults = self._new_med
        schema = vol.Schema({
            vol.Required(CONF_MED_NAME, default=defaults.get(CONF_MED_NAME, "")): TextSelector(),
            vol.Required(CONF_MED_DOSAGE, default=defaults.get(CONF_MED_DOSAGE, "")): TextSelector(),
            vol.Required(CONF_MED_MORNING, default=defaults.get(CONF_MED_MORNING, 0)): _number(0, 10, 0.5),
            vol.Required(CONF_MED_NOON, default=defaults.get(CONF_MED_NOON, 0)): _number(0, 10, 0.5),
            vol.Required(CONF_MED_EVENING, default=defaults.get(CONF_MED_EVENING, 0)): _number(0, 10, 0.5),
            vol.Required(CONF_MED_NIGHT, default=defaults.get(CONF_MED_NIGHT, 0)): _number(0, 10, 0.5),
            vol.Required(CONF_MED_PACKAGE_SIZE, default=defaults.get(CONF_MED_PACKAGE_SIZE, 30)): _number(1, 1000, 1),
        })
        return self.async_show_form(step_id="med_basic", data_schema=schema)

    # ── Step 2: Action ────────────────────────────────────────────────────────

    async def async_step_med_action(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            action_type = user_input[CONF_MED_ACTION_TYPE]
            bring_list = user_input.get(CONF_MED_BRING_LIST)
            calendar = user_input.get(CONF_MED_CALENDAR)
            notify = user_input.get(CONF_MED_NOTIFY)

            if action_type == ACTION_BRING and not bring_list:
                errors[CONF_MED_BRING_LIST] = "required_for_bring"
            elif action_type == ACTION_CALENDAR and not calendar:
                errors[CONF_MED_CALENDAR] = "required_for_calendar"
            elif action_type == ACTION_NOTIFY and not notify:
                errors[CONF_MED_NOTIFY] = "required_for_notify"
            else:
                self._new_med.update(user_input)
                return await self.async_step_med_prenotify()

        defaults = self._new_med
        todo_entities = _todo_entities(self.hass)
        calendar_entities = _calendar_entities(self.hass)
        notify_services = _notify_services(self.hass)

        schema_dict: dict = {
            vol.Required(CONF_MED_ACTION_TYPE, default=defaults.get(CONF_MED_ACTION_TYPE, ACTION_NOTIFY)): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": ACTION_BRING, "label": "Bring! (Einkaufsliste)"},
                        {"value": ACTION_CALENDAR, "label": "Kalender-Eintrag"},
                        {"value": ACTION_NOTIFY, "label": "Benachrichtigung (Notify)"},
                    ],
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_MED_ACTION_DAYS, default=defaults.get(CONF_MED_ACTION_DAYS, DEFAULT_ACTION_DAYS)): _number(1, 60, 1),
        }

        if todo_entities:
            schema_dict[vol.Optional(CONF_MED_BRING_LIST, default=defaults.get(CONF_MED_BRING_LIST, vol.UNDEFINED))] = SelectSelector(
                SelectSelectorConfig(options=todo_entities, mode=SelectSelectorMode.DROPDOWN)
            )

        if calendar_entities:
            schema_dict[vol.Optional(CONF_MED_CALENDAR, default=defaults.get(CONF_MED_CALENDAR, vol.UNDEFINED))] = SelectSelector(
                SelectSelectorConfig(options=calendar_entities, mode=SelectSelectorMode.DROPDOWN)
            )

        if notify_services:
            schema_dict[vol.Optional(CONF_MED_NOTIFY, default=defaults.get(CONF_MED_NOTIFY, vol.UNDEFINED))] = SelectSelector(
                SelectSelectorConfig(options=notify_services, mode=SelectSelectorMode.DROPDOWN)
            )

        return self.async_show_form(
            step_id="med_action",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    # ── Step 3: Pre-notify ────────────────────────────────────────────────────

    async def async_step_med_prenotify(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._new_med.update(user_input)
            self._save_medication()
            return await self.async_step_menu()

        defaults = self._new_med
        notify_services = _notify_services(self.hass)

        schema_dict: dict = {
            vol.Required(CONF_MED_PRE_NOTIFY_ENABLED, default=defaults.get(CONF_MED_PRE_NOTIFY_ENABLED, False)): BooleanSelector(),
            vol.Required(CONF_MED_PRE_NOTIFY_DAYS, default=defaults.get(CONF_MED_PRE_NOTIFY_DAYS, DEFAULT_PRE_NOTIFY_DAYS)): _number(1, 90, 1),
        }

        if notify_services:
            schema_dict[vol.Optional(CONF_MED_PRE_NOTIFY_SERVICE, default=defaults.get(CONF_MED_PRE_NOTIFY_SERVICE, vol.UNDEFINED))] = SelectSelector(
                SelectSelectorConfig(options=notify_services, mode=SelectSelectorMode.DROPDOWN)
            )

        return self.async_show_form(step_id="med_prenotify", data_schema=vol.Schema(schema_dict))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _save_medication(self) -> None:
        if CONF_MED_ID not in self._new_med:
            self._new_med[CONF_MED_ID] = str(uuid.uuid4())

        med_id = self._new_med[CONF_MED_ID]
        existing = next((i for i, m in enumerate(self._medications) if m[CONF_MED_ID] == med_id), None)
        if existing is not None:
            self._medications[existing] = self._new_med
        else:
            self._medications.append(self._new_med)
        self._new_med = {}
        self._editing_med = None

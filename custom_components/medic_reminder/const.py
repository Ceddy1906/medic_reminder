"""Constants for Medic Reminder integration."""
from __future__ import annotations

DOMAIN = "medic_reminder"
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_state"

PLATFORMS = ["sensor", "button"]

# Action types
ACTION_BRING = "bring"
ACTION_CALENDAR = "calendar"
ACTION_NOTIFY = "notify"

ACTION_TYPES = [ACTION_BRING, ACTION_CALENDAR, ACTION_NOTIFY]

# Config keys — integration level
CONF_ACTION_TIME = "action_time"

# Config keys — medication level
CONF_MEDICATIONS = "medications"
CONF_MED_ID = "med_id"
CONF_MED_NAME = "name"
CONF_MED_DOSAGE = "dosage"
CONF_MED_MORNING = "morning"
CONF_MED_NOON = "noon"
CONF_MED_EVENING = "evening"
CONF_MED_NIGHT = "night"
CONF_MED_PACKAGE_SIZE = "package_size"
CONF_MED_ACTION_TYPE = "action_type"
CONF_MED_ACTION_DAYS = "action_days_before"
CONF_MED_BRING_LIST = "bring_list_entity"
CONF_MED_CALENDAR = "calendar_entity"
CONF_MED_NOTIFY = "notify_service"
CONF_MED_PRE_NOTIFY_ENABLED = "pre_notify_enabled"
CONF_MED_PRE_NOTIFY_SERVICE = "pre_notify_service"
CONF_MED_PRE_NOTIFY_DAYS = "pre_notify_days"
CONF_MED_FREQUENCY = "frequency"

# Frequency options
FREQ_DAILY      = "daily"       # every day          → divisor 1
FREQ_EVERY_2D   = "every_2d"    # every 2 days       → divisor 2
FREQ_EVERY_3D   = "every_3d"    # every 3 days       → divisor 3
FREQ_2X_WEEK    = "2x_week"     # 2× per week        → divisor 3.5
FREQ_3X_WEEK    = "3x_week"     # 3× per week        → divisor 7/3
FREQ_1X_WEEK    = "1x_week"     # 1× per week        → divisor 7

# Maps each frequency option to its effective day-divisor
FREQ_DIVISOR: dict[str, float] = {
    FREQ_DAILY:    1.0,
    FREQ_EVERY_2D: 2.0,
    FREQ_EVERY_3D: 3.0,
    FREQ_2X_WEEK:  7.0 / 2,
    FREQ_3X_WEEK:  7.0 / 3,
    FREQ_1X_WEEK:  7.0,
}

# State keys (persisted in storage)
STATE_CURRENT_COUNT = "current_count"
STATE_ACTION_TRIGGERED = "action_triggered"
STATE_PRE_NOTIFY_TRIGGERED = "pre_notify_triggered"

# Defaults
DEFAULT_ACTION_TIME = "08:00"
DEFAULT_ACTION_DAYS = 7
DEFAULT_PRE_NOTIFY_DAYS = 14

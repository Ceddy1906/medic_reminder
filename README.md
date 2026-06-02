# Medic Reminder

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Eine Home Assistant Integration zur Verwaltung von Medikamentenplänen mit automatischer Kauf-Erinnerung.

## Features

- Mehrere Medikamente in einer Integration-Instanz verwalten
- Einnahmeplan (Morgens / Mittags / Abends / Nachts), auch Dezimalwerte (z.B. 0,5 Tabletten)
- Errechnet automatisch „Tage bis leer" und „Nächster Kauftermin"
- Aktion bei Erreichen des Schwellwerts:
  - **Bring!** – Medikament zur Einkaufsliste hinzufügen
  - **Kalender** – Termin in einem HA-Kalender anlegen
  - **Notify** – Benachrichtigung über beliebigen Notify-Dienst (Matrix, Signal, Alexa, …)
- Separate, konfigurierbarer Vorab-Notify
- Bring!-Integration: Packung wird automatisch „aufgefüllt", wenn das Medikament als erledigt aus der Liste entfernt wird

## Installation via HACS

1. HACS → Integrationen → Drei-Punkte-Menü → **Benutzerdefiniertes Repository**
2. URL: `https://github.com/MarcMann/medic_reminder` · Kategorie: **Integration**
3. Integration installieren und Home Assistant neu starten
4. Einstellungen → Geräte & Dienste → **Medic Reminder hinzufügen**

## Sensoren

Pro Medikament werden zwei Sensoren erstellt:

| Sensor | Beschreibung |
|---|---|
| `sensor.<name>_tage_bis_leer` | Verbleibende Tage bis die Packung leer ist |
| `sensor.<name>_nachster_kauf` | Datum, an dem die Kauf-Aktion ausgelöst wird |

## Konfiguration

Die gesamte Konfiguration erfolgt über die UI:

1. **Einrichtung**: Tägliche Prüfuhrzeit festlegen
2. **Optionen**: Medikamente hinzufügen / bearbeiten / löschen

### Einnahmeplan

Das Schema `1-0-0-0` entspricht:
- Morgens: **1**, Mittags: **0**, Abends: **0**, Nachts: **0**

Dezimalwerte sind möglich (z.B. `0.5` für eine halbe Tablette).

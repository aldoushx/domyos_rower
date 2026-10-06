"""Rower sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATUSES
from .coordinator import DomyosRowerCoordinator
from .entity import DomyosRowerEntity
from .protocol import RowerData, format_pace


@dataclass(frozen=True, kw_only=True)
class RowerSensorDescription(SensorEntityDescription):
    value_fn: Callable[[RowerData], float | int | str | None]


SENSORS: tuple[RowerSensorDescription, ...] = (
    RowerSensorDescription(
        key="cadence",
        native_unit_of_measurement="spm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:rowing",
        value_fn=lambda d: d.cadence,
    ),
    RowerSensorDescription(
        key="strokes",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
        value_fn=lambda d: d.strokes,
    ),
    RowerSensorDescription(
        key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.speed_kmh,
    ),
    RowerSensorDescription(
        key="pace",
        native_unit_of_measurement="s/500m",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-outline",
        value_fn=lambda d: d.pace_s500,
    ),
    RowerSensorDescription(
        key="pace_mmss",
        icon="mdi:timer-outline",
        value_fn=lambda d: format_pace(d.pace_s500),
    ),
    RowerSensorDescription(
        key="distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.distance_m,
    ),
    RowerSensorDescription(
        key="calories",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:fire",
        value_fn=lambda d: d.calories,
    ),
    RowerSensorDescription(
        key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.power_w,
    ),
    RowerSensorDescription(
        key="resistance",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda d: d.resistance,
    ),
    RowerSensorDescription(
        key="heart_rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:heart-pulse",
        value_fn=lambda d: d.heart_rate,
    ),
    RowerSensorDescription(
        key="elapsed_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.elapsed_s,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DomyosRowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [DomyosRowerSensor(coordinator, desc) for desc in SENSORS]
        + [DomyosRowerStatusSensor(coordinator)]
    )


class DomyosRowerSensor(DomyosRowerEntity, SensorEntity):
    entity_description: RowerSensorDescription

    def __init__(
        self, coordinator: DomyosRowerCoordinator, description: RowerSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        return self.coordinator.connected

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.view)


class DomyosRowerStatusSensor(DomyosRowerEntity, SensorEntity):
    """Always-available diagnostic: what the integration is doing and the last error."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bluetooth-transfer"

    def __init__(self, coordinator: DomyosRowerCoordinator) -> None:
        super().__init__(coordinator, "status")

    @property
    def native_value(self) -> str:
        return self.coordinator.status

    @property
    def extra_state_attributes(self) -> dict:
        c = self.coordinator
        return {
            "protocol": c.mode,
            "power_calculated": c.power_is_calculated,
            "distance_scale": c.distance_scale,
            "last_error": c.last_error,
            "last_failed_step": c.last_operation,
            "consecutive_failures": c.failures,
            "services": c.services,
            "resistance_range": list(c.resistance_range),
            "resistance_range_from_rower": c.resistance_range_known,
        }

from itertools import product
import time
import pytest

from algo import Sampler
from data import alerts
from data.measurements import Measurements
from data.events import Events
from data.configurations import Configurations
from data.thresholds import (FlowRange, PressureRange,
                             RespiratoryRateRange, VolumeRange)
from drivers.driver_factory import DriverFactory


MICROSECOND = 10 ** -6
SIMULATION_LENGTH = 1  # seconds
LOW_THRESHOLD = -50000
HIGH_THRESHOLD = 50000


@pytest.fixture
def driver_factory():
    return DriverFactory(simulation_mode=True, simulation_data="sinus")


@pytest.fixture
def config():
    c = Configurations.instance()
    c.flow_range = FlowRange(min=0, max=30)
    c.pressure_range = PressureRange(min=0, max=30)
    c.resp_rate_range = RespiratoryRateRange(min=0, max=30)
    c.volume_range = VolumeRange(min=0, max=30)
    c.graph_seconds = 12
    c.debug_port = 7777
    c.breathing_threshold = 3.5
    c.log_enabled = False
    return c


@pytest.fixture
def measurements():
    return Measurements()


@pytest.fixture
def events():
    return Events()


def test_sampler_alerts_when_pressure_exceeds_minium(events, measurements, config, driver_factory):
    flow_sensor = driver_factory.get_driver("flow")
    pressure_sensor = driver_factory.get_driver("pressure")
    oxygen_a2d = driver_factory.get_driver("oxygen_a2d")
    sampler = Sampler(measurements, events, flow_sensor, pressure_sensor, oxygen_a2d)
    assert len(events.alerts_queue) == 0
    sampler.sampling_iteration()
    assert len(events.alerts_queue) == 0

    config.volume_range = VolumeRange(HIGH_THRESHOLD, HIGH_THRESHOLD)

    current_time = time.time()
    while time.time() - current_time < SIMULATION_LENGTH:
        time.sleep(MICROSECOND)
        sampler.sampling_iteration()

    assert len(events.alerts_queue) > 0

    all_alerts = list(events.alerts_queue.queue.queue)
    assert all(alert == alerts.AlertCodes.VOLUME_LOW for alert in all_alerts)


def test_sampler_alerts_when_pressure_exceeds_maximum(events, measurements, config, driver_factory):
    flow_sensor = driver_factory.get_driver("flow")
    pressure_sensor = driver_factory.get_driver("pressure")
    oxygen_a2d = driver_factory.get_driver("oxygen_a2d")
    sampler = Sampler(measurements, events, flow_sensor, pressure_sensor, oxygen_a2d)
    assert len(events.alerts_queue) == 0
    sampler.sampling_iteration()
    assert len(events.alerts_queue) == 0

    config.volume_range = VolumeRange(LOW_THRESHOLD, LOW_THRESHOLD)

    current_time = time.time()
    while time.time() - current_time < SIMULATION_LENGTH:
        time.sleep(MICROSECOND)
        sampler.sampling_iteration()

    assert len(events.alerts_queue) > 0

    all_alerts = list(events.alerts_queue.queue.queue)
    assert all(alert == alerts.AlertCodes.VOLUME_HIGH for alert in all_alerts)
import pytest

from algo import Sampler
from data.alert import AlertCodes
from data.measurements import Measurements
from data.events import Events
from data.configurations import Configurations
from data.thresholds import (O2Range, PressureRange,
                             RespiratoryRateRange, VolumeRange)
from drivers.driver_factory import DriverFactory

SIMULATION_SAMPLES = 1000
NO_BREATH_TIME = 13  # seconds


@pytest.fixture
def config():
    c = Configurations.instance()
    c.o2_range = O2Range(min=0, max=100)
    c.pressure_range = PressureRange(min=0, max=30)
    c.resp_rate_range = RespiratoryRateRange(min=0, max=30)
    c.volume_range = VolumeRange(min=0, max=600)
    c.graph_seconds = 12
    c.breathing_threshold = 3.5
    c.log_enabled = False
    return c


@pytest.fixture
def measurements():
    return Measurements()


@pytest.fixture
def events():
    return Events()


def test_sinus_alerts_when_no_breath(events, measurements, config):
    """Test that no-breath alert is sent after time without breathing

    Flow:
        * Run sinus simulation for a few cycles and make sure no alert was sent.
        * Don't simulate sensors for time required to sent no-breath alert.
        * Make sure a single no-breath alert was sent.
    """
    driver_factory = DriverFactory(simulation_mode=True, simulation_data="sinus")
    flow_sensor = driver_factory.acquire_driver("flow")
    pressure_sensor = driver_factory.acquire_driver("pressure")
    a2d = driver_factory.acquire_driver("a2d")
    timer = driver_factory.acquire_driver("timer")
    sampler = Sampler(measurements, events, flow_sensor, pressure_sensor,
                      a2d, timer)

    for _ in range(SIMULATION_SAMPLES):
        sampler.sampling_iteration()

    assert len(events.alert_queue) == 0

    # mocking time continue for no breath time.
    intervals = 1 / driver_factory.MOCK_SAMPLE_RATE_HZ
    num_of_samples = int(NO_BREATH_TIME / intervals)
    for _ in range(num_of_samples):
        sampler._timer.get_time()

    sampler.sampling_iteration()

    assert len(events.alert_queue) == 1

    alert = events.alert_queue.last_alert
    assert alert == AlertCodes.NO_BREATH


def test_dead_man_alerts_when_no_breath(events, measurements, config):
    """Test that no-breath alert is sent after time without breathing

    Flow:
        * Run deadman simulation for no-breath time.
        * Make sure at least one no-breath alert was sent.
    """
    driver_factory = DriverFactory(simulation_mode=True, simulation_data="dead")
    flow_sensor = driver_factory.acquire_driver("flow")
    pressure_sensor = driver_factory.acquire_driver("pressure")
    a2d = driver_factory.acquire_driver("a2d")
    timer = driver_factory.acquire_driver("timer")
    sampler = Sampler(measurements, events, flow_sensor, pressure_sensor,
                      a2d, timer)

    time_intervals = 1 / driver_factory.MOCK_SAMPLE_RATE_HZ
    num_of_samples = int(NO_BREATH_TIME / time_intervals)
    for _ in range(num_of_samples):
        sampler.sampling_iteration()

    assert len(events.alert_queue) >= 1

    all_alerts = list(events.alert_queue)
    assert all(alert == AlertCodes.NO_BREATH for alert in all_alerts)


def test_noise_alerts_when_no_breath(events, measurements, config):
    """Test that no-breath alert is sent after time without breathing

    Flow:
        * Run noise simulation for no-breath time.
        * Make sure at least one no-breath alert was sent.
    """
    driver_factory = DriverFactory(simulation_mode=True, simulation_data="noise")
    flow_sensor = driver_factory.acquire_driver("flow")
    pressure_sensor = driver_factory.acquire_driver("pressure")
    a2d = driver_factory.acquire_driver("a2d")
    timer = driver_factory.acquire_driver("timer")
    sampler = Sampler(measurements, events, flow_sensor, pressure_sensor,
                      a2d, timer)

    time_intervals = 1 / driver_factory.MOCK_SAMPLE_RATE_HZ
    num_of_samples = int(NO_BREATH_TIME / time_intervals)
    for _ in range(num_of_samples):
        sampler.sampling_iteration()

    assert len(events.alert_queue) >= 1

    all_alerts = list(events.alert_queue)
    assert all(alert == AlertCodes.NO_BREATH for alert in all_alerts)

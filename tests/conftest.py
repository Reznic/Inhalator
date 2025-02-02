import pytest

from algo import Sampler
from data.configurations import ConfigurationManager
from data.events import Events
from data.measurements import Measurements
from drivers.driver_factory import DriverFactory
from unittest.mock import patch


@pytest.fixture
def config_path(tmpdir):
    return tmpdir / "config.json"


@pytest.fixture
def events():
    e = Events()
    e.alerts_queue.initial_uptime = 0
    return e


@pytest.fixture
def configuration_manager(config_path, events):
    return ConfigurationManager.initialize(events, config_path)


@pytest.fixture
def default_config(configuration_manager, events):
    # For the sake of tests, some of the defaults are really not appropriate
    # and should be modified
    c = configuration_manager.config
    c.boot_alert_grace_time = 0
    return c


@pytest.fixture
def config(default_config):
    return default_config


@pytest.fixture
def measurements(default_config):
    return Measurements(default_config.graph_seconds)


@pytest.fixture
def driver_factory(data):
    return DriverFactory(simulation_mode=True, simulation_data=data)


@pytest.yield_fixture
def abp_driver():
    with patch('drivers.i2c_driver.pigpio.pi') as pigpio_mock:
        patch('drivers.mux_i2c.MuxI2C.lock')
        from drivers.abp_pressure_sensor import AbpPressureSensor
        yield AbpPressureSensor()


@pytest.yield_fixture
def hsc_driver():
    with patch('drivers.i2c_driver.pigpio.pi') as pigpio_mock:
        patch('drivers.mux_i2c.MuxI2C.lock')
        from drivers.hsc_pressure_sensor import HscPressureSensor
        yield HscPressureSensor()


@pytest.yield_fixture
def a2d_driver():
    with patch('spidev.SpiDev') as spidev_mock:
        from drivers.ads7844_a2d import Ads7844A2D
        yield Ads7844A2D()


@pytest.fixture
def sim_sampler(driver_factory, config, measurements, events):
    flow_sensor = driver_factory.flow
    pressure_sensor = driver_factory.pressure
    a2d = driver_factory.a2d
    timer = driver_factory.timer
    sampler = Sampler(
        measurements=measurements,
        events=events,
        flow_sensor=flow_sensor,
        pressure_sensor=pressure_sensor,
        a2d=a2d,
        timer=timer)
    return sampler

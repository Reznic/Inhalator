import time
import logging
import threading
from enum import Enum
from statistics import mean
from collections import deque

from data.alerts import AlertCodes
from data.measurements import Measurements
from data.configurations import Configurations


class VolumeAccumulator(object):
    def __init__(self):
        self.air_volume_liter = 0
        self.last_sample_ts = None

    def accumulate(self, timestamp, air_flow):
        if self.last_sample_ts is not None:
            elapsed_time_seconds = timestamp - self.last_sample_ts
            elapsed_time_minutes = elapsed_time_seconds / 60
            # flow is measured in Liter/minute, so we multiply the last read by
            # the time elapsed in minutes to calculate the accumulated volume
            # inhaled in this inhale.
            self.air_volume_liter += air_flow * elapsed_time_minutes
        self.last_sample_ts = timestamp

    def reset(self):
        self.air_volume_liter = 0
        self.last_sample_ts = None


class RunningAvg(object):

    def __init__(self, max_samples):
        self.max_samples = max_samples
        self.samples = deque(maxlen=max_samples)

    def reset(self):
        self.samples.clear()

    def process(self, pressure):
        self.samples.append(pressure)
        return mean(self.samples)


class VentilationState(Enum):
    Inhale = 0
    Exhale = 1
    PEEP = 2


class RateMeter(object):

    def __init__(self, time_span_seconds):
        """
        :param time_span_seconds: How long (seconds) the sliding window of the
            running average should be
        """
        if time_span_seconds <= 0:
            raise ValueError("Time span must be non-zero and positive")
        self.time_span_seconds = time_span_seconds
        self.samples = deque()

    def reset(self):
        self.samples.clear()

    def beat(self, timestamp=None):
        now = time.time()
        if timestamp is None:
            timestamp = now
        self.samples.append(timestamp)
        # Discard beats older than `self.time_span_seconds`
        while self.samples[0] < (now - self.time_span_seconds):
            self.samples.popleft()

        # Basically the rate is the number of elements left, since the container
        # represents only the relevant time span.
        # BUT there is a corner-case at the beginning of the process - what if
        # we did not yet passed a single time span? The rate then will be
        # artificially low. For example on the first two beats, even if there
        # are only 10 seconds between them and the time span is 60 seconds, the
        # rate will be 2/min, instead of 6/min (1 beats every 10 seconds).
        # This is why we compute the interval between the oldest and newest beat
        # in the data, and calculate the rate based on it. After we accumulate
        # enough data, this interval will be pretty close to the desired span.
        oldest = self.samples[0]
        interval = now - oldest
        # protect against division by zero
        if interval == 0:
            # Technically rate is infinity, but 0 will be more descriptive
            return 0

        # We subtract 1 because we have both 1st and last sentinels.
        rate = (len(self.samples) - 1) * (self.time_span_seconds / interval)
        return rate


class Sampler(threading.Thread):
    SAMPLING_INTERVAL = 0.02  # sec
    MS_IN_MIN = 60 * 1000
    ML_IN_LITER = 1000

    def __init__(self, measurements, events, flow_sensor, pressure_sensor):
        super(Sampler, self).__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self.daemon = True
        self._measurements = measurements  # type: Measurements
        self._flow_sensor = flow_sensor
        self._pressure_sensor = pressure_sensor
        self._config = Configurations.instance()
        self._events = events
        self.accumulator = VolumeAccumulator()
        # No good reason for 1000 max samples. Sounds enough.
        self.peep_avg_calculator = RunningAvg(max_samples=1000)
        self.breathes_rate_meter = RateMeter(time_span_seconds=60)
        self.alerts = AlertCodes.OK

        # State
        self.handlers = {
            VentilationState.Inhale: self.handle_inhale,
            VentilationState.Exhale: self.handle_exhale,
            VentilationState.PEEP: self.handle_peep
        }

        self.current_state = VentilationState.Inhale  # Initial Value
        self.last_pressure = 0
        self._inhale_max_flow = 0
        self._inhale_max_pressure = 0
        self._has_crossed_first_cycle = False
        self._is_during_intake = False

    def handle_inhale(self, flow_slm, pressure):
        ts = time.time()
        if pressure <= self.last_pressure:
            self.log.debug("Inhale volume: %s" % self.accumulator.air_volume_liter)
            self._inhale_finished(ts)
            return

        self.accumulator.accumulate(ts, flow_slm)

        if (self._config.volume_threshold.max != 'off' and
                self.accumulator.air_volume_liter >
                self._config.volume_threshold.max):
            self.alerts |= AlertCodes.VOLUME_HIGH

        if pressure <= self._config.breathing_threshold:
            self._has_crossed_first_cycle = True

        self._inhale_max_pressure = max(pressure, self._inhale_max_pressure)
        self._inhale_max_flow = max(flow_slm, self._inhale_max_flow)

    def _inhale_finished(self, timestamp):
        self.log.debug("Inhale finished. Exhale starts")
        self._measurements.bpm = self.breathes_rate_meter.beat(timestamp)
        if (self._config.volume_threshold.min != "off" and
                self.accumulator.air_volume_liter <
                self._config.volume_threshold.min and
                self._has_crossed_first_cycle):

            self.alerts |= AlertCodes.VOLUME_LOW

        self._measurements.set_intake_peaks(self._inhale_max_pressure,
                                            self._inhale_max_pressure,
                                            self.accumulator.air_volume_liter)
        # reset values of last intake
        self.accumulator.reset()
        self._inhale_max_flow = 0
        self._inhale_max_pressure = 0
        self.current_state = VentilationState.Exhale

    def handle_exhale(self, flow, pressure):
        if pressure < self._config.breathing_threshold:
            self.current_state = VentilationState.PEEP

    def handle_peep(self, flow, pressure):
        # peep_avg = self.peep_avg_calculator.process(pressure)
        if pressure > self._config.breathing_threshold:
            # self.log.debug("Last PEEP: %s", peep_avg)
            self.current_state = VentilationState.Inhale

    def run(self):
        while True:
            self.sampling_iteration()
            time.sleep(self.SAMPLING_INTERVAL)

    def sampling_iteration(self):
        # Read from sensors
        flow_slm = self._flow_sensor.read()
        pressure_cmh2o = self._pressure_sensor.read()

        handler = self.handlers.get(self.current_state)
        handler(flow_slm, pressure_cmh2o)
        self._measurements.set_pressure_value(pressure_cmh2o)

        if self._config.pressure_threshold.max != "off" and \
                pressure_cmh2o > self._config.pressure_threshold.max:
            # Above healthy lungs pressure
            self.alerts |= AlertCodes.PRESSURE_HIGH

        if self._config.pressure_threshold.max != "off" and \
                pressure_cmh2o < self._config.pressure_threshold.min:
            # Below healthy lungs pressure
            self.alerts |= AlertCodes.PRESSURE_LOW

        self._measurements.set_flow_value(flow_slm)

        if (self.alerts != AlertCodes.OK and
                self._events.alerts_queue.last_alert != self.alerts):
            self._events.alerts_queue.enqueue_alert(self.alerts)
        self.last_pressure = pressure_cmh2o

import time
import logging
import threading

from data.alerts import Alert, AlertCodes

log = logging.getLogger(__name__)


class Sampler(threading.Thread):
    SAMPLING_INTERVAL = 0.02  # sec
    MS_IN_MIN = 60 * 1000
    OXYGEN_A2D_SAMPLE_CHANNELS = [0]

    def __init__(self, data_store, flow_sensor, pressure_sensor, oxygex_a2d):
        super(Sampler, self).__init__()
        self.daemon = True
        self._data_store = data_store  # type: DataStore
        self._flow_sensor = flow_sensor
        self._pressure_sensor = pressure_sensor
        self._oxygen_a2d = oxygex_a2d

        # State
        self._currently_breathed_volume = 0
        self._is_during_intake = False
        self._has_crossed_first_cycle = False

        # Alerts related
        self.breathing_alert = AlertCodes.OK
        self.pressure_alert = AlertCodes.OK

    def _handle_intake(self, flow, pressure):
        """We are giving patient air."""
        sampling_interval_in_minutes = self.SAMPLING_INTERVAL / self.MS_IN_MIN
        self._currently_breathed_volume += \
            (flow * sampling_interval_in_minutes)

        if self._currently_breathed_volume > self._data_store.flow_max_threshold.value:
            self.breathing_alert = AlertCodes.BREATHING_VOLUME_HIGH

        if pressure <= self._data_store.breathing_threshold:
            self._has_crossed_first_cycle = True

    def _handle_intake_finished(self, flow, pressure):
        """We are not giving patient air anymore."""

        if self._currently_breathed_volume < self._data_store.flow_min_threshold.value and \
                self._has_crossed_first_cycle:

            self.breathing_alert = AlertCodes.BREATHING_VOLUME_LOW

        self._currently_breathed_volume = 0

    def run(self):
        while True:
            self.sampling_iteration()
            time.sleep(self.SAMPLING_INTERVAL)

    def sampling_iteration(self):
        # Clear alerts calculation
        self.breathing_alert = AlertCodes.OK
        self.pressure_alert = AlertCodes.OK

        # Read from sensors
        flow_value = self._flow_sensor.read_flow_slm()
        pressure_value = self._pressure_sensor.read_pressure()
        oxygen_value = self._oxygen_a2d.sample_a2d_channels(
            self.OXYGEN_A2D_SAMPLE_CHANNELS)

        print("oxygen", oxygen_value)

        self._data_store.set_pressure_value(pressure_value)

        if pressure_value > self._data_store.pressure_max_threshold.value:
            # Above healthy lungs pressure
            self.pressure_alert = AlertCodes.PRESSURE_HIGH
        if pressure_value < self._data_store.pressure_min_threshold.value:
            # Below healthy lungs pressure
            self.pressure_alert = AlertCodes.PRESSURE_LOW

        logging.debug("Breathed: %s" % self._currently_breathed_volume)
        logging.debug("Flow: %s" % flow_value)
        logging.debug("Pressure: %s" % pressure_value)

        if pressure_value <= self._data_store.breathing_threshold:
            logging.debug("-----------is_during_intake=False----------")
            self._is_during_intake = False

        if pressure_value > self._data_store.breathing_threshold:
            logging.debug("-----------is_during_intake=True-----------")
            self._is_during_intake = True

        if self._is_during_intake:
            self._handle_intake(flow=flow_value, pressure=pressure_value)

        else:
            self._handle_intake_finished(flow=flow_value,
                                         pressure=pressure_value)

        self._data_store.set_flow_value(flow_value)

        # TODO: Multiplied by 100000 just so it looks good on graph, delete this
        self._data_store.update_volume_value(self._currently_breathed_volume * 100000)

        alert = Alert(self.breathing_alert | self.pressure_alert)
        if alert != AlertCodes.OK and self._data_store.alerts_queue.last_alert != alert:
            self._data_store.alerts_queue.enqueue_alert(alert)

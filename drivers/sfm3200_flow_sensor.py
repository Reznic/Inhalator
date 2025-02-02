"""SFM3200 air flow sensor driver.

The use of this driver requires pigpio deamon:
'sudo pigpiod'
(sudo apt-get install pigpio)
"""
from time import sleep
import logging
import pigpio

from .i2c_driver import I2cDriver
from errors import (I2CReadError,
                    I2CWriteError,
                    FlowSensorCRCError,
                    I2CDeviceNotFoundError)

log = logging.getLogger(__name__)


class Sfm3200(I2cDriver):
    """Driver class for SFM3200 Flow sensor."""
    CRC_POLYNOMIAL = 0x131
    I2C_ADDRESS = 0x40
    SCALE_FACTOR_FLOW = 120
    OFFSET_FLOW = 0x8000
    START_MEASURE_CMD = b"\x10\x00"
    SOFT_RST_CMD = b"\x20\x00"

    def __init__(self):
        super().__init__()
        self._start_measure()
        sleep(0.1)
        # Dummy read - first read values are invalid
        read_size, dummy = self._pig.i2c_read_device(self._dev, 3)
        if read_size == pigpio.PI_I2C_READ_FAILED:
            log.error("Could not read first data from flow sensor."
                      "Is it connected?")
            raise I2CDeviceNotFoundError("i2c read failed")

        log.debug(f"Flow sensor: Successfully read dummy values: {dummy}")

    # Todo: Implement read serial number command

    def _start_measure(self):
        try:
            self._pig.i2c_write_device(self._dev, self.START_MEASURE_CMD)
        except pigpio.error as e:
            log.error("Could not write start_measure cmd to flow sensor. "
                      "Is the flow sensor connected?.")
            raise I2CWriteError("i2c write failed") from e

        log.info("Started flow sensor measurement")

    def soft_reset(self):
        try:
            self._pig.i2c_write_device(self._dev, self.SOFT_RST_CMD)
        except pigpio.error as e:
            log.error("Could not write soft reset cmd to flow sensor.")
            raise I2CWriteError("i2c write failed") from e

    def read(self, retries=2):
        read_size, data = self._pig.i2c_read_device(self._dev, 3)
        if read_size >= 2:
            raw_value = data[0] << 8 | data[1]

            if read_size == 3:
                expected_crc = data[2]
                crc_calc = self._crc8(data[:2])
                if crc_calc != expected_crc:
                    log.error("CRC mismatch while reading data from flow sensor. "
                              "%s - expected %s", crc_calc, expected_crc)
                    raise FlowSensorCRCError("CRC mismatch")
            else:
                log.error("Too much data received, "
                          "got %s expected 3. data: %s", len(data), data)
                raise I2CReadError("Too much data read, invalid state")

        elif read_size == 0:
            # Measurement not ready
            if not retries:
                log.error("Flow sensor's measure data consistently not ready")

            elif retries == 1:
                log.warning("Flow sensor read returns NA."
                            "This could be a result of voltage swings."
                            "Sending start_measure command to sensor")
                self._start_measure()

            else:
                log.warning("Flow sensor's measure data was not ready. "
                            "Retrying read after a short delay")

            sleep(0.1)
            flow = self.read_flow_slm(retries=retries - 1)
            log.info("Flow Sensor successfully read data, after failed attempt")
            return flow

        elif read_size == pigpio.PI_raw_valueI2C_READ_FAILED:
            log.error("Could not read data from flow sensor."
                      "Is it connected?")
            raise I2CReadError("i2c read failed")

        # Normalize flow to slm units
        flow = float(raw_value - self.OFFSET_FLOW) / self.SCALE_FACTOR_FLOW
        return flow

    def _crc8(self, data):
        crc = 0
        for b in data:
            crc = crc ^ b
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ self.CRC_POLYNOMIAL
                else:
                    crc = crc << 1
        return crc

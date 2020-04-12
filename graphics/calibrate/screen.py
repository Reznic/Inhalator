import math
import statistics
from tkinter import *

from data.configurations import Configurations
from graphics.themes import Theme


class Calibration(object):
    CALIBRATED_DRIVER = NotImplemented
    PRE_CALIBRATE_ALERT_MSG = NotImplemented
    NUMBER_OF_SAMPLES_TO_TAKE = 100
    SLEEP_IN_BETWEEN = 3 / 100

    def __init__(self, parent, root, drivers):
        self.parent = parent
        self.root = root

        self.sensor_driver = drivers.acquire_driver(self.CALIBRATED_DRIVER)
        self.timer = drivers.acquire_driver("timer")
        self.watch_dog = drivers.acquire_driver("wd")

        self.frame = Frame(master=self.root)
        self.label = Label(master=self.frame,
                           text=self.PRE_CALIBRATE_ALERT_MSG,
                           font=("Roboto", 16),
                           bg=Theme.active().BACKGROUND,
                           fg=Theme.active().TXT_ON_BG)

        self.button = Button(master=self.frame,
                             bg=Theme.active().SURFACE,
                             command=self.calibrate,
                             fg=Theme.active().TXT_ON_SURFACE,
                             text="Calibrate")

        # State
        self.average_value_found = None

    @property
    def offset_configuration(self):
        raise NotImplemented

    def read_raw_value(self):
        raise NotImplemented

    def get_difference(self):
        """Get offset drift."""
        return self.average_value_found - self.offset_configuration

    def calibrate(self):
        # TODO: Handle watchdog

        values = []

        # Read values from sensor
        for index in range(self.NUMBER_OF_SAMPLES_TO_TAKE):
            # Inform User
            waiting_time_left = ((self.NUMBER_OF_SAMPLES_TO_TAKE - index ) *
                                 self.SLEEP_IN_BETWEEN)

            self.label.configure(
                text=f"Please wait {math.ceil(waiting_time_left)} seconds...")
            self.button.configure(state="disabled")

            self.label.update()  # This is needed so the GUI doesn't freeze

            values.append(self.read_raw_value())

            self.timer.sleep(self.SLEEP_IN_BETWEEN)

        self.average_value_found = statistics.mean(values)
        self.label.configure(text=f"Offset found: {self.get_difference():.5f}")
        self.button.configure(state="normal")
        self.parent.enable_ok_button()
        self.button.configure(text="Recalibrate")

    def render(self):
        self.frame.place(relx=0, rely=0.25, relwidth=1, relheight=0.5)
        self.label.place(relx=0, rely=0, relheight=0.5, relwidth=1)
        self.button.place(relx=0, rely=0.5, relheight=0.5, relwidth=1)

    def save(self):
        raise NotImplemented


class OKCancelSection(object):
    def __init__(self, parent, root):
        self.parent = parent
        self.root = root
        self.frame = Frame(master=self.root, bg=Theme.active().BACKGROUND)
        self.ok_button = Button(master=self.frame,
                                command=self.parent.on_ok,
                                bg=Theme.active().SURFACE,
                                fg=Theme.active().TXT_ON_SURFACE,
                                state="disabled",
                                text="OK")
        self.cancel_button = Button(master=self.frame,
                                    bg=Theme.active().SURFACE,
                                    command=self.parent.on_cancel,
                                    fg=Theme.active().TXT_ON_SURFACE,
                                    text="Cancel")

    def render(self):
        self.frame.place(relx=0, rely=0.75, relwidth=1, relheight=0.25)
        self.ok_button.place(relx=0, rely=0, relwidth=0.5, relheight=1)
        self.cancel_button.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

    def enable_ok_button(self):
        self.ok_button.configure(state="normal")


class Title(object):
    def __init__(self, parent, root, title_str):
        self.parent = parent
        self.root = root
        self.frame = Frame(master=self.root)
        self.label = Label(master=self.frame,
                           text=title_str,
                           font=("Roboto", 20),
                           bg=Theme.active().BACKGROUND,
                           fg=Theme.active().TXT_ON_BG)

    def render(self):
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=0.25)
        self.label.place(relx=0, rely=0, relheight=1, relwidth=1)


class CalibrationScreen(object):
    def __init__(self, root, calibration_class, drivers):
        self.root = root
        self.calibration_class = calibration_class

        self.screen = Frame(master=self.root, bg="red")
        self.calibration = self.calibration_class(self, self.screen, drivers)
        self.title = Title(self, self.screen, self.calibration.NAME)
        self.ok_cancel_section = OKCancelSection(self, self.screen)

    def show(self):
        self.screen.place(relx=0.1, rely=0.15, relheight=0.7, relwidth=0.8)
        self.title.render()
        self.calibration.render()
        self.ok_cancel_section.render()

    def hide(self):
        self.screen.place_forget()

    def enable_ok_button(self):
        self.ok_cancel_section.enable_ok_button()

    def on_ok(self):
        self.calibration.save()
        self.hide()

    def on_cancel(self):
        self.hide()


class DifferentialPressureCalibration(Calibration):
    NAME = "Flow Calibration"
    CALIBRATED_DRIVER = "differential_pressure"
    PRE_CALIBRATE_ALERT_MSG = \
        "Please make sure tubes are detached from flow sensor!"

    def read_raw_value(self):
        return self.sensor_driver.read_differential_pressure()

    @property
    def offset_configuration(self):
        return Configurations.instance().dp_offset

    def save(self):
        Configurations.instance().dp_offset = self.average_value_found
        self.sensor_driver.set_calibration_offset(self.average_value_found)
        Configurations.instance().save_to_file()

class OxygenCalibration(Calibration):
    NAME = "O2 sensor Calibration"
    CALIBRATED_DRIVER = "a2d"
    PRE_CALIBRATE_ALERT_MSG = \
        "Please make sure system in 100% oxygen, and tube connected to sensor."

    def read_raw_value(self):
        return self.sensor_driver.read_oxygen_raw()

    @property
    def offset_configuration(self):
        return Configurations.instance().oxygen_offset

    def save(self):
        Configurations.instance().oxygen = self.average_value_found
        self.sensor_driver.set_oxygen_calibration_offset(self.average_value_found)
        Configurations.instance().save_to_file()

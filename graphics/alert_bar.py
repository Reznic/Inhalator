import os
import time

import timeago
import datetime
from tkinter import *

from data.alerts import Alert, AlertCodes
from graphics.themes import Theme
from data.configurations import ConfigurationManager
from graphics.version import __version__

THIS_DIRECTORY = os.path.dirname(__file__)
RESOURCES_DIRECTORY = os.path.join(os.path.dirname(THIS_DIRECTORY),
                                   "resources")


class IndicatorAlertBar(object):
    BATTERY_OK_PATH = os.path.join(RESOURCES_DIRECTORY,
                                   "baseline_battery_full_white_18dp.png")
    BATTERY_LOW_PATH = os.path.join(RESOURCES_DIRECTORY,
                                    "baseline_battery_alert_white_18dp.png")
    BATTERY_MISSING_PATH = os.path.join(
        RESOURCES_DIRECTORY,
        "baseline_battery_unknown_white_18dp.png")
    R_LETTER_PATH = os.path.join(RESOURCES_DIRECTORY, "r_letter.png")

    def __init__(self, parent, events, drivers, measurements, record_sensors=False):
        self.parent = parent
        self.root = parent.element
        self.events = events
        self.config = ConfigurationManager.config()
        self.drivers = drivers
        self.measurements = measurements

        self.height = self.parent.height
        self.width = self.parent.width

        self.bar = Frame(self.root, bg=Theme.active().ALERT_BAR_OK,
                         height=self.height, width=self.width)

        self.message_label = Label(master=self.bar,
                                   font=("Roboto", 32),
                                   text="OK",
                                   bg=Theme.active().ALERT_BAR_OK,
                                   fg=Theme.active().ALERT_BAR_OK_TXT,)

        self.timestamp_label = Label(master=self.root,
                                     font=("Roboto", 12),
                                     text="",
                                     fg=Theme.active().ALERT_BAR_OK_TXT,
                                     bg=Theme.active().ALERT_BAR_OK)

        self.system_info_frame = Frame(master=self.root,
                                       bg=Theme.active().ALERT_BAR_OK)  # TODO: Implement a tk.style
        self.battery_ok_image = PhotoImage(name="ok",
                                           file=self.BATTERY_OK_PATH)
        self.battery_low_image = PhotoImage(name="low",
                                            file=self.BATTERY_LOW_PATH)
        self.battery_missing_image = PhotoImage(name="missing",
                                                file=self.BATTERY_MISSING_PATH)
        self.r_letter_image = PhotoImage(name="r_letter", file=self.R_LETTER_PATH)

        self.battery_icon = Label(master=self.system_info_frame,
                                  image=self.battery_ok_image,
                                  fg=Theme.active().ALERT_BAR_OK_TXT,
                                  bg=Theme.active().ALERT_BAR_OK)

        self.battery_label = Label(master=self.system_info_frame,
                                   font=("Roboto", 9),
                                   text="",
                                   fg=Theme.active().ALERT_BAR_OK_TXT,
                                   bg=Theme.active().ALERT_BAR_OK)

        self.version_label = Label(master=self.system_info_frame,
                                   font=("Roboto", 9),
                                   text="Ver. {}".format(__version__),
                                   fg=Theme.active().ALERT_BAR_OK_TXT,
                                   bg=Theme.active().ALERT_BAR_OK)


        record_sensors_image = {True: self.r_letter_image, False: None}
        self.record_sensors = Label(master=self.system_info_frame,
                                    image=record_sensors_image[record_sensors],
                                    fg=Theme.active().ALERT_BAR_OK_TXT,
                                    bg=Theme.active().ALERT_BAR_OK)


        self.current_alert = Alert(AlertCodes.OK)

    @property
    def element(self):
        return self.bar

    @property
    def frames(self):
        return [self.bar, self.system_info_frame]

    @property
    def textual(self):
        """Return all textual tkinter widgets, for color configuration."""
        return [self.version_label, self.timestamp_label,
                self.message_label, self.battery_label,
                self.battery_icon, self.record_sensors]

    def render(self):
        self.bar.place(relx=0, rely=0)
        self.message_label.place(anchor="nw", relx=0.03, rely=0.05)
        self.timestamp_label.place(anchor="nw", relx=0.04, rely=0.7)
        self.system_info_frame.place(relx=0.7, rely=0.05,
                                     relheight=0.8, relwidth=0.3)
        self.battery_label.place(relx=0.75, rely=0)
        self.battery_icon.place(relx=0.6, rely=0)
        self.version_label.place(relx=0.3, rely=0.7)
        self.record_sensors.place(relx=0.35, rely=0)

    def update(self):
        # Check mute time limit
        if self.events.mute_alerts._alerts_muted and\
                (time.time() - self.events.mute_alerts.mute_time) >\
                self.config.mute_time_limit:
            self.events.mute_alerts.mute_alerts(False)
        last_alert_in_queue = self.events.alerts_queue.last_alert

        # If the queue says everything is ok, and the graphics shows
        # otherwise, change the graphics state and update the GUI
        if last_alert_in_queue == AlertCodes.OK:
            if self.current_alert != AlertCodes.OK:
                self.current_alert = Alert(AlertCodes.OK)
                self.set_no_alert()

        # If the queue says there's an issue, and graphics shows
        # everything to be okay, change the graphics state and update the GUI
        else:
            if self.current_alert == AlertCodes.OK:
                self.current_alert = last_alert_in_queue
                self.set_alert(last_alert_in_queue)

        self.update_timestamp_label()

        # Handle battery
        self.update_battery()

    def set_no_alert(self):
        # Change background colors
        for frame in self.frames:
            frame.config(bg=Theme.active().ALERT_BAR_OK)

        # Change text colors
        for label in self.textual:
            label.config(bg=Theme.active().ALERT_BAR_OK,
                         fg=Theme.active().ALERT_BAR_OK_TXT)

        self.message_label.configure(text="OK")
        self.timestamp_label.configure(text="")

    def set_alert(self, alert: Alert):
        # Change background colors
        for frame in self.frames:
            frame.config(bg=Theme.active().ERROR)

        # Change text colors
        for label in self.textual:
            label.configure(bg=Theme.active().ERROR,
                            fg=Theme.active().TXT_ON_ERROR)

        self.message_label.configure(text=str(alert))

    def update_timestamp_label(self):
        if self.current_alert == AlertCodes.OK:
            self.timestamp_label.configure(text="")
            return

        # We can't use simple alert.date() or time.time() for this calculation
        # because we want to support both simulation mode and real mode.
        # hence, we look at the differential time since the alert
        # last happened.
        now = self.drivers.timer.get_current_time()
        then = self.current_alert.timestamp

        now_dt = datetime.datetime.fromtimestamp(now)
        then_dt = datetime.datetime.fromtimestamp(then)

        # This display a '2 minutes ago' text
        time_ago = timeago.format(now_dt - then_dt)
        self.timestamp_label.configure(text=f"{time_ago}")

    def update_battery(self):
        current_battery = self.measurements.battery_percentage
        battery_is_low = current_battery < self.config.low_battery_percentage
        battry_is_missing = self.current_alert.contains(AlertCodes.NO_BATTERY)

        if battry_is_missing:
            self.battery_icon.configure(image=self.battery_missing_image)

        else:
            if battery_is_low:
                self.battery_icon.configure(image=self.battery_low_image)

            else:
                self.battery_icon.configure(image=self.battery_ok_image)

            self.battery_label.configure(text=f"{current_battery}%")

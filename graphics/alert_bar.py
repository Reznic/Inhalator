import time
# Tkinter stuff
import platform

from graphics.themes import Theme

if platform.python_version() < '3':
    from Tkinter import *

else:
    from tkinter import *

from data import alerts, events, configurations

from drivers.driver_factory import DriverFactory

from data.configurations import Configurations


class IndicatorAlertBar(object):
    error_dict = {
        alerts.AlertCodes.PRESSURE_LOW: "Low Pressure",
        alerts.AlertCodes.PRESSURE_HIGH: "High Pressure",
        alerts.AlertCodes.BREATHING_VOLUME_LOW: "Low Volume",
        alerts.AlertCodes.BREATHING_VOLUME_HIGH: "High Volume"
    }

    def __init__(self, parent, events, drivers):
        self.parent = parent
        self.root = parent.element
        self.events = events
        self.configs = Configurations.instance()
        self.drivers = drivers

        self.height = self.parent.height
        self.width = self.parent.width

        self.bar = Frame(self.root, bg=Theme.active().ALERT_BAR_OK,
                         height=self.height, width=self.width)
        self.message_label = Label(master=self.bar,
                                   font=("Roboto", 34),
                                   text="OK",
                                   bg=Theme.active().ALERT_BAR_OK,
                                   fg=Theme.active().ALERT_BAR_OK_TXT,)

        self.sound_device = drivers.get_driver("aux")

    @property
    def element(self):
        return self.bar

    def render(self):
        self.bar.place(relx=0, rely=0)
        self.message_label.place(anchor="nw", relx=0.03, rely=0.2)

    def update(self):
        # Check mute time limit
        if (self.events.mute_alerts and
                    (time.time() - self.events.mute_time) >
                    self.configs.mute_time_limit):
            self.events.mute_alerts = False

        last_alert_code = self.events.alerts_queue.last_alert.code
        if last_alert_code == alerts.AlertCodes.OK:
            self.set_no_alert()
        else:
            self.set_alert(self.error_dict.get(last_alert_code, "Multiple Errors"))

    def set_no_alert(self):
        self.bar.config(bg=Theme.active().ALERT_BAR_OK)
        self.message_label.config(bg=Theme.active().ALERT_BAR_OK,
                                  fg=Theme.active().ALERT_BAR_OK_TXT,
                                  text="OK")
        self.sound_device.stop()

    def set_alert(self, message):
        self.bar.config(bg=Theme.active().ERROR)
        self.message_label.config(bg=Theme.active().ERROR,
                                  fg=Theme.active().TXT_ON_ERROR, text=message)
        if self.events.mute_alerts:
            self.sound_device.stop()

        else:
            self.sound_device.start()

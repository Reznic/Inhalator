from queue import Queue


class DataStore(object):
    THRESHOLD_STEP_SIZE = 0.5
    NO_BREATHING_THRESHOLD = 3.5  # mbar
    BREATHING_THRESHOLD = 3.5  # mbar

    def __init__(self):
        self.pressure_min_threshold = [1]  # mbar
        self.pressure_max_threshold = [15]  # mbar
        self.flow_min_threshold = [0.3] # Liter
        self.flow_max_threshold = [15]
        self.flow_display_values = [0] * 40
        self.pressure_display_values = range(0, 40)
        self.x_axis = range(0, 40)
        self.alerts = Queue(maxsize=10)
        self.arm_wd = False

    def update_flow_values(self, new_value):
        if len(self.flow_display_values) == len(self.x_axis):
            self.flow_display_values.pop(0)
        self.flow_display_values.append(new_value)

    def update_pressure_values(self, new_value):
        if len(self.pressure_display_values) == len(self.x_axis):
            self.pressure_display_values.pop(0)
        self.pressure_display_values.append(new_value)

    def set_alert(self, alert):
        self.alerts.put(alert)

    def get_alert(self):
        return self.alerts.get()

import time
from tkinter import Frame

import freezegun
import pytest
from unittest.mock import MagicMock

from data.alert import Alert, AlertCodes
from data.alert_queue import AlertQueue
from data.events import Events
from drivers.driver_factory import DriverFactory
from graphics.alerts_history.history_screen import HistoryScreen
from graphics.themes import Theme, DarkTheme


@pytest.fixture
def screen() -> HistoryScreen:
    Theme.ACTIVE_THEME = DarkTheme()
    events = Events()

    return HistoryScreen(root=Frame(), events=events)


def test_an_alert_is_shown_on_screen(screen: HistoryScreen):
    with freezegun.freeze_time("12th February 2000"):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    screen.show()
    screen.on_refresh_button_click()

    assert len([alert for alert in screen.entries_container.alerts_displayed
                if alert is not None]) == 1
    assert screen.entries_container.alerts_displayed[0] == AlertCodes.NO_BREATH

    with freezegun.freeze_time("12th February 2000"):
        assert screen.entries_container.alerts_displayed[0].timestamp == time.time()

def test_scrolling_down_when_not_enough_alerts(screen: HistoryScreen):
    with freezegun.freeze_time("12th February 2000"):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    screen.show()
    screen.on_refresh_button_click()
    screen.on_scroll_down()

    assert screen.entries_container.index == 0
    assert screen.entries_container.factory.entries[0].entry.index_label["text"] == "1"

def test_scrolling_up_when_on_top(screen: HistoryScreen):
    with freezegun.freeze_time("12th February 2000"):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    screen.show()
    screen.on_refresh_button_click()
    screen.on_scroll_up()

    assert screen.entries_container.index == 0
    assert screen.entries_container.factory.entries[0].entry.index_label["text"] == "1"


def test_scrolling_down_at_the_bottom(screen: HistoryScreen):
    for i in range(screen.entries_container.NUMBER_OF_ALERTS_ON_SCREEN):
        screen.events.alert_queue.enqueue_alert(1 << i, time.time())

    screen.show()
    screen.on_refresh_button_click()

    assert screen.entries_container.index == 0

    screen.on_scroll_down()

    assert len([alert for alert in screen.entries_container.alerts_displayed
                if alert is not None]) == \
           screen.entries_container.NUMBER_OF_ALERTS_ON_SCREEN
    assert screen.entries_container.index == 0

    for i in range(screen.entries_container.NUMBER_OF_ALERTS_ON_SCREEN):
        assert screen.entries_container.factory.entries[i].entry.index_label["text"] == str(i + 1)


def test_scrolling_down_successfully(screen: HistoryScreen):
    for i in range(screen.entries_container.NUMBER_OF_ALERTS_ON_SCREEN + 1):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH,
                                                 time.time() + i * 1000000)
    screen.show()
    screen.on_refresh_button_click()
    screen.on_scroll_down()

    assert screen.entries_container.index == 1

    for i in range(screen.entries_container.NUMBER_OF_ALERTS_ON_SCREEN):
        assert screen.entries_container.factory.entries[i].entry.index_label["text"] == str(i + 2)


def test_scrolling_up_successfully(screen: HistoryScreen):
    for i in range(screen.entries_container.NUMBER_OF_ALERTS_ON_SCREEN + 2):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH,
                                                 time.time() + i * 1000000)

    screen.show()
    screen.on_refresh_button_click()
    screen.on_scroll_down()
    screen.on_scroll_down()

    screen.on_scroll_up()
    assert screen.entries_container.index == 1

    for i in range(screen.entries_container.NUMBER_OF_ALERTS_ON_SCREEN):
        assert screen.entries_container.factory.entries[i].entry.index_label["text"] == str(i + 2)


def test_refresh_button(screen: HistoryScreen):
    screen.show()
    assert screen.right_side_menu_container.refresh_button["state"] == "disabled"
    screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    assert screen.right_side_menu_container.refresh_button["state"] == "active"

    screen.right_side_menu_container.on_refresh_button_click()
    assert screen.right_side_menu_container.refresh_button["state"] == "disabled"

def test_back_button_click(screen: HistoryScreen):
    screen.show()
    screen.alerts_history_screen = MagicMock()
    screen.bottom_bar.on_click()
    assert screen.alerts_history_screen.place_forget.called

def test_unseen_alerts_are_red(screen: HistoryScreen):
    screen.show()
    screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())
    screen.on_refresh_button_click()
    assert screen.entries_container.factory.entries[0].entry.frame["bg"] == \
        Theme.active().UNSEEN_ALERT

def test_seen_alerts_are_not_red(screen: HistoryScreen):
    screen.show()
    screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())
    screen.events.alert_queue.clear_alerts()
    screen.on_refresh_button_click()
    assert screen.entries_container.factory.entries[0].entry.frame["bg"] == \
        Theme.active().SURFACE

def test_unseen_alerts_dont_stay_that_way(screen: HistoryScreen):
    screen.show()
    screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())
    screen.on_refresh_button_click()

    screen.events.alert_queue.clear_alerts()
    screen.on_refresh_button_click()
    assert screen.entries_container.factory.entries[0].entry.frame["bg"] == \
        Theme.active().SURFACE

def test_same_alerts_trigger_a_refresh_button_after_some_time(screen: HistoryScreen):
    screen.show()

    time_to_wait = screen.events.alert_queue.history.time_difference_between_same_alerts

    with freezegun.freeze_time("12th February 2000"):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    screen.on_refresh_button_click()

    with freezegun.freeze_time("12th February 2000", tz_offset=time_to_wait + 1):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    assert screen.right_side_menu_container.refresh_button["state"] == "active"

    screen.on_refresh_button_click()

    assert screen.entries_container.factory.entries[0].entry.frame["bg"] == \
        Theme.active().UNSEEN_ALERT


def test_same_alerts_are_ignored(screen: HistoryScreen):
    screen.show()

    time_to_wait = screen.events.alert_queue.history.time_difference_between_same_alerts

    with freezegun.freeze_time("12th February 2000"):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    screen.right_side_menu_container.on_refresh_button_click()
    assert screen.right_side_menu_container.refresh_button["state"] == "disabled"

    with freezegun.freeze_time("12th February 2000", tz_offset=time_to_wait - 1):
        screen.events.alert_queue.enqueue_alert(AlertCodes.NO_BREATH, time.time())

    assert screen.right_side_menu_container.refresh_button["state"] == "disabled"

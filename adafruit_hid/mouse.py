# SPDX-FileCopyrightText: 2017 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_hid.mouse.Mouse`
====================================================

* Author(s): Dan Halbert
"""
from .keycode import MouseButton

from . import find_device

try:
    from typing import Optional, Sequence
    import usb_hid
except ImportError:
    pass


class Mouse:
    """Send USB HID mouse reports."""

    LEFT_BUTTON = MouseButton.LEFT
    """Left mouse button."""
    RIGHT_BUTTON = MouseButton.RIGHT
    """Right mouse button."""
    MIDDLE_BUTTON = MouseButton.MIDDLE
    """Middle mouse button."""
    SIDE_BUTTON = MouseButton.SIDE
    """Side button."""
    EXTRA_BUTTON = MouseButton.EXTRA
    """Extra button."""
    FORWARD_BUTTON = MouseButton.FORWARD
    """Forward mouse button."""
    BACK_BUTTON = MouseButton.BACK
    """Back mouse button."""
    TASK_BUTTON = MouseButton.TASK
    """Task button."""

    def __init__(self, devices: Sequence[usb_hid.Device], timeout: Optional[int] = None) -> None:
        """Create a Mouse object that will send USB mouse HID reports.

        :param timeout: Time in seconds to wait for USB to become ready before timing out.
          Defaults to None to wait indefinitely.

        Devices can be a sequence of devices that includes a keyboard device or a keyboard device
        itself. A device is any object that implements ``send_report()``, ``usage_page`` and
        ``usage``.
        """
        self._mouse_device = find_device(
            devices, usage_page=0x1, usage=0x02, timeout=timeout
        )

        # Basic report format
        # report[0] buttons pressed (LEFT, RIGHT, MIDDLE, etc.)
        # report[1] x movement
        # report[2] y movement
        # report[3] wheel movement

        # Extended report format
        # report[0] buttons pressed (LEFT, RIGHT, MIDDLE, etc.)
        # report[1] 16-bit x movement (LSB)
        # report[2] 16-bit x movement (MSB)
        # report[3] 16-bit y movement (LSB)
        # report[4] 16-bit y movement (MSB)
        # report[5] wheel movement
        # report[6] AC pan movement

        self.report = bytearray(7)  # Reuse this bytearray to send mouse reports.

    def __str__(self):
        return str(self._mouse_device)

    def press(self, buttons: int, ex: bool = True) -> None:
        """Press the given mouse buttons.

        :param buttons: a bitwise-or'd combination of ``LEFT_BUTTON``,
            ``MIDDLE_BUTTON``, and ``RIGHT_BUTTON``.
        :param ex: If True (default), report buttons using the extended report format.
            Otherwise, use the basic report format.

        Examples::

            # Press the left button.
            m.press(Mouse.LEFT_BUTTON)

            # Press the left and right buttons simultaneously.
            m.press(Mouse.LEFT_BUTTON | Mouse.RIGHT_BUTTON)
        """
        self.report[0] |= buttons
        self._send_no_move(ex)

    def release(self, buttons: int, ex: bool = True) -> None:
        """Release the given mouse buttons.

        :param buttons: a bitwise-or'd combination of ``LEFT_BUTTON``,
            ``MIDDLE_BUTTON``, and ``RIGHT_BUTTON``.
        :param ex: If True (default), report buttons using the extended report format.
            Otherwise, use the basic report format.
        """
        self.report[0] &= ~buttons
        self._send_no_move(ex)

    def release_all(self, ex: bool = True) -> None:
        """Release all the mouse buttons.

        :param ex: If True (default), report buttons using the extended report format.
            Otherwise, use the basic report format.
        """
        self.report[0] = 0
        self._send_no_move(ex)

    def click(self, buttons: int, ex: bool = True) -> None:
        """Press and release the given mouse buttons.

        :param buttons: a bitwise-or'd combination of ``LEFT_BUTTON``,
            ``MIDDLE_BUTTON``, and ``RIGHT_BUTTON``.
        :param ex: If True (default), report buttons using the extended report format.
            Otherwise, use the basic report format.

        Examples::

            # Click the left button.
            m.click(Mouse.LEFT_BUTTON)

            # Double-click the left button.
            m.click(Mouse.LEFT_BUTTON)
            m.click(Mouse.LEFT_BUTTON)
        """
        self.press(buttons, ex)
        self.release(buttons, ex)

    def move(self, x: int = 0, y: int = 0, wheel: int = 0) -> None:
        """Move the mouse and turn the wheel as directed.

        :param x: Move the mouse along the x axis. Negative is to the left, positive
            is to the right.
        :param y: Move the mouse along the y axis. Negative is upwards on the display,
            positive is downwards.
        :param wheel: Rotate the wheel this amount. Negative is toward the user, positive
            is away from the user. The scrolling effect depends on the host.

        Examples::

            # Move 100 to the left. Do not move up and down. Do not roll the scroll wheel.
            m.move(-100, 0, 0)
            # Same, with keyword arguments.
            m.move(x=-100)

            # Move diagonally to the upper right.
            m.move(50, 20)
            # Same.
            m.move(x=50, y=-20)

            # Roll the mouse wheel away from the user.
            m.move(wheel=1)
        """
        # Send multiple reports if necessary to move or scroll requested amounts.
        while x != 0 or y != 0 or wheel != 0:
            partial_x = self._limit_i8(x)
            partial_y = self._limit_i8(y)
            partial_wheel = self._limit_i8(wheel)
            self.report[1] = partial_x & 0xFF
            self.report[2] = partial_y & 0xFF
            self.report[3] = partial_wheel & 0xFF
            self._mouse_device.send_report(self.report[:4])
            x -= partial_x
            y -= partial_y
            wheel -= partial_wheel

    def move_ex(self, x: int = 0, y: int = 0, wheel: int = 0, pan: int = 0) -> None:
        """Move the mouse and turn the wheel / pan as directed. Using the extended report format.

        :param x: Move the mouse along the x axis. Negative is to the left, positive
            is to the right.
        :param y: Move the mouse along the y axis. Negative is upwards on the display,
            positive is downwards.
        :param wheel: Rotate the wheel this amount. Negative is toward the user, positive
            is away from the user. The scrolling effect depends on the host.
        :param pan: Pan (horizontal scroll) this amount. Negative is to the left, positive
            is to the right. The panning effect depends on the host.

        Note::
            This method uses the extended report format with 16-bit x and y movement
            and pan support.
        """
        # Send multiple reports if necessary to move or scroll requested amounts.
        while x != 0 or y != 0 or wheel != 0 or pan != 0:
            partial_x = self._limit_i16(x)
            partial_y = self._limit_i16(y)
            partial_wheel = self._limit_i8(wheel)
            partial_pan = self._limit_i8(pan)
            self.report[1] = partial_x & 0xFF
            self.report[2] = (partial_x >> 8) & 0xFF
            self.report[3] = partial_y & 0xFF
            self.report[4] = (partial_y >> 8) & 0xFF
            self.report[5] = partial_wheel & 0xFF
            self.report[6] = partial_pan & 0xFF
            self._mouse_device.send_report(self.report, 0x82)
            x -= partial_x
            y -= partial_y
            wheel -= partial_wheel
            pan -= partial_pan

    def _send_no_move(self, ex: bool = True) -> None:
        """
        Send a button-only report.

        :param ex: If True (default), report buttons using the extended report format.
            Otherwise, use the basic report format.
        """
        self.report[1] = 0
        self.report[2] = 0
        self.report[3] = 0
        self.report[4] = 0
        self.report[5] = 0
        self.report[6] = 0
        if ex:
            self._mouse_device.send_report(self.report, 0x82)
        else:
            self._mouse_device.send_report(self.report[:4])

    @staticmethod
    def _limit_i8(dist: int) -> int:
        return min(127, max(-127, dist))

    @staticmethod
    def _limit_i16(dist: int) -> int:
        return min(32767, max(-32767, dist))

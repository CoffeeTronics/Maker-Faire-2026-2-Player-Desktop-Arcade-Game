"""
imu_sensor.py — ICM20948 9-Axis IMU
=====================================
Board: Ruler Baseboard

Wraps the adafruit_icm20x library for the ICM20948 IMU (accelerometer,
gyroscope, magnetometer) connected via I2C.

Hardware
--------
  board.I2C()       — shared I2C bus (SCL / SDA)
  I2C address: 0x68 (default for ICM20948)

Provides
--------
  - Raw acceleration (m/s²), gyroscope (rad/s), magnetometer (µT)
  - Tilt angles computed from the accelerometer
  - Gesture-style helper: detect tilt direction
  - Calibration for zero-point offset correction

Use this module for:
  - Motion-controlled games (tilt to move)
  - Inclinometers / levelling tools
  - Shake/tap detection
  - Orientation tracking
"""

import board
import adafruit_icm20x
import math
import time


class IMUSensor:
    """Read acceleration, gyroscope, and magnetometer from the ICM20948.

    Example
    -------
import pykit_explorer
from imu_sensor import IMUSensor
imu = IMUSensor()
while True:
    ax, ay, az = imu.acceleration
    gx, gy, gz = imu.gyro
    mx, my, mz = imu.magnetic
    print(f"Tilt angles of X axis and Y axis: {imu.tilt_angle_x:.2f}°, {imu.tilt_angle_y:.2f}°")
    print(f"Acceleration (m/s²): ax={ax:.2f}, ay={ay:.2f}, az={az:.2f}")
    print(f"Gyro (rad/s): gx={gx:.2f}, gy={gy:.2f}, gz={gz:.2f}")
    print(f"Magnetic (µT): mx={mx:.2f}, my={my:.2f}, mz={mz:.2f}\n\n")
    time.sleep(0.1)

    """

    # Tilt thresholds for gesture detection (m/s²)
    TILT_THRESHOLD = 3.0

    def __init__(self, i2c=None):
        if i2c is None:
            i2c = board.I2C()
        self._icm = adafruit_icm20x.ICM20948(i2c)
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._calibrated = False

    # -- Calibration ---------------------------------------------------------

    def calibrate(self, samples=30, delay=0.05):
        """Calibrate the IMU by averaging samples at rest.

        Takes multiple readings while the board is stationary on a level
        surface to determine the resting bias (offset) for X and Y axes.
        After calibration, use calibrated_acceleration for offset-corrected
        readings.

        Parameters
        ----------
        samples : int
            Number of samples to average (default 30)
        delay : float
            Delay between samples in seconds (default 0.05)

        Example
        -------
        imu = IMUSensor()
        imu.calibrate(samples=30)
        # Now use imu.calibrated_acceleration for games
        """
        total_x = 0.0
        total_y = 0.0
        for _ in range(samples):
            x, y, _ = self._icm.acceleration
            total_x += x
            total_y += y
            time.sleep(delay)
        self._offset_x = total_x / samples
        self._offset_y = total_y / samples
        self._calibrated = True

    @property
    def is_calibrated(self):
        """Return True if calibrate() has been called."""
        return self._calibrated

    @property
    def calibration_offset(self):
        """Return the calibration offsets as (offset_x, offset_y)."""
        return (self._offset_x, self._offset_y)

    @property
    def calibrated_acceleration(self):
        """Calibration-corrected acceleration as (x, y, z).

        X and Y axes have the resting offset subtracted.
        Z axis is returned unchanged.
        """
        ax, ay, az = self._icm.acceleration
        return (ax - self._offset_x, ay - self._offset_y, az)

    # -- Raw sensor data -----------------------------------------------------

    @property
    def acceleration(self) -> tuple:
        """Acceleration in m/s² as (x, y, z)."""
        return self._icm.acceleration

    @property
    def gyro(self) -> tuple:
        """Angular velocity in rad/s as (x, y, z)."""
        return self._icm.gyro

    @property
    def magnetic(self) -> tuple:
        """Magnetic field in µT as (x, y, z)."""
        return self._icm.magnetic

    # -- Computed orientation ------------------------------------------------

    @property
    def tilt_angle_x(self) -> float:
        """Board tilt about the X-axis in degrees (-90 to +90)."""
        ax, ay, az = self._icm.acceleration
        return math.degrees(math.atan2(ay, math.sqrt(ax ** 2 + az ** 2)))

    @property
    def tilt_angle_y(self) -> float:
        """Board tilt about the Y-axis in degrees (-90 to +90)."""
        ax, ay, az = self._icm.acceleration
        return math.degrees(math.atan2(ax, math.sqrt(ay ** 2 + az ** 2)))

    # -- Gesture / direction detection ----------------------------------------

    def tilt_direction(self) -> str:
        """Return a coarse tilt direction string: 'LEFT', 'RIGHT', 'UP', 'DOWN', or 'FLAT'."""
        ax, ay, _ = self._icm.acceleration
        if ax >  self.TILT_THRESHOLD:
            return "RIGHT"
        if ax < -self.TILT_THRESHOLD:
            return "LEFT"
        if ay >  self.TILT_THRESHOLD:
            return "DOWN"
        if ay < -self.TILT_THRESHOLD:
            return "UP"
        return "FLAT"

    def is_shaking(self, threshold: float = 15.0) -> bool:
        """Return True if total acceleration magnitude exceeds *threshold* m/s².

        Gravity (~9.8 m/s²) is always present, so threshold should be > 9.8.
        Default 15.0 catches moderate shaking.
        """
        ax, ay, az = self._icm.acceleration
        magnitude = math.sqrt(ax ** 2 + ay ** 2 + az ** 2)
        return magnitude > threshold

    # -- Display-friendly delta for sprite control ---------------------------

    def sprite_delta(self, scale: float = 1.0) -> tuple:
        """Return (dx, dy) pixel deltas suitable for moving a display sprite.

        Maps X/Y accelerometer axes to screen coordinates:
          board tilted right → dx positive (sprite moves right)
          board tilted forward → dy negative (sprite moves up)

        Parameters
        ----------
        scale : multiplier applied to the integer-cast acceleration values

        Returns
        -------
        (dx, dy) tuple of ints
        """
        ax, ay, _ = self._icm.acceleration
        return (int(ax * scale), -int(ay * scale))

    # -- Logging -------------------------------------------------------------

    def print_all(self):
        """Print all sensor axes to the console."""
        ax, ay, az = self._icm.acceleration
        gx, gy, gz = self._icm.gyro
        mx, my, mz = self._icm.magnetic
        print(f"Accel  X:{ax:6.2f} Y:{ay:6.2f} Z:{az:6.2f} m/s²")
        print(f"Gyro   X:{gx:6.2f} Y:{gy:6.2f} Z:{gz:6.2f} rad/s")
        print(f"Mag    X:{mx:6.2f} Y:{my:6.2f} Z:{mz:6.2f} µT")

    def log_loop(self, interval: float = 0.2):
        """Continuously print sensor readings (blocking)."""
        while True:
            self.print_all()
            print()
            time.sleep(interval)

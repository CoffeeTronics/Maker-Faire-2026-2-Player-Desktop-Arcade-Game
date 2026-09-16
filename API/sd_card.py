"""
sd_card.py — SD Card File Storage
====================================
Board: Ruler Baseboard

Mounts the SPI-connected SD card and exposes helpers for reading, writing,
and appending to files on the card.  Once mounted, all standard Python file
I/O (open / read / write) works as normal under the "/sd" mount point.

Hardware (Ruler baseboard)
--------------------------
  board.SD_SCK  — SPI clock
  board.SD_MOSI — SPI MOSI
  board.SD_MISO — SPI MISO
  board.SD_CS   — chip select

Requires
--------
  adafruit_sdcard library

SD card format
--------------
  FAT32 formatted.  Max reliable file size limited by available memory
  for buffering, not the library.

Use this module for:
  - Data logging (sensor readings, events, errors)
  - Config file storage
  - WAV audio file source (see audio_out.py)
  - Large data sets that don't fit in on-chip flash
"""

import board
import busio
import digitalio
import storage
import adafruit_sdcard
import time


class SDCard:
    """Mount and access an SD card connected via SPI.

    Parameters
    ----------
    mount_point : filesystem path to mount at (default "/sd")

    Example
    -------

import pykit_explorer
from sd_card import SDCard
sd = SDCard()
sd.write_text("log.txt", "Hello SD!\\n")
print(sd.read_text("log.txt"))
sd.append_text("log.txt", "Another line\\n")

    """

    def __init__(self, mount_point: str = "/sd"):
        self._mount = mount_point
        spi = busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO)
        cs  = digitalio.DigitalInOut(board.SD_CS)
        sdcard = adafruit_sdcard.SDCard(spi, cs)
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, mount_point)

    def _path(self, filename: str) -> str:
        """Join the mount point and filename."""
        return f"{self._mount}/{filename}"

    # -- Text file helpers ---------------------------------------------------

    def write_text(self, filename: str, text: str):
        """Write (overwrite) a text file on the SD card.

        Parameters
        ----------
        filename : file name within the SD root, e.g. "data.txt"
        text     : string content to write
        """
        with open(self._path(filename), "w") as f:
            f.write(text)

    def append_text(self, filename: str, text: str):
        """Append a string to a text file (creates the file if it doesn't exist).

        Parameters
        ----------
        filename : file name within the SD root
        text     : string to append
        """
        with open(self._path(filename), "a") as f:
            f.write(text)

    def read_text(self, filename: str) -> str:
        """Read and return the entire contents of a text file as a string."""
        with open(self._path(filename), "r") as f:
            return f.read()

    def read_lines(self, filename: str) -> list:
        """Read a file and return a list of lines (strings)."""
        with open(self._path(filename), "r") as f:
            return f.readlines()

    # -- CSV / data logging --------------------------------------------------

    def log_csv(self, filename: str, fields: list):
        """Append a single CSV row to *filename*.

        Parameters
        ----------
        filename : CSV file name, e.g. "sensors.csv"
        fields   : list of values (will be converted to strings)

        Example
        -------
sd.log_csv("temp.csv", [time.monotonic(), 24.5, 65.2])
        """
        row = ",".join(str(v) for v in fields) + "\n"
        self.append_text(filename, row)

    def log_temperature(self, filename: str = "temperature.txt"):
        """Append the current CPU temperature to *filename* (blocking loop).

        Reads temperature every second until interrupted.
        Requires cpu_temp module for standalone use; here it imports directly.
        """
        import microcontroller
        import digitalio

        # Visual feedback via onboard LED if available
        try:
            led = digitalio.DigitalInOut(board.LED)
            led.direction = digitalio.Direction.OUTPUT
            has_led = True
        except Exception:
            has_led = False

        print(f"Logging temperature to {self._path(filename)}")
        while True:
            t = microcontroller.cpu.temperature
            print(f"Temperature = {t:.1f} °C")
            with open(self._path(filename), "a") as f:
                if has_led:
                    led.value = True
                f.write(f"{t:.1f}\n")
                if has_led:
                    led.value = False
            time.sleep(1)

    # -- Filesystem utilities ------------------------------------------------

    def listdir(self, subdir: str = "") -> list:
        """List files in *subdir* (default: SD card root).

        Returns a list of filename strings.
        """
        import os
        path = self._path(subdir) if subdir else self._mount
        return os.listdir(path)

    def exists(self, filename: str) -> bool:
        """Return True if *filename* exists on the SD card."""
        import os
        try:
            os.stat(self._path(filename))
            return True
        except OSError:
            return False

    def remove(self, filename: str):
        """Delete *filename* from the SD card."""
        import os
        os.remove(self._path(filename))

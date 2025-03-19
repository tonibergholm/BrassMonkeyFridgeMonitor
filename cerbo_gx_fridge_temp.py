"""
Victron Venus OS Driver for Brass Monkey Fridge Monitor

This script adapts the original Brass Monkey Fridge Monitor code to be compatible with Victron's Venus OS running on a Cerbo GX.  It reads temperature data from the fridge and publishes it to the Venus OS's D-Bus, making it visible in the Cerbo GX GUI.

Original code source: https://github.com/tonibergholm/BrassMonkeyFridgeMonitor

Key Changes:
-   Import necessary libraries for Venus OS (dbus, os, platform).
-   Check if running on a Raspberry Pi (for Venus OS compatibility).
-   Establish a D-Bus connection to the Venus OS system.
-   Create a custom service on the D-Bus to publish the temperature.
-   Modify the main loop to:
    -   Read temperature from the appropriate source (simulated or actual).
    -   Publish the temperature to the D-Bus service.
    -   Handle D-Bus connection errors and attempt to reconnect.
-   Include a dummy read_temp() function for non-Raspberry Pi systems.
-   Added logging for debugging and information.
-   Added a version variable.
-   Added a sleep to reduce CPU load.

**To Install and Run on Victron Cerbo GX:**

1.  **Prerequisites:**
    * A Victron Cerbo GX with Venus OS.
    * A compatible temperature sensor connected to the Cerbo GX (or Raspberry Pi if used as a gateway).  This script can be adapted for various sensors (DS18B20, etc.).  The original script appears to be designed for a serial connection, so significant modification may be needed depending on your sensor.  This example provides a starting point and assumes a simulated temperature if not running on a Raspberry Pi.
    * Enable "Services -> D-Bus TCP" on the Cerbo GX.

2.  **Installation:**
    * Copy this script to the Cerbo GX (e.g., using `scp`).  A common location is `/data/venus/`:
        ```bash
        scp brass_monkey_fridge_monitor.py root@<your_cerbo_ip>:/data/venus/
        ```
    * Make the script executable:
        ```bash
        ssh root@<your_cerbo_ip> "chmod +x /data/venus/brass_monkey_fridge_monitor.py"
        ```

3.  **Configuration (Important):**
     * **Check Sensor Connection:** This script, in its current form, *simulates* the temperature if not running on a Raspberry Pi.  You **MUST** adapt the `read_temp()` function to read from your actual temperature sensor.  This may involve:
        * Installing necessary drivers (if needed) on the Cerbo GX (this might not be persistent across reboots).
        * Modifying the `read_temp()` function to use the correct libraries and methods for your sensor (e.g., `os.listdir` and file reading for DS18B20, or a serial library like `pyserial` if the sensor is connected via serial).
     * **DBus Path:** The line `OBJ_PATH = '/Settings/Temperature/BrassMonkey'` defines where the temperature will appear in the Venus OS D-Bus.  You can change this if needed, but ensure it's a valid path.

4.  **Running the Script:**
    * **Automatic Start (Recommended):** For the script to start automatically on boot, you can add it to the Venus OS startup scripts.  This is the recommended approach for a reliable solution.
        * Create a service file (e.g., `/etc/init.d/brass_monkey_monitor`):

            ```bash
            ssh root@<your_cerbo_ip> "vi /etc/init.d/brass_monkey_monitor"
            ```

        * Add the following content (adjust the path if you saved the script elsewhere):

            ```bash
            #!/bin/sh /etc/rc.common
            # Start/stop script for the Brass Monkey fridge monitor

            start() {
                /data/venus/brass_monkey_fridge_monitor.py &
                exit 0
            }

            stop() {
                pkill -f /data/venus/brass_monkey_fridge_monitor.py
                exit 0
            }
            ```

        * Make the service file executable:

            ```bash
            ssh root@<your_cerbo_ip> "chmod +x /etc/init.d/brass_monkey_monitor"
            ```
        * Enable the service to start on boot:

             ```bash
             ssh root@<your_cerbo_ip> "update-rc.d brass_monkey_monitor defaults"
             ```
    * **Manual Start (for testing):**
        * Connect to the Cerbo GX via SSH:
            ```bash
            ssh root@<your_cerbo_ip>
            ```
        * Run the script:
            ```bash
            /data/venus/brass_monkey_fridge_monitor.py &
            ```
            (The `&` runs it in the background)

5.  **Verification:**
    * Check for the service in the Venus OS D-Bus:
        * On the Cerbo GX, use the `dbus-spy` command (if available) or check using another D-Bus client.  You should see a service with the name `com.victronenergy.temperature.brass_monkey` and the object path `/Settings/Temperature/BrassMonkey` (or whatever you set `OBJ_PATH` to).
    * Check the Cerbo GX GUI:  The temperature should appear in the temperature overview.  The exact location in the GUI depends on the Venus OS version and configuration, but it will typically be in the temperature monitoring section.
    * Check the log file:
        * The script logs to `/tmp/brass_monkey_monitor.log`.  Check this file for any errors or information:
            ```bash
            ssh root@<your_cerbo_ip> "tail -f /tmp/brass_monkey_monitor.log"
            ```

"""

import dbus
import dbus.mainloop.glib
import os
import platform
import time
import logging
from gi.repository import GLib  # Use GLib main loop

# Version of the script
VERSION = "1.1.0"

# D-Bus service and object paths
SERVICE_NAME = 'com.victronenergy.temperature.brass_monkey'
OBJ_PATH = '/Settings/Temperature/BrassMonkey'
DRIVER_NAME = 'Brass Monkey Fridge Monitor'
DEVICE_INSTANCE = 245 # Choose a unique device instance (245 is just an example)

# Logging setup
logging.basicConfig(
    filename='/tmp/brass_monkey_monitor.log',  # Log file location on Venus OS
    level=logging.INFO,  # Set the logging level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(DRIVER_NAME)
logger.info(f"{DRIVER_NAME} v{VERSION} started")

# Dummy function for reading temperature.  This MUST be replaced with your actual sensor reading code.
def read_temp():
    """
    Reads the temperature from the sensor.  This is a placeholder.
    Replace this with your actual sensor reading code.  This example
    simulates a temperature.

    If running on a Raspberry Pi, you would replace this with code
    that reads from your sensor (e.g., DS18B20).  If using a serial
    connection, you would use pyserial.

    :return: The temperature in Celsius (float).
    """
    if platform.machine() == 'armv7l':  # Example: Check for Raspberry Pi (adjust as needed)
        # ** REPLACE THIS SECTION WITH YOUR ACTUAL SENSOR READING CODE **
        # Example for DS18B20 on Raspberry Pi (requires proper setup):
        try:
            #  This part assumes you have the 1-wire interface enabled
            #  and the w1-therm module loaded.
            base_dir = '/sys/bus/w1/devices/'
            device_folder = next((folder for folder in os.listdir(base_dir) if folder.startswith('28-')), None) # Find device
            if device_folder:
                device_file = os.path.join(base_dir, device_folder, 'w1_slave')
                with open(device_file, 'r') as f:
                    lines = f.readlines()
                if lines[0].strip().endswith('YES'):
                    equals_pos = lines[1].find('t=')
                    if equals_pos != -1:
                        temp_string = lines[1][equals_pos + 2:]
                        temp_c = float(temp_string) / 1000.0
                        return temp_c
                    else:
                         logger.error("Could not find temperature in sensor output")
                         return 25.0 # Return a default
                else:
                    logger.error("CRC check failed for temperature reading")
                    return 25.0
            else:
                logger.error("No DS18B20 sensor found.  Check wiring and modules.")
                return 25.0
        except Exception as e:
            logger.error(f"Error reading DS18B20 sensor: {e}")
            return 25.0  # Return a default temperature on error
        ####################################################################
    else:
        #  ** REPLACE THIS SECTION WITH YOUR ACTUAL SENSOR READING CODE IF NOT RASPBERRY PI **
        # For testing on other platforms, simulate a temperature:
        logger.info("Running on non-Raspberry Pi.  Simulating temperature.")
        return 22.5  # Simulate a temperature
    ######################################################################

def main():
    """
    Main function to connect to D-Bus, publish temperature data, and handle errors.
    """
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)  # Use GLib main loop

    while True:
        try:
            # System bus for D-Bus communication on Venus OS
            bus = dbus.SystemBus()

            # Create and publish the D-Bus service
            service = bus.get_object('com.victronenergy.settings', '/')
            settings = dbus.Interface(service, 'com.victronenergy.Settings')

            # Check if the path exists, create if it does not.
            try:
                settings.GetValue(OBJ_PATH)
            except dbus.exceptions.DBusException:
                logger.info(f"Path {OBJ_PATH} does not exist. Creating...")
                settings.SetValue(OBJ_PATH, 25.0)  # Initial value

            # Create a D-Bus object to represent the temperature sensor.
            # Use a custom service name.
            dbus_service = dbus.service.BusName(SERVICE_NAME, bus=bus)
            class TemperatureService(dbus.service.Object):
                def __init__(self, bus, object_path):
                    super().__init__(bus, object_path)
                    self._temperature = 25.0  # Initial temperature

                @dbus.service.signal('com.victronenergy.BusItem')
                def PropertiesChanged(self, changes):
                    """
                    Signal emitted when properties change.  Needed for GUI updates.
                    """
                    pass

                @dbus.service.property('com.victronenergy.BusItem',
                                     variant_level=1,
                                     access=dbus.PROP_ACCESS_READWRITE)
                def Value(self):
                    """
                    The current temperature value.
                    """
                    return self._temperature

                @Value.setter
                def Value(self, value):
                    """
                    Sets the current temperature and emits a signal.
                    """
                    self._temperature = value
                    self.PropertiesChanged({'Value': value},
                                           {})  # Empty invalidated

                @dbus.service.property('com.victronenergy.BusItem',
                                     variant_level=1,
                                     access=dbus.PROP_ACCESS_READ)
                def Text(self):
                    """
                    The current temperature as text.
                    """
                    return f"{self._temperature:.1f} °C"

            # Create an instance of the TemperatureService
            temperature_service = TemperatureService(bus, OBJ_PATH)

            # Add a device instance.  This is crucial for the Victron system to recognize the sensor.
            device_instance_path = '/DeviceInstance'
            try:
                settings.GetValue(device_instance_path)
            except dbus.exceptions.DBusException:
                logger.info(f"Path {device_instance_path} does not exist. Creating...")
                settings.SetValue(device_instance_path, DEVICE_INSTANCE)

            # Add the DeviceInstance to D-Bus - Needed for correct identification in Venus OS
            setattr(temperature_service, 'DeviceInstance', DEVICE_INSTANCE)
            temperature_service.DeviceInstance = DEVICE_INSTANCE

             # Add the ProductId to D-Bus
            product_id_path = '/ProductId'
            try:
                settings.GetValue(product_id_path)
            except dbus.exceptions.DBusException:
                logger.info(f"Path {product_id_path} does not exist. Creating...")
                settings.SetValue(product_id_path, 0xB104)  # Example Product ID for Brass Monkey (0xB104).  Change as needed.

            setattr(temperature_service, 'ProductId', 0xB104)
            temperature_service.ProductId = 0xB104

            # Add the ProductName to D-Bus
            product_name_path = '/ProductName'
            try:
                settings.GetValue(product_name_path)
            except dbus.exceptions.DBusException:
                logger.info(f"Path {product_name_path} does not exist. Creating...")
                settings.SetValue(product_name_path, DRIVER_NAME)

            setattr(temperature_service, 'ProductName', DRIVER_NAME)
            temperature_service.ProductName = DRIVER_NAME

            # Add the custom name
            custom_name_path = '/CustomName'
            try:
                settings.GetValue(custom_name_path)
            except dbus.exceptions.DBusException:
                logger.info(f"Path {custom_name_path} does not exist. Creating...")
                settings.SetValue(custom_name_path, DRIVER_NAME) # set CustomName

            setattr(temperature_service, 'CustomName', DRIVER_NAME)
            temperature_service.CustomName = DRIVER_NAME

            # Get the main loop from GLib
            mainloop = GLib.MainLoop()

            # Main loop to continuously read and publish temperature
            while mainloop.is_running():
                try:
                    temp = read_temp()
                    temperature_service.Value = temp
                    logger.info(f"Temperature: {temp:.1f} °C")
                    time.sleep(5)  # Sleep for 5 seconds (adjust as needed)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    #  Consider adding a more sophisticated backoff strategy here.
                    time.sleep(60)  # Wait longer before retrying
        except dbus.DBusException as e:
            logger.error(f"D-Bus error: {e}.  Reconnecting in 60 seconds...")
            # Attempt to reconnect after a delay
            time.sleep(60)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}. Restarting in 60 seconds")
            time.sleep(60)

if __name__ == "__main__":
    main()

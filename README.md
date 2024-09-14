# IDQ ID801 TDC (Time to Digital Converter) or "Time Tagging Box"

This package is developed within the advisory of the Gallicchio Research Group, Harvey Mudd College.

It has a fast counter with a period ("native bin") of 81 ps. It outputs the value of this counter along with which channel saw the rising edge. This instruction assumes that you have the latest version of firmware updated on the physical IDQ ID801. Firmware update is contained with the official manual provided by the IDQ company itself (you should contact them directly if you own the device).


# Table of Contents

- [IDQ ID801 TDC (Time to Digital Converter) or "Time Tagging Box"](#idq-id801-tdc-time-to-digital-converter-or-time-tagging-box)
- [Table of Contents](#table-of-contents)
  - [Required setup to interface with IDQ devices](#required-setup-to-interface-with-idq-devices)
  - [Python module that utilizes C library shared-object](#python-module-that-utilizes-c-library-shared-object)
  - [Troubleshooting](#troubleshooting)


## Required setup to interface with IDQ devices

grant the permission to manage the IDQ USB device by running the following shell command:
```shell
sudo vim /etc/udev/rules.d/idq.rules
```
then, add the following lines to the file and press `:wq` to save and quit
```
# Make IDQ devices available to all users
SUBSYSTEMS=="usb", ATTRS{idVendor}=="16c0", MODE="0660"
```
install the package by running the following shell command:
```shell
pip install idq-id801
```

 
## Python module that utilizes C library shared-object

I implemented a [Python interface](./src/id801/id801.py) that connects to the C library shared-object. This module allows for simple integration with other Python scripts. The use cases are laid out in [this example notebook](./examples.ipynb).

A Python script to try is the [real-time plotter](./real-time_plotter.py) that you can call by the following shell command:
```shell
# This is an example for configurations below:
# exposure: 100ms
# coincidence window: 500TDC
# switch_termination: off
# save: do not save to CSV file
# A graph: plot channels "1" and "2"
# B graph: plot channel "1/2" (coincidence between channels "1" and "2")
python3 real-time_plotter.py -e 100 -w 500 -t 0 -A "1" "2" -B "1/2"  
```

To record the raw timestamps from the device [record timestamps](./record_timestamps.py) could be used:
```shell
python3 record_timestamps.py -e 100 -b 10_000  # to record all timestamps at 100ms exposure and 10_000 CSV writing batch size
```


## Troubleshooting

If no information is retrieved from the device but no error is shown, try running `python3 -m pytest -v` to test if the device is working correctly. Note that you have to enable to channels first unless no channel is turned on by default.

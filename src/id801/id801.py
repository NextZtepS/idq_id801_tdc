import ctypes as c
from enum import Enum
import numpy as np
import pandas as pd
import time
import sys

# Add the parent directory to the path to ensure that we can find libtdcbase.so
path_list = __file__.split('/')
package_dir = '/'.join(path_list[:-1])
sys.path.append(package_dir)


# Enum Types
# ----------

class DevType(Enum):
    DEVTYPE_1A = 0  # no signal conditioning
    DEVTYPE_1B = 1  # 8 channels signal conditioning
    DEVTYPE_1C = 2  # 3 channels signal conditioning
    DEVTYPE_NONE = 3  # No device / Invalid

class c_DevType(c.Structure):
    _fields_ = [("value", c.c_int)]


class FileFormat(Enum):
    FORMAT_ASCII = 0  # ASCII format
    FORMAT_BINARY = 1  # Uncompressed binary format (40B header, 10B/time tag)
    FORMAT_COMPRESSED = 2  # Compressed binary format (40B header, 5B/time tag)
    FORMAT_RAW = 3  # Uncompressed binary without header (for compatibility)
    FORMAT_NONE = 4  # No format / invalid

class c_FileFormat(c.Structure):
    _fields_ = [("value", c.c_int)]


class SignalCond(Enum):
    SCOND_TTL = 0  # For 5V TTL signals: Conditioning off
    SCOND_LVTTL = 1  # For LVTTL signals: Trigger at 2V rising edge, termination optional
    SCOND_NIM = 2  # For NIM signals: Trigger at -0.6V falling edge, termination fixed on
    SCOND_MISC = 3  # Other signal type: Conditioning on, everything optional
    SCOND_NONE = 4  # No signal / invalid

class c_SignalCond(c.Structure):
    _fields_ = [("value", c.c_int)]


# Note: TDC unit is the smallest time difference that the TDC can measure which is obtained from get_timebase() function
class SimType(Enum):
    SIM_FLAT = 0  # Time diffs and channel numbers uniformly distributed -> Requires 2 parameters: center, width for time diffs in TDC units
    SIM_NORMAL = 1  # Time diffs normally distributed, channels uniformly -> Requires 2 parameters: center, width for time diffs int TDC units
    SIM_NONE = 2  # No type / invalid

class c_SimType(c.Structure):
    _fields_ = [("value", c.c_int)]


# Main ID801 Class
# ----------------

class ID801:

    TDC_UNIT = 8.1e-11
    MAX_TIMESTAMP_BUFFER_SIZE = 1000000

    _clib: c.CDLL

    # Functions from the C Library
    # ----------------------------

    def __init__(self, lib_path=f"{package_dir}/libtdcbase.so"):
        """
        Initialize the TDC object.

        Args:
            lib_path (str, optional): A path to the C shared object complied for Linux. Defaults to f"{package_dir}/libtdcbase.so".
        """
        self._clib = c.CDLL(lib_path)
        init = self._clib.TDC_init
        init.argtypes = [c.c_int]
        init.restype = c.c_int
        err_code = init(-1)
        self.check_error_code(err_code)

    def __del__(self):
        """
        De-initialize the TDC object. (Prevent Segmentation Faults)
        """
        deInit = self._clib.TDC_deInit
        deInit.argtypes = []
        deInit.restype = c.c_int
        err_code = deInit()
        self.check_error_code(err_code)

    def get_version(self) -> str:
        """
        Get the version of the TDC library.

        Returns:
            str: The version of the TDC library.
        """
        get_version = self._clib.TDC_getVersion
        get_version.argtypes = []
        get_version.restype = c.c_double
        return str(get_version())
    
    def parse_error(self, err_code: int) -> str:
        """
        Parse the error code to get the error message.

        Args:
            err_code (int): The error code (range -1 to 14).

        Returns:
            str: The corresponding error message e.g. 0 -> "Success", -1 -> "Unspecified Error", etc.
        """
        perror = self._clib.TDC_perror
        perror.argtypes = [c.c_int]
        perror.restype = c.c_char_p
        return perror(err_code).decode()
    
    def check_error_code(self, err_code: int) -> None:
        """
        Check the error code and raise an exception if it is not 0.

        Args:
            err_code (int): The error code to check.
        """
        if err_code != 0:
            raise Exception(f"Error: {self.parse_error(err_code)}")

    def get_timebase(self) -> float:
        """
        Get the timebase of the TDC (aka. TDC unit).

        Returns:
            float: The timebase (TDC unit) of the TDC in second.
        """
        get_timebase = self._clib.TDC_getTimebase
        get_timebase.argtypes = []
        get_timebase.restype = c.c_double
        return float(get_timebase())
    
    def get_dev_type(self) -> DevType:
        """
        Get the device type of the TDC.

        Returns:
            DevType: The Device Type of the TDC following the `DevType` Enum.
        """
        get_dev_type = self._clib.TDC_getDevType
        get_dev_type.argtypes = []
        get_dev_type.restype = DevType
        return get_dev_type()

    def check_feature_hbt(self) -> bool:
        """
        Check if the connected device has the HBT feature.

        Returns:
            bool: True if the device has the HBT feature, False otherwise.
        """
        check_feature_hbt = self._clib.TDC_checkFeatureHbt
        check_feature_hbt.argtypes = []
        check_feature_hbt.restype = c.c_int32
        return bool(check_feature_hbt())

    def check_feature_lifetime(self) -> bool:
        """
        Check if the connected device has the Lifetime feature.

        Returns:
            bool: True if the device has the Lifetime feature, False otherwise.
        """
        check_feature_lifetime = self._clib.TDC_checkFeatureLifeTime
        check_feature_lifetime.argtypes = []
        check_feature_lifetime.restype = c.c_int32
        return bool(check_feature_lifetime())

    def configure_signal_conditioning(self, channel: int, conditioning: SignalCond, edge: int, term: int, threshold: float) -> None:
        """
        Configures a channel's signal conditioning. The function requires an 1B or 1C device.
        If it isn't present for the specified channel, OutOfRange error is returned.

        Primarily, a conditioning type is selected. Depending on the type, the three detailed settings may be relevant or ignored by the function (checkout `SignalCond` Enum).
        In particular, SCOND_TTL switches off the complete signal conditioning including the input divider. For full access to the details use SCOND_MISC as type.

        Args:
            channel (int): Number of the input channel to configure. For 1c devices, use 0=Ext0, 1=Ext1, 2=Sync
            conditioning (SignalCond): Type of signal conditioning. By default, the signal conditioning is off (SCOND_TTL).
            edge (int): Selects the signal edge that is processed as an event: rising (1) or falling (0)
            term (int): Switches the termination in the signal path on (1) or off (0)
            threshold (float): Voltage threshold that is used to identify events, in V. Allowed range is -2 ... 3V; internal resolution is 1.2mV
        """
        configure_signal_conditioning = self._clib.TDC_configureSignalConditioning
        configure_signal_conditioning.argtypes = [c.c_int32, c_SignalCond, c.c_int32, c.c_int32, c.c_double]
        configure_signal_conditioning.restype = c.c_int
        err_code = configure_signal_conditioning(channel, c_SignalCond(conditioning.value), edge, term, threshold)
        self.check_error_code(err_code)

    def get_signal_conditioning(self, channel: int) -> tuple[int, int, int, float]:
        """
        Reads back the signal conditioning parameters. These are the parameters that are actually in effect, they may differ from those set by `configure_signal_conditioning` in two cases: 
            1. Depending on the signal type the parameter may be preset and therefore ignored in the function call. 
            2. If the signal conditioning is completely off, the constant parameters of the direct signal path are returned.

        Args:
            channel (int): Number of the input channel to read out. For 1c devices, use 0=Ext0, 1=Ext1, 2=Sync

        Returns:
            on (int): 1 if the signal conditioning is on, 0 if it is off
            edge (int): 1 if the rising edge is selected, 0 if the falling edge is selected
            term (int): 1 if the termination is on, 0 if it is off
            threshold (float): Voltage threshold that is used to identify events, in V
        """
        get_signal_conditioning = self._clib.TDC_getSignalConditioning
        get_signal_conditioning.argtypes = [c.c_int32, c.POINTER(c.c_int32), c.POINTER(c.c_int32), c.POINTER(c.c_int32), c.POINTER(c.c_double)]
        get_signal_conditioning.restype = c.c_int
        on, edge, term, threshold = c.c_int32(), c.c_int32(), c.c_int32(), c.c_double()
        err_code = get_signal_conditioning(channel, c.byref(on), c.byref(edge), c.byref(term), c.byref(threshold))
        self.check_error_code(err_code)
        return on.value, edge.value, term.value, threshold.value
    
    def configure_sync_divider(self, divider: int, reconstruct: bool) -> None:
        """
        Configures the input divider of channel 0 if available. The divider does not work if the signal conditioning is switched off (see `configure_signal_conditioning`).

        Args:
            divider (int): Number of events skipped before one is passed. Only the following values are allowed: 1, 8, 16, 32, 64, 128 Ignored for 1C devices where the divider is always 1024.
            reconstruct (bool): Reconstruct the skipped events in software (True) or not (False).
        """
        configure_sync_divider = self._clib.TDC_configureSyncDivider
        configure_sync_divider.argtypes = [c.c_int32, c.c_int32]
        configure_sync_divider.restype = c.c_int
        err_code = configure_sync_divider(divider, int(reconstruct))
        self.check_error_code(err_code)

    def get_sync_divider(self) -> tuple[int, bool]:
        """
        Reads back the sync divider settings.

        Returns:
            divider (int): Number of events skipped before one is passed.
            reconstruct (bool): True if the skipped events are reconstructed in software, False otherwise.
        """
        get_sync_divider = self._clib.TDC_getSyncDivider
        get_sync_divider.argtypes = [c.POINTER(c.c_int32), c.POINTER(c.c_int32)]
        get_sync_divider.restype = c.c_int
        divider, reconstruct = c.c_int32(), c.c_int32()
        err_code = get_sync_divider(c.byref(divider), c.byref(reconstruct))
        self.check_error_code(err_code)
        return divider.value, bool(reconstruct.value)
    
    def configure_apd_cooling(self, fan_speed: int, temp: int) -> None:
        """
        Configures parameters for the cooling of the internal APDs if available. This function requires an 1C device, otherwise OutOfRange error is returned.

        Args:
            fan_speed (int): Fan speed, range 0 to 50000
            temp (int): Temperature control setpoint, range 0 to 65535. The temperature scale is nonlinear, some sample points: 0: -31° 16384: -25° 32768: -18° 65535: 0°
        """
        configure_apd_cooling = self._clib.TDC_configureApdCooling
        configure_apd_cooling.argtypes = [c.c_int32, c.c_int32]
        configure_apd_cooling.restype = c.c_int
        err_code = configure_apd_cooling(fan_speed, temp)
        self.check_error_code(err_code)

    def configure_internal_apds(self, apd: int, bias: float, thresh: float) -> None:
        """
        Configures parameters for the internal APDs if available. This function requires an 1C device, otherwise OutOfRange error is returned.

        Args:
            apd (int): index of addressed APD, 0 or 1
            bias (float): Bias value [V], range 0 to 250. Internal resolution is 61mV.
            thresh (float): Threshold value [V], range 0 to 2. Internal resolution is 0.5mV.
        """
        configure_internal_apds = self._clib.TDC_configureInternalApds
        configure_internal_apds.argtypes = [c.c_int32, c.c_double, c.c_double]
        configure_internal_apds.restype = c.c_int
        err_code = configure_internal_apds(apd, bias, thresh)
        self.check_error_code(err_code)

    def enable_channels(self, channels_enabled: list[bool]) -> None:
        """
        Selects the channels that contribute to the output stream.
        
        Args:
            channels_enabled (list[bool]): List of 8 boolean values to enable or disable the channels. True to enable, False to disable.
        """
        enable_channels = self._clib.TDC_enableChannels
        enable_channels.argtypes = [c.c_int32]
        enable_channels.restype = c.c_int
        channelMask = 0
        for i, enabled in enumerate(channels_enabled):
            if enabled:
                channelMask += (2 ** i)
        err_code = enable_channels(channelMask)
        self.check_error_code(err_code)

    def set_coincidence_window(self, coinc_win: int) -> None:
        """
        Sets the coincidence window for the coincidence counters. The coincidence window is the time interval in which two events are considered coincident.

        Args:
            coinc_win (int): The coincidence window in TDC units, range 0 to 65535.
        """
        set_coincidence_window = self._clib.TDC_setCoincidenceWindow
        set_coincidence_window.argtypes = [c.c_int32]
        set_coincidence_window.restype = c.c_int
        err_code = set_coincidence_window(coinc_win)
        self.check_error_code(err_code)

    def set_exposure_time(self, exp_time: int) -> None:
        """
        Sets the exposure time for the coincidence counters. The exposure time is the time interval in which events are counted.

        Args:
            exp_time (int): The exposure time in milliseconds, range 0 to 65535.
        """
        set_exposure_time = self._clib.TDC_setExposureTime
        set_exposure_time.argtypes = [c.c_int32]
        set_exposure_time.restype = c.c_int
        err_code = set_exposure_time(exp_time)
        self.check_error_code(err_code)

    def get_device_params(self) -> tuple[list[bool], int, int]:
        """
        Reads back the device parameters.

        Returns:
            channels_enabled (list[bool]): List of 8 boolean values to enable or disable the channels.
            coinc_win (int): The coincidence window in TDC units.
            exp_time (int): The exposure time in milliseconds.
        """
        get_device_params = self._clib.TDC_getDeviceParams
        get_device_params.argtypes = [c.POINTER(c.c_int32), c.POINTER(c.c_int32), c.POINTER(c.c_int32)]
        get_device_params.restype = c.c_int
        channelMask, coinc_win, exp_time = c.c_int32(), c.c_int32(), c.c_int32()
        err_code = get_device_params(c.byref(channelMask), c.byref(coinc_win), c.byref(exp_time))
        self.check_error_code(err_code)
        channels_enabled = [bool((channelMask.value >> i) & 1) for i in range(8)]
        return channels_enabled, coinc_win.value, exp_time.value

    def set_channel_delays(self, delays: list[int]) -> None:
        """
        Sets the channel delays. The channel delays are the time intervals by which the signals are delayed before they are processed by the TDC.

        Args:
            delays (list[int]): List of 8 integers representing the delays for each channel in TDC units.
        """
        set_channel_delays = self._clib.TDC_setChannelDelays
        set_channel_delays.argtypes = [c.POINTER(c.c_int32)]
        set_channel_delays.restype = c.c_int
        c_delays = (c.c_int32 * 8)(*delays)
        err_code = set_channel_delays(c_delays)
        self.check_error_code(err_code)

    def get_channel_delays(self) -> list[int]:
        """
        Reads back the channel delays.

        Returns:
            list[int]: List of 8 integers representing the delays for each channel in TDC units.
        """
        get_channel_delays = self._clib.TDC_getChannelDelays
        get_channel_delays.argtypes = [c.POINTER(c.c_int32)]
        get_channel_delays.restype = c.c_int
        delays = (c.c_int32 * 8)()
        err_code = get_channel_delays(delays)
        self.check_error_code(err_code)
        return list(delays)
    
    def switch_termination(self, on: bool) -> None:
        """
        Switches the 50Ohm termination of input lines on or off. The function requires an 1A type hardware, otherwise OutOfRange is returned.

        Args:
            on (bool): True to switch the termination on, False to switch it off.
        """
        switch_termination = self._clib.TDC_switchTermination
        switch_termination.argtypes = [c.c_int32]
        switch_termination.restype = c.c_int
        err_code = switch_termination(int(on))
        self.check_error_code(err_code)

    def configure_selftest(self, channels_enabled: list[bool], period: int, burst_size: int, burst_dist: int) -> None:
        """
        Configures the internal selftest. The selftest generates events on the selected channels with a given period, burst size and burst distance.

        Args:
            channels_enabled (list[bool]): List of 8 boolean values to enable or disable the channels.
            period (int): Period of all test singals in units of 20ns, range = 2 to 60
            burst_size (int): Number of periods in a burst, range = 1 to 65535
            burst_dist (int): Distance between bursts in units of 80ns, range = 0 to 10000
        """
        configure_selftest = self._clib.TDC_configureSelftest
        configure_selftest.argtypes = [c.c_int32, c.c_int32, c.c_int32, c.c_int32]
        configure_selftest.restype = c.c_int
        channelMask = 0
        for i, enabled in enumerate(channels_enabled):
            if enabled:
                channelMask += (2 ** i)
        err_code = configure_selftest(channelMask, period, burst_size, burst_dist)
        self.check_error_code(err_code)

    def get_data_lost(self) -> int:
        """
        Reads back the number of lost events since the last call of this function, mostly due to USB buffer overflow.

        Returns:
            int: The number of lost events.
        """
        get_data_lost = self._clib.TDC_getDataLost
        get_data_lost.argtypes = []
        get_data_lost.restype = c.c_int32
        data_lost = c.c_int32()
        err_code = get_data_lost(c.byref(data_lost))
        self.check_error_code(err_code)
        return int(data_lost.value)
    
    def set_timestamp_buffer_size(self, size: int) -> None:
        """
        Sets the size of the timestamp buffer. The buffer size determines how many timestamps can be stored in the buffer.

        Args:
            size (int): The size of the timestamp buffer, range 1 to 1000000.
        """
        set_timestamp_buffer_size = self._clib.TDC_setTimestampBufferSize
        set_timestamp_buffer_size.argtypes = [c.c_int32]
        set_timestamp_buffer_size.restype = c.c_int
        err_code = set_timestamp_buffer_size(size)
        self.check_error_code(err_code)

    def get_timestamp_buffer_size(self) -> int:
        """
        Gets the size of the timestamp buffer. The buffer size determines how many timestamps can be stored in the buffer.

        Returns:
            int: The size of the timestamp buffer.
        """
        get_timestamp_buffer_size = self._clib.TDC_getTimestampBufferSize
        get_timestamp_buffer_size.argtypes = [c.POINTER(c.c_int32)]
        get_timestamp_buffer_size.restype = c.c_int32
        buffer_size = c.c_int32()
        err_code = get_timestamp_buffer_size(c.byref(buffer_size))
        self.check_error_code(err_code)
        return int(buffer_size.value)
    
    def enable_tdc_input(self, enable: bool) -> None:
        """
        Enables input from the physical channels of the TDC device or the internal selftest.
        If disabled, the software ignores those "real" events, the device and its coincidence counters are not affected. By default the input is enabled.

        Args:
            enable (bool): True to enable the input, False to disable it.
        """
        enable_tdc_input = self._clib.TDC_enableTdcInput
        enable_tdc_input.argtypes = [c.c_int32]
        enable_tdc_input.restype = c.c_int
        err_code = enable_tdc_input(int(enable))
        self.check_error_code(err_code)

    def freeze_buffers(self, freeze: bool) -> None:
        """
        Freezes the input buffers. If frozen, the software ignores all incoming events, the device and its coincidence counters are not affected.

        Args:
            freeze (bool): True to freeze the buffers, False to unfreeze them.
        """
        freeze_buffers = self._clib.TDC_freezeBuffers
        freeze_buffers.argtypes = [c.c_int32]
        freeze_buffers.restype = c.c_int
        err_code = freeze_buffers(int(freeze))
        self.check_error_code(err_code)

    def get_coinc_counters(self) -> tuple[list[int], list[str], int]:
        """
        Retrieves the most recent values of the built-in coincidence counters. The coincidence counters are not accumulated, i.e. the counter values for the last exposure are returned.
        The array contains count rates for all 8 channels, and rates for two, three, and fourfold coincidences of events detected on different channels out of the first 4.

        Returns:
            data (list[int]): List of 19 integers representing the counter values. 
            labels (list[str]): The labels of the counter in the following order: 1, 2, 3, 4, 5, 6, 7, 8, 1/2, 1/3, 1/4, 2/3, 2/4, 3/4, 1/2/3, 1/2/4, 1/3/4, 2/3/4, 1/2/3/4
            updates (int): Number of data updates by the device since the last call.
        """
        labels = ["1", "2", "3", "4", "5", "6", "7", "8", "1/2", "1/3", "1/4", "2/3", "2/4", "3/4", "1/2/3", "1/2/4", "1/3/4", "2/3/4", "1/2/3/4"]
        get_coinc_counters = self._clib.TDC_getCoincCounters
        get_coinc_counters.argtypes = [c.POINTER(c.c_int32), c.POINTER(c.c_int32)]
        get_coinc_counters.restype = c.c_int
        c_data = (c.c_int32 * 19)()
        updates = c.c_int32()
        err_code = get_coinc_counters(c_data, c.byref(updates))
        self.check_error_code(err_code)
        return list(c_data), labels, int(updates.value)
    
    def get_last_timestamps(self, buffer_size: int = MAX_TIMESTAMP_BUFFER_SIZE, reset = True) -> tuple[np.ndarray, np.ndarray, int]:
        """
        Retrieves the most recent timestamps from the buffer. The buffer is filled with the most recent timestamps, the oldest timestamps are overwritten.

        Args:
            buffer_size (int, optional): The size of the timestamp buffer. Defaults to 1000000.
            reset (bool, optional): Reset the buffer after retrieving. Defaults to True.

        Returns:
            timestamps (np.ndarray): NumPy array of integers representing the timestamps.
            channels (np.ndarray): NumPy array of integers representing the channels corresponding to the timestamps at the same index.
            valid (int): Number of valid timestamps in the buffer.
        """
        get_last_timestamps = self._clib.TDC_getLastTimestamps
        get_last_timestamps.argtypes = [c.c_int32, c.POINTER(c.c_int64), c.POINTER(c.c_int8), c.POINTER(c.c_int32)]
        get_last_timestamps.restype = c.c_int

        timestamps = np.ndarray(buffer_size, dtype=np.int64)
        channels = np.ndarray(buffer_size, dtype=np.int8)
        valid = c.c_int32()
        err_code = get_last_timestamps(int(reset), timestamps.ctypes.data_as(c.POINTER(c.c_int64)), channels.ctypes.data_as(c.POINTER(c.c_int8)), c.byref(valid))
        self.check_error_code(err_code)
        return timestamps, channels, int(valid.value)

    def write_timestamps(self, filename: str, format: FileFormat) -> None:
        """
        Writes the timestamps to a file. The file format can be ASCII, binary, compressed binary, or raw binary.
        This function must be called again with empty filename or FORMAT_NONE to close the file.

        Args:
            filename (str): The name of the file to write the timestamps to.
            format (FileFormat): The format of the file to write the timestamps to.
        """
        write_timestamps = self._clib.TDC_writeTimestamps
        write_timestamps.argtypes = [c.c_char_p, c_FileFormat]
        write_timestamps.restype = c.c_int
        err_code = write_timestamps(filename.encode(), c_FileFormat(format.value))
        self.check_error_code(err_code)

    def input_timestamps(self, timestamps: list[int], channels: list[int], count: int) -> None:
        """
        Inputs timestamps and corresponding channels into the TDC buffer. The timestamps must be in ascending order and will be processed just like "raw" data from a real device.

        Args:
            timestamps (list[int]): List of integers representing the timestamps.
            channels (list[int]): List of integers representing the channels corresponding to the timestamps.
            count (int): The number of valid elements in timestamps and channels lists to input.
        """
        input_timestamps = self._clib.TDC_inputTimestamps
        input_timestamps.argtypes = [c.POINTER(c.c_int64), c.POINTER(c.c_int8), c.c_int32]
        input_timestamps.restype = c.c_int
        c_timestamps = (c.c_int64 * count)(*timestamps)
        c_channels = (c.c_int8 * count)(*channels)
        err_code = input_timestamps(c_timestamps, c_channels, count)
        self.check_error_code(err_code)

    def read_timestamps(self, filename: str, format: FileFormat) -> None:
        """
        Reads timestamps from a file. The file format must be binary (FORMAT_BINARY).

        Args:
            filename (str): The name of the .bin file to read the timestamps from.
            format (FileFormat): The format of the file to read the timestamps from. Must be FORMAT_BINARY.
        """
        read_timestamps = self._clib.TDC_readTimestamps
        read_timestamps.argtypes = [c.c_char_p, c_FileFormat]
        read_timestamps.restype = c.c_int
        err_code = read_timestamps(filename.encode(), c_FileFormat(format.value))
        self.check_error_code(err_code)

    def generate_timestamps(self, sim_type: SimType, params: list[float], count: int) -> None:
        """
        Generates timestamps with a given simulation type and parameters. The timestamps are stored in the buffer.

        Args:
            sim_type (SimType): The simulation type to use.
            params (list[float]): List of 2 floats representing the parameters for the simulation type.
            count (int): The number of timestamps to generate.
        """
        generate_timestamps = self._clib.TDC_generateTimestamps
        generate_timestamps.argtypes = [c_SimType, c.POINTER(c.c_double), c.c_int32]
        generate_timestamps.restype = c.c_int
        c_params = (c.c_double * 2)(*params)
        err_code = generate_timestamps(c_SimType(sim_type.value), c_params, count)
        self.check_error_code(err_code)
    

    # Functions For Recording Real Timestamps
    # ---------------------------------------

    def record_real_timestamps_to_file(self, filename: str, format: FileFormat, exp_time: int, buffer_size: int = MAX_TIMESTAMP_BUFFER_SIZE) -> None:
        """
        Record real timestamps to a file for a given exp_time.

        Args:
            filename (str): The name of the file to write the timestamps to.
            format (FileFormat): The format of the file to write the timestamps to.
            exp_time (int): The exp_time in milliseconds to record the timestamps.
            buffer_size (int, optional): The size of the timestamp buffer. Defaults to 1000000.

        Warning:
            The recorded channel list ranges from 0 to 7 while the channel numbers in the file range from 1 to 8.
            Speed! The timestamps withing the same file are continuos while the timestamps between may be not at high frequency.
        """
        self.set_exposure_time(exp_time)
        self.enable_channels([True] * 8)
        self.enable_tdc_input(False)
        self.freeze_buffers(True)
        self.set_timestamp_buffer_size(buffer_size)
        self.write_timestamps(filename, format)
        self.freeze_buffers(False)
        self.enable_tdc_input(True)
        time.sleep(exp_time / 1000)
        self.freeze_buffers(True)
        self.write_timestamps("", FileFormat.FORMAT_NONE)
        data_lost = self.get_data_lost()
        print(f"Data Lost: {data_lost}")

    def get_timestamps(self, exp_time: int, buffer_size: int = MAX_TIMESTAMP_BUFFER_SIZE) -> tuple[np.ndarray, np.ndarray]:
        """
        Get real timestamps for a given exp_time.

        Args:
            exp_time (int): The exp_time in seconds to get the timestamps.
            buffer_size (int, optional): The size of the timestamp buffer. Defaults to 1000000.

        Returns:
            timestamps (np.ndarray): NumPy array of integers representing the timestamps.
            channels (np.ndarray): NumPy array of integers representing the channels corresponding to the timestamps at the same index.

        Warning:
            - The recorded channel list ranges from 0 to 7 while the channel numbers in the file range from 1 to 8.
            - Ensure that the number of events within a given exp_time is less than the buffer size.
            - The timestamps between consecutive function calls are reliably continuos under 2 MEvent/s (maximum at 5 MEvent/s)
        """
        self.set_exposure_time(exp_time)
        self.enable_channels([True] * 8)
        self.enable_tdc_input(False)
        self.freeze_buffers(True)
        self.set_timestamp_buffer_size(buffer_size)
        self.freeze_buffers(False)
        self.enable_tdc_input(True)
        time.sleep(exp_time / 1000)
        self.freeze_buffers(True)
        timestamps, channels, valid = self.get_last_timestamps(buffer_size)
        print(f"Valid Timestamps: {valid}")
        timestamps = timestamps[:valid]
        channels = channels[:valid]
        return timestamps, channels
    
    def fill_array_with_timestamps(self, timestamps: np.ndarray, channels: np.ndarray, exp_time: int, reset = True) -> int:
        """
        Fill the NumPy arrays with timestamps and channels for a given exp_time.

        Args:
            timestamps (np.ndarray): NumPy array of integers representing the timestamps.
            channels (np.ndarray): NumPy array of integers representing the channels corresponding to the timestamps at the same index.
            exp_time (int): The exp_time in milliseconds to fill the arrays.
            reset (bool, optional): Reset the buffer after retrieving. Defaults to True.

        Returns:
            (Side Effect) Modify the timestamps and channels arrays.
            int: Number of valid timestamps in the buffer.

        Warning:
            - The recorded channel list ranges from 0 to 7 while the channel numbers in the file range from 1 to 8.
            - Ensure that the number of events within a given exp_time is less than the buffer size. 
            - The timestamps between consecutive function calls are reliably continuos under 2 MEvent/s (maximum at 5 MEvent/s)
        """
        assert(len(timestamps) == len(channels)), "Timestamps and Channels must have the same length."

        get_last_timestamps = self._clib.TDC_getLastTimestamps
        get_last_timestamps.argtypes = [c.c_int32, c.POINTER(c.c_int64), c.POINTER(c.c_int8), c.POINTER(c.c_int32)]
        get_last_timestamps.restype = c.c_int
        valid = c.c_int32()

        self.set_exposure_time(exp_time)
        self.enable_channels([True] * 8)
        self.enable_tdc_input(False)
        self.freeze_buffers(True)
        self.set_timestamp_buffer_size(len(timestamps))
        self.freeze_buffers(False)
        self.enable_tdc_input(True)
        time.sleep(exp_time / 1000)
        self.freeze_buffers(True)
        err_code = get_last_timestamps(int(reset), timestamps.ctypes.data_as(c.POINTER(c.c_int64)), channels.ctypes.data_as(c.POINTER(c.c_int8)), c.byref(valid))
        self.check_error_code(err_code)
        print(f"Valid Timestamps: {valid.value}")
        return valid.value

    def get_last_coinc_counters(self, exp_time: int, coinc_win: int) -> tuple[list[int], list[str], int]:
        """
        Get the most recent values of the built-in coincidence counters.

        Args:
            exp_time (int): The exposure time in milliseconds to get the coincidence counters.
            coinc_win (int): The coincidence window in TDC units.

        Returns:
            data (list[int]): List of 19 integers representing the counter values. 
            labels (list[str]): The labels of the counter in the following order: 1, 2, 3, 4, 5, 6, 7, 8, 1/2, 1/3, 1/4, 2/3, 2/4, 3/4, 1/2/3, 1/2/4, 1/3/4, 2/3/4, 1/2/3/4
            updates (int): Number of data updates by the device since the last call.
        """
        self.set_exposure_time(exp_time)
        self.set_coincidence_window(coinc_win)
        self.enable_tdc_input(False)
        self.freeze_buffers(True)
        self.set_timestamp_buffer_size(self.MAX_TIMESTAMP_BUFFER_SIZE)
        self.freeze_buffers(False)
        self.enable_tdc_input(True)
        time.sleep(exp_time / 1000)
        self.freeze_buffers(True)
        data, labels, updates = self.get_coinc_counters()
        return data, labels, updates
    
    def get_last_coinc_counters_n_timestamps(self, exp_time: int, coinc_win: int) -> tuple[list[int], list[str], int, np.ndarray, np.ndarray]:
        """
        Get the most recent values of the built-in coincidence counters and the timestamps.

        Args:
            exp_time (int): The exposure time in milliseconds to get the coincidence counters.
            coinc_win (int): The coincidence window in TDC units.

        Returns:
            data (list[int]): List of 19 integers representing the counter values. 
            labels (list[str]): The labels of the counter in the following order: 1, 2, 3, 4, 5, 6, 7, 8, 1/2, 1/3, 1/4, 2/3, 2/4, 3/4, 1/2/3, 1/2/4, 1/3/4, 2/3/4, 1/2/3/4
            updates (int): Number of data updates by the device since the last call.
            timestamps (np.ndarray): NumPy array of integers representing the timestamps.
            channels (np.ndarray): NumPy array of integers representing the channels corresponding to the timestamps at the same index.
        """
        self.set_exposure_time(exp_time)
        self.set_coincidence_window(coinc_win)
        self.enable_tdc_input(False)
        self.freeze_buffers(True)
        self.set_timestamp_buffer_size(self.MAX_TIMESTAMP_BUFFER_SIZE)
        self.freeze_buffers(False)
        self.enable_tdc_input(True)
        time.sleep(exp_time / 1000)
        self.freeze_buffers(True)
        data, labels, updates = self.get_coinc_counters()
        timestamps, channels, valid = self.get_last_timestamps()
        return data, labels, updates, timestamps[:valid], channels[:valid]
    

    # Functions for Generating Testing Data
    # -------------------------------------

    @staticmethod
    def generate_timestamps_on_channel(channel: int | str, freq: float, num_timestamps: int, start_timestamp: int = 0, noise_level: float = 0) -> pd.DataFrame:
        """
        Generate a DataFrame of timestamps for a given channel with optional noise.

        Args:
            channel (int | str): The channel number or custom name to generate timestamps for.
            freq (float): The frequency of the timestamps.
            num_timestamps (int): The number of timestamps to generate.
            start_timestamp (int): The starting timestamp.
            noise_level (float): The level of noise to introduce (as a fraction of 1/freq). Default is 0 (no noise).

        Returns:
            pd.DataFrame: A DataFrame containing the generated timestamps.
        """
        tau = 1 / freq
        base_times = np.arange(num_timestamps) * tau
        
        if noise_level > 0:
            noise = np.random.uniform(-noise_level * tau, noise_level * tau, num_timestamps)
            base_times += noise

        timestamps = ((base_times) / ID801.TDC_UNIT).astype(int) + start_timestamp
        
        return pd.DataFrame({
            "timestamp": timestamps,
            "channel": np.full(num_timestamps, channel)
        })
    
    @staticmethod
    def generate_timestamps_on_channels(channels: list[int | str], freqs: list[float], num_timestamps: int, start_timestamp: int = 0, noise_level: float = 0) -> pd.DataFrame:
        """
        Generate a DataFrame of timestamps for multiple channels with optional noise.

        Args:
            channels (list[int | str]): A list of channel numbers or custom names to generate timestamps for.
            freqs (list[float]): A list of frequencies for each channel.
            num_timestamps (int): The number of timestamps to generate.
            start_timestamp (int): The starting timestamp.
            noise_level (float): The level of noise to introduce (as a fraction of 1/freq). Default is 0 (no noise).

        Returns:
            pd.DataFrame: A DataFrame containing the generated timestamps.
        """
        assert len(channels) == len(freqs), "The number of channels and frequencies must be the same."

        dfs = []
        for channel, freq in zip(channels, freqs):
            dfs.append(ID801.generate_timestamps_on_channel(channel, freq, num_timestamps, start_timestamp, noise_level))
        
        return pd.concat(dfs).sort_values("timestamp", ignore_index=True)
    
    @staticmethod
    def calculate_average_frequency(df: pd.DataFrame, channel: int | str) -> float:
        """
        Calculate the average frequency of events for a given channel.

        Args:
            df (pd.DataFrame): A DataFrame containing the timestamps and channels of the events.
            channel (int | str): The channel number or custom name to calculate the frequency for.

        Returns:
            float: The average frequency of the events for the given channel.
        """
        assert channel in df["channel"].unique(), f"Channel {channel} not found in DataFrame."

        channel_df = df[df["channel"] == channel]
        time_diffs = np.diff(channel_df["timestamp"])
        avg_time_diff = float(np.mean(time_diffs))
        avg_frequency = 1 / (avg_time_diff * ID801.TDC_UNIT)
        
        return avg_frequency
    

    # Functions for Calculating Coincidences and Offset of Recorded Data
    # ------------------------------------------------------------------

    @staticmethod
    def get_coinc_count(df: pd.DataFrame, coinc_window: int, channel1: int | str, channel2: int | str) -> int:
        """
        Get the number of coincidences between two channels within a given time window.

        Args:
            df (pd.DataFrame): A DataFrame containing the timestamps and channels of the events.
            coinc_window (int): A time window in which to count coincidences.
            channel1 (int | str): A channel number or custom name.
            channel2 (int | str): A channel number or custom name.

        Returns:
            int: The number of coincidences between the two channels.
        """
        df = df.sort_values("timestamp", ignore_index=True)  # Ensure the DataFrame is sorted by timestamp
        coinc_count = 0
        i = 0
        
        while i < len(df):
            if df["channel"][i] == channel1 or df["channel"][i] == channel2:
                current_channel = df["channel"][i]
                other_channel = channel2 if current_channel == channel1 else channel1
                j = i + 1
                
                while j < len(df) and (df["timestamp"][j] - df["timestamp"][i] <= coinc_window):
                    if df["channel"][j] == other_channel:
                        coinc_count += 1
                        break  # Break to avoid double-counting
                    j += 1
            i += 1
        
        return coinc_count
    
    @staticmethod
    def get_coincs_count_from_interval(
        df: pd.DataFrame, 
        coinc_window: int, 
        channel1: int | str, 
        channel2: int | str,
        timestamp1: int,
        timestamp2: int
    ) -> int:
        """
        Get the number of coincidences between two channels within a given time window.

        Args:
            df (pd.DataFrame): A DataFrame containing the timestamps and channels of the events.
            coinc_window (int): A time window in which to count coincidences.
            channel1 (int | str): A channel number or custom name.
            channel2 (int| str): A channel number or custom name.
            timestamp1 (int): A timestamp to start counting coincidences.
            timestamp2 (int): A timestamp to stop counting coincidences.

        Returns:
            int: The number of coincidences between the two channels.
        """
        assert timestamp1 <= timestamp2, "timestamp2 must greater than or equal to timestamp1."
        assert timestamp1 >= df["timestamp"].min(), "timestamp1 is out of range."
        assert timestamp2 <= df["timestamp"].max(), "timestamp2 is out of range."

        df = df.sort_values("timestamp", ignore_index=True)  # Ensure the DataFrame is sorted by timestamp
        filtered_df = df[(df["timestamp"] >= timestamp1) & (df["timestamp"] <= timestamp2)].reset_index(drop=True)
        return ID801.get_coinc_count(filtered_df, coinc_window, channel1, channel2)

    @staticmethod
    def get_coincs_count_from_intervals(
        df: pd.DataFrame, 
        coinc_window: int, 
        channel1: int | str, 
        channel2: int | str,
        intervals: list[tuple[int, int]]
    ) -> int:
        """
        Get the number of coincidences between two channels within a given time window for multiple intervals.

        Args:
            df (pd.DataFrame): A DataFrame containing the timestamps and channels of the events.
            coinc_window (int): A time window in which to count coincidences.
            channel1 (int | str): A channel number or custom name.
            channel2 (int | str): A channel number or custom name.
            intervals (list[tuple[int, int]]): A list of tuples representing the start and end timestamps of the intervals.

        Returns:
            int: The number of coincidences between the two channels.
        """
        coinc_counts = []
        for interval in intervals:
            coinc_counts.append(ID801.get_coincs_count_from_interval(df, coinc_window, channel1, channel2, interval[0], interval[1]))
        return sum(coinc_counts)

    @staticmethod
    def get_nearest_offset_stats(df: pd.DataFrame, leading_channel: int | str, trailing_channel: int | str) -> tuple:
        """
        Get the mean and standard deviation of the time offset between the nearest events on two channels.

        Args:
            df (pd.DataFrame): A DataFrame containing the timestamps and channels of the events.
            leading_channel (int | str): A leading channel number or custom name.
            trailing_channel (int| str): A trailing channel number or custom name.

        Returns:
            mean_offset (float): The mean time offset between the nearest events on the two channels.
            std_offset (float): The standard deviation of the time offsets between the nearest events on the two channels.
            nearest_offset (list): A list of the time offsets between the nearest events on the two channels.
        """
        assert leading_channel in df["channel"].unique(), f"Channel {leading_channel} not found in DataFrame."
        assert trailing_channel in df["channel"].unique(), f"Channel {trailing_channel} not found in DataFrame."

        df = df.sort_values("timestamp", ignore_index=True)  # Ensure the DataFrame is sorted by timestamp
        nearest_offset = []
        for i in range(len(df)):
            if df["channel"][i] == leading_channel:
                j = i + 1
                while j < len(df):
                    if df["channel"][j] == trailing_channel:
                        nearest_offset.append(df["timestamp"][j] - df["timestamp"][i])
                        break
                    j += 1
        
        mean_offset = np.mean(nearest_offset)
        std_offset = np.std(nearest_offset)
        
        return mean_offset, std_offset, nearest_offset

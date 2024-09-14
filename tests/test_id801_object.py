from ..src.id801.id801 import ID801, DevType, SignalCond


idq_tdc = ID801()


def test_get_version():
    assert idq_tdc.get_version() == "7.2"


def test_get_timebase():
    assert round(idq_tdc.get_timebase(), 12) == 8.1e-11


def test_get_dev_type():
    assert idq_tdc.get_dev_type() == DevType.DEVTYPE_1A or idq_tdc.get_dev_type() == DevType.DEVTYPE_1B


def test_check_feature_hbt():
    assert idq_tdc.check_feature_hbt() == False


def test_check_feature_lifetime():
    assert idq_tdc.check_feature_lifetime() == False


def test_signal_conditioning():
    if (idq_tdc.get_dev_type() == DevType.DEVTYPE_1B):
        idq_tdc.configure_signal_conditioning(0, SignalCond.SCOND_MISC, 1, 1, 1.0)
        assert idq_tdc.get_signal_conditioning(0) == (1, 1, 1, 1.0)


def test_sync_divider():
    if (idq_tdc.get_dev_type() == DevType.DEVTYPE_1B):
        idq_tdc.configure_sync_divider(8, False)
        assert idq_tdc.get_sync_divider() == (8, False)


def test_enable_channels():
    idq_tdc.enable_channels([True] * 8)
    channels_enabled, coinc_win, exp_time = idq_tdc.get_device_params()
    assert all(channels_enabled)

    idq_tdc.enable_channels([False] * 8)
    channels_enabled, coinc_win, exp_time = idq_tdc.get_device_params()
    assert not any(channels_enabled)


def test_set_coincidence_window():
    idq_tdc.set_coincidence_window(10)
    channels_enabled, coinc_win, exp_time = idq_tdc.get_device_params()
    assert coinc_win == 10


def test_set_exposure_time():
    idq_tdc.set_exposure_time(10)
    channels_enabled, coinc_win, exp_time = idq_tdc.get_device_params()
    assert exp_time == 10


def test_channel_delays():
    idq_tdc.set_channel_delays([0 for _ in range(8)])
    assert idq_tdc.get_channel_delays() == [0 for _ in range(8)]

    idq_tdc.set_channel_delays([i for i in range(8)])
    assert idq_tdc.get_channel_delays() == [i for i in range(8)]

def test_switch_termination():
    if (idq_tdc.get_dev_type() == DevType.DEVTYPE_1A):
        idq_tdc.switch_termination(False)


def test_timestamp_buffer_size():
    idq_tdc.set_timestamp_buffer_size(100)
    assert idq_tdc.get_timestamp_buffer_size() == 100

    idq_tdc.set_timestamp_buffer_size(10_000)
    assert idq_tdc.get_timestamp_buffer_size() == 10_000

    idq_tdc.set_timestamp_buffer_size(1_000_000)
    assert idq_tdc.get_timestamp_buffer_size() == 1_000_000

def test_get_real_timestamps():
    timestamps, channels = idq_tdc.get_timestamps(100, 100)
    assert len(timestamps) == len(channels)

    timestamps, channels = idq_tdc.get_timestamps(100, 1_000_000)
    assert len(timestamps) == len(channels)

from ..src.id801.id801 import ID801
import numpy as np
import pandas as pd


def test_generate_timestamps():
    df = ID801.generate_timestamps_on_channel(1, 100, 100)
    assert len(df) == 100
    assert np.round(ID801.calculate_average_frequency(df, 1), 0) == 100

    df = ID801.generate_timestamps_on_channels([1, 2], [1_000, 2_000], 1_000)
    assert len(df) == 2_000
    assert np.round(ID801.calculate_average_frequency(df, 1), 0) == 1000
    assert np.round(ID801.calculate_average_frequency(df, 2), 0) == 2000


def test_get_coincs_count():
    data = {
        "timestamp": [100, 200, 400, 500, 600, 650],
        "channel": [1, 2, 1, 2, 1, 1]
    }
    df = pd.DataFrame(data)
    assert ID801.get_coinc_count(df, 100, 1, 2) == 3
    assert ID801.get_coincs_count_from_interval(df, 100, 1, 2, 100, 200) == 1
    assert ID801.get_coincs_count_from_interval(df, 100, 1, 2, 400, 650) == 2
    assert ID801.get_coincs_count_from_intervals(df, 100, 1, 2, [(100, 200), (400, 600)]) == 3


def test_get_nearest_offset_stats():
    data = {
        "timestamp": [100, 200, 600, 700, 1100, 1200],
        "channel": [1, 2, 1, 2, 1, 2]
    }
    df = pd.DataFrame(data)
    assert ID801.get_nearest_offset_stats(df, 1, 2) == (100, 0, [100, 100, 100])

    data = {
        "timestamp": [100, 250, 600, 650, 1100, 1200],
        "channel": [1, 2, 1, 2, 1, 2]
    }
    df = pd.DataFrame(data)
    assert ID801.get_nearest_offset_stats(df, 1, 2)[0] == 100
    assert ID801.get_nearest_offset_stats(df, 1, 2)[2] == [150, 50, 100]

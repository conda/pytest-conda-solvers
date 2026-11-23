import pytest
from constants import (
    EXPORTED_CHANNELS_WITH_FEATURES,
    SUBDIR,
    UNEXPORTED_CHANNELS_WITH_FEATURES,
)

from pytest_conda_solvers import data


def test_load_data_file():
    index = data.load_data_file("channel-1_non-noarch.json")
    # 1149 in conda upstream records, + scipy-0.11.0-np17py33_x0, from track-features tests
    assert len(index) == 1150
    random_entry_key = "numpy-1.7.0rc1-py33_p0.tar.bz2"
    random_entry_value = {
        "build": "py33_p0",
        "build_number": 0,
        "depends": [
            "mkl 10.3",
            "nose",
            "python 3.3*",
        ],
        "features": "mkl",
        "md5": "4976525dda67fb55578b8763dd2c04b1",
        "name": "numpy",
        "pub_date": "2013-01-29",
        "requires": [
            "mkl 10.3",
            "nose 1.2.1",
            "python 3.3",
        ],
        "version": "1.7.0rc1",
    }
    assert index[random_entry_key] == random_entry_value


@pytest.mark.parametrize("filename", ["repodata.json", "current_repodata.json"])
def test_get_channel_repodata(filename):
    repodata = data.get_channel_repodata("channel-1", "linux-64", filename)
    assert repodata["info"] == {
        "subdir": "linux-64",
        "arch": "x86_64",
        "platform": "linux",
    }
    assert "numpy-1.7.0rc1-py33_p0.tar.bz2" in repodata["packages"]


def test_get_channel_repodata_rejects_unsupported_filename():
    with pytest.raises(
        ValueError, match=r"Unsupported repodata filename 'repodata\.json\.zst'"
    ):
        data.get_channel_repodata("channel-1", "linux-64", "repodata.json.zst")


@pytest.mark.parametrize("channel", EXPORTED_CHANNELS_WITH_FEATURES)
def test_exported_channels_expose_features_as_track_features(channel):
    raw = data.get_channel_repodata(channel, SUBDIR, "repodata.json")
    exported = data.get_channel_repodata(
        channel, SUBDIR, "repodata.json", features_as_track_features=True
    )
    raw_packages, exported_packages = raw["packages"], exported["packages"]
    assert set(exported_packages) == set(raw_packages)
    with_features = {fn for fn, meta in raw_packages.items() if "features" in meta}
    assert with_features
    for fn in with_features:
        assert "features" not in exported_packages[fn]
        assert exported_packages[fn]["track_features"] == raw_packages[fn]["features"]
        assert {
            key: value
            for key, value in exported_packages[fn].items()
            if key != "track_features"
        } == {
            key: value for key, value in raw_packages[fn].items() if key != "features"
        }
    untouched = set(raw_packages) - with_features
    assert any("track_features" in raw_packages[fn] for fn in untouched)
    for fn in untouched:
        assert exported_packages[fn] == raw_packages[fn]


@pytest.mark.parametrize("channel", UNEXPORTED_CHANNELS_WITH_FEATURES)
def test_unexported_channels_keep_features(channel):
    raw = data.get_channel_repodata(channel, SUBDIR, "repodata.json")
    exported = data.get_channel_repodata(
        channel, SUBDIR, "repodata.json", features_as_track_features=True
    )
    assert any("features" in meta for meta in raw["packages"].values())
    assert exported["packages"] == raw["packages"]

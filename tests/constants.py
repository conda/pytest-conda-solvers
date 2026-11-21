from importlib.resources import files

from pytest_conda_solvers.data import EXPORTED_CHANNELS, get_channel_repodata
from pytest_conda_solvers.models import TestChannel

# the channel lists below describe the repodata of this subdir
SUBDIR = "linux-64"

_DATA = files("pytest_conda_solvers.data")


def _has_features(channel):
    repodata = get_channel_repodata(channel, SUBDIR, "repodata.json")
    return any("features" in meta for meta in repodata["packages"].values())


# the server builds the repodata of these channels from a pair of JSON files
CHANNELS_WITH_GENERATED_REPODATA = [
    channel.value
    for channel in TestChannel
    if _DATA.joinpath(f"{channel.value}_non-noarch.json").is_file()
]
# the server serves these channels as plain files from a directory
CHANNELS_WITH_STATIC_FILES = [
    channel.value for channel in TestChannel if _DATA.joinpath(channel.value).is_dir()
]
_CHANNELS_WITH_FEATURES = [
    channel for channel in CHANNELS_WITH_GENERATED_REPODATA if _has_features(channel)
]
# the track_features view of these channels differs from the plain one
EXPORTED_CHANNELS_WITH_FEATURES = [
    channel for channel in _CHANNELS_WITH_FEATURES if channel in EXPORTED_CHANNELS
]
# both views of these channels keep the features
UNEXPORTED_CHANNELS_WITH_FEATURES = [
    channel for channel in _CHANNELS_WITH_FEATURES if channel not in EXPORTED_CHANNELS
]

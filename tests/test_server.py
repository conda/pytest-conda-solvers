import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from constants import (
    CHANNELS_WITH_GENERATED_REPODATA,
    CHANNELS_WITH_STATIC_FILES,
    EXPORTED_CHANNELS_WITH_FEATURES,
    SUBDIR,
    UNEXPORTED_CHANNELS_WITH_FEATURES,
)

from pytest_conda_solvers.data import get_channel_repodata, load_raw_data_file
from pytest_conda_solvers.server import RepodataFilename, run_test_server

REPODATA_FILENAMES = [filename.value for filename in RepodataFilename]


def fetch(channel_server, channel, filename, features_as_track_features):
    channel_url = channel_server.get_channel_url(channel, features_as_track_features)
    with urllib.request.urlopen(f"{channel_url}/{SUBDIR}/{filename}") as response:
        return response.read()


def test_each_server_gets_its_own_port():
    servers = [run_test_server(), run_test_server()]
    addresses = [http.servers[0].sockets[0].getsockname()[:2] for http in servers]
    assert len({port for _, port in addresses}) == 2
    for host, port in addresses:
        url = f"http://{host}:{port}/channel-1/linux-64/repodata.json"
        with urllib.request.urlopen(url) as response:
            assert response.status == 200
    for http in servers:
        http.should_exit = True


@pytest.mark.parametrize("channel", EXPORTED_CHANNELS_WITH_FEATURES)
@pytest.mark.parametrize("filename", REPODATA_FILENAMES)
def test_track_features_route_serves_the_exported_index(
    channel_server, channel, filename
):
    raw = json.loads(fetch(channel_server, channel, filename, False))["packages"]
    exported = json.loads(fetch(channel_server, channel, filename, True))
    featured = {fn: meta["features"] for fn, meta in raw.items() if "features" in meta}
    assert featured
    for fn, features in featured.items():
        assert "features" not in exported["packages"][fn]
        assert exported["packages"][fn]["track_features"] == features
    assert exported == get_channel_repodata(
        channel, SUBDIR, filename, features_as_track_features=True
    )


@pytest.mark.parametrize("channel", UNEXPORTED_CHANNELS_WITH_FEATURES)
@pytest.mark.parametrize("filename", REPODATA_FILENAMES)
def test_track_features_route_keeps_features_outside_exported_channels(
    channel_server, channel, filename
):
    raw = json.loads(fetch(channel_server, channel, filename, False))
    exported = json.loads(fetch(channel_server, channel, filename, True))
    assert any("features" in meta for meta in raw["packages"].values())
    assert exported == raw


@pytest.mark.parametrize("channel", CHANNELS_WITH_STATIC_FILES)
@pytest.mark.parametrize("filename", REPODATA_FILENAMES)
def test_track_features_route_serves_static_channel_files(
    channel_server, channel, filename
):
    # this path also fits the repodata route, which has no such channel
    served = fetch(channel_server, channel, filename, True)
    assert served == load_raw_data_file(Path(f"{channel}/{SUBDIR}/{filename}"))


@pytest.mark.parametrize(
    "channel", CHANNELS_WITH_GENERATED_REPODATA + CHANNELS_WITH_STATIC_FILES
)
@pytest.mark.parametrize("features_as_track_features", [False, True])
def test_unserved_repodata_variants_are_not_found(
    channel_server, channel, features_as_track_features
):
    # solvers ask for the compressed file first and fall back on a 404
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        fetch(channel_server, channel, "repodata.json.zst", features_as_track_features)
    assert exc_info.value.code == 404

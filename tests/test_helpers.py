import json

import pytest
from conda.models.records import PackageRecord

from pytest_conda_solvers.helpers import SimpleEnvironment


def make_record(subdir):
    return PackageRecord(
        name="a",
        version="1.0",
        build="0",
        build_number=0,
        subdir=subdir,
        fn="a-1.0-0.tar.bz2",
    )


def test_write_repo_packages(tmp_path):
    env = SimpleEnvironment(tmp_path, None, ("linux-64", "noarch"))
    env._write_repo_packages("test", [make_record("linux-64")])

    channel_path = tmp_path / "channels" / "test"
    linux_64 = json.loads((channel_path / "linux-64" / "repodata.json").read_text())
    assert linux_64["info"] == {"subdir": "linux-64"}
    assert list(linux_64["packages"]) == ["a-1.0-0.tar.bz2"]
    # served subdirs without any packages still get an empty repodata.json
    noarch = json.loads((channel_path / "noarch" / "repodata.json").read_text())
    assert noarch == {"info": {"subdir": "noarch"}, "packages": {}}


def test_write_repo_packages_rejects_unserved_subdirs(tmp_path):
    env = SimpleEnvironment(tmp_path, None, ("linux-64",))
    with pytest.raises(
        ValueError, match=r"subdirs \['osx-64'\].*only serves \['linux-64'\]"
    ):
        env._write_repo_packages("test", [make_record("osx-64")])

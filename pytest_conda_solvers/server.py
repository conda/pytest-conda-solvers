"""
Local test server based on uvicorn

(Adapted from the http.server based one in the conda-index source tree,
itself taken from the conda source tree)
"""

import mimetypes
import queue
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Response, status
from fastapi_cache import Coder, FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from pytest import fixture

from .data import get_channel_repodata, load_raw_data_file


class RepodataFilename(str, Enum):
    repodata = "repodata.json"
    current_repodata = "current_repodata.json"


class ChannelServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def get_base_url(self, features_as_track_features=False):
        base_url = f"http://{self.host}:{self.port}"
        return f"{base_url}/track-features" if features_as_track_features else base_url

    def get_channel_url(self, channel, features_as_track_features=False):
        return f"{self.get_base_url(features_as_track_features)}/{channel}"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    yield


class NullCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        return value

    @classmethod
    def decode(cls, value: bytes) -> Any:
        return value


def run_test_server() -> uvicorn.Server:
    """
    Run a test server on a random port. Inspect returned server to get port,
    shutdown etc.
    """
    app = FastAPI(lifespan=lifespan)

    @app.get("/conda_format_repo/{full_path:path}")
    @app.get("/track-features/conda_format_repo/{full_path:path}")
    @cache(coder=NullCoder)
    async def conda_format_repo_contents(full_path: str):
        path = Path(f"conda_format_repo/{full_path}")
        try:
            data = load_raw_data_file(path)
        except FileNotFoundError:
            # Missing variants such as current_repodata.json.zst raise a 404,
            # to make conda fall back to the uncompressed filename instead of
            # treating the fetch as a server failure
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        mimetype = mimetypes.guess_type(path)[0]
        return Response(data, media_type=mimetype)

    def serve_repodata(channel_name: str, subdir: str, filename: str, **variant):
        # Validate the filename manually and return 404 for unsupported repodata
        # variants rather than relying on FastAPI's enum validation (which returns
        # 422). This server only serves repodata.json and current_repodata.json.
        # Compressed and sharded repodata variants, such as repodata.json.zst or
        # repodata_shards.msgpack.zst are not available, and a 404 tells libmamba
        # to fall back to repodata.json.
        try:
            validated = RepodataFilename(filename)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return get_channel_repodata(channel_name, subdir, validated.value, **variant)

    @app.get("/track-features/{channel_name}/{subdir}/{filename}")
    @cache()
    async def track_features_repodata(
        channel_name: str,
        subdir: str,
        filename: str,
    ):
        # The index as upstream exports it for every solver but classic, see
        # EXPORTED_CHANNELS in pytest_conda_solvers.data
        return serve_repodata(
            channel_name, subdir, filename, features_as_track_features=True
        )

    @app.get("/{channel_name}/{subdir}/{filename}")
    @cache()
    async def repodata(
        channel_name: str,
        subdir: str,
        filename: str,
    ):
        return serve_repodata(channel_name, subdir, filename)

    @app.get("/{full_path:path}")
    async def catch_all():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    def start_server(queue):
        class Server(uvicorn.Server):
            async def startup(self, sockets=None):
                await super().startup(sockets)
                queue.put(self)

        try:
            Server(uvicorn.Config(app, host="127.0.0.1", port=0)).run()
        except SystemExit:
            # uvicorn exits the thread when it cannot bind, and the caller's
            # queue.get() times out
            pass

    started = queue.Queue()

    threading.Thread(target=start_server, args=(started,), daemon=True).start()

    return started.get(timeout=1)


@fixture(scope="session")
def channel_server():
    """Open a local web server to test remote support files."""
    http = run_test_server()
    host, port = http.servers[0].sockets[0].getsockname()[:2]
    yield ChannelServer(host, port)
    # shutdown is checked at a polling interval, or the daemon thread will shut
    # down when the test suite exits.
    http.should_exit = True

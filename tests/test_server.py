import urllib.request

from pytest_conda_solvers.server import run_test_server


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

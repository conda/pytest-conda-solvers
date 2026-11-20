import pytest

PLUGIN_ARGS = (
    "-p",
    "no:conda-solvers",
    "-p",
    "pytest_conda_solvers.plugin",
)

CUSTOM_YAML = """
    tests:
      - name: local solver test
        id: LOCAL001
        provenance:
          node_id: tests/test_local.py::test_local
          commit: "0000000000000000000000000000000000000000"
          url: https://example.invalid/test
        kind: solve
        input:
          channels: channel-1
          specs_to_add: numpy
        output:
          final_state: []
"""


def test_bundled_suite_is_not_collected_in_other_projects(pytester):
    pytester.makeini("""
        [pytest]
        testpaths = configured
    """)
    test_dir = pytester.mkdir("configured")
    test_dir.joinpath("test_local.py").write_text("def test_local():\n    pass\n")

    result = pytester.runpytest(*PLUGIN_ARGS, "--collect-only", "-q")

    assert result.ret == pytest.ExitCode.OK
    output = result.stdout.str()
    assert "configured/test_local.py::test_local" in output
    assert "basic.yaml" not in output
    assert "1 test collected" in output


def test_bundled_suite_is_collected_with_pyargs(pytester):
    result = pytester.runpytest(
        *PLUGIN_ARGS, "--collect-only", "-q", "--pyargs", "pytest_conda_solvers"
    )

    assert result.ret == pytest.ExitCode.OK
    output = result.stdout.str()
    assert "basic.yaml::solve_1_1::test_solve[solve_1_1]" in output
    assert "test_solve_regressions.py::" in output


def test_custom_yaml_is_collected_next_to_python_tests(pytester):
    pytester.makepyfile("""
        def test_local():
            pass
    """)
    pytester.makefile(".yaml", custom=CUSTOM_YAML)

    result = pytester.runpytest(*PLUGIN_ARGS, "--collect-only", "-q")

    assert result.ret == pytest.ExitCode.OK
    output = result.stdout.str()
    assert "test_custom_yaml_is_collected_next_to_python_tests.py::test_local" in output
    assert "custom.yaml::local_solver_test::test_solve[local_solver_test]" in output
    assert "basic.yaml" not in output


def test_unrelated_yaml_is_ignored(pytester):
    pytester.makepyfile("""
        def test_local():
            pass
    """)
    pytester.makefile(
        ".yaml",
        environment="""
            name: example
            dependencies:
              - python
        """,
    )

    result = pytester.runpytest(*PLUGIN_ARGS, "--collect-only", "-q")

    assert result.ret == pytest.ExitCode.OK
    output = result.stdout.str()
    assert "test_unrelated_yaml_is_ignored.py::test_local" in output
    assert "environment.yaml" not in output


def test_invalid_solver_yaml_still_reports_a_collection_error(pytester):
    pytester.makefile(
        ".yaml",
        invalid="""
            tests:
              - name: incomplete solver test
        """,
    )

    result = pytester.runpytest(*PLUGIN_ARGS, "--collect-only", "-q")

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.stdout.fnmatch_lines(["*invalid.yaml*Object missing required field*"])

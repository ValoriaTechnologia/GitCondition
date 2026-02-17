"""Tests for main.py (Check path changes action)."""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure repo root is on path when running tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main as main_module


@pytest.fixture
def github_output_file(tmp_path):
    """Temporary file used as GITHUB_OUTPUT."""
    f = tmp_path / "github_output.txt"
    return str(f)


@pytest.fixture
def minimal_env(github_output_file):
    """Minimal env for successful run (git diff mocked)."""
    workspace = str(Path(github_output_file).parent)
    return {
        "INPUT_PATH": "mon-dossier",
        "INPUT_BEFORE": "abc123",
        "INPUT_AFTER": "def456",
        "GITHUB_OUTPUT": github_output_file,
        "GITHUB_WORKSPACE": workspace,
    }


def read_output(path: str) -> str:
    """Read GITHUB_OUTPUT file and return the value of 'changed'."""
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("changed="):
                return line.strip().split("=", 1)[1]
    return ""


def test_missing_input_path_exits_with_error(github_output_file, capfd):
    """INPUT_PATH empty or missing -> exit 1 and error on stderr."""
    env = {
        "INPUT_PATH": "",
        "GITHUB_OUTPUT": github_output_file,
    }
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(SystemExit) as exc_info:
            main_module.main()
    assert exc_info.value.code == 1
    out, err = capfd.readouterr()
    assert "Missing required input: path (env INPUT_PATH)" in err


def test_missing_github_output_exits_with_error(capfd):
    """GITHUB_OUTPUT not set -> exit 1 and error on stderr."""
    env = {
        "INPUT_PATH": "mon-dossier",
        "INPUT_BEFORE": "abc",
        "INPUT_AFTER": "def",
        "GITHUB_OUTPUT": "",  # empty so code treats as not set
    }
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(SystemExit) as exc_info:
            main_module.main()
    assert exc_info.value.code == 1
    out, err = capfd.readouterr()
    assert "GITHUB_OUTPUT is not set" in err


def test_invalid_before_empty_exits_with_error(github_output_file):
    """INPUT_BEFORE empty -> ValueError (before is required, no try/except in main for it)."""
    env = {
        "INPUT_PATH": "mon-dossier",
        "INPUT_BEFORE": "",
        "INPUT_AFTER": "def456",
        "GITHUB_OUTPUT": github_output_file,
        "GITHUB_WORKSPACE": str(Path(github_output_file).parent),
    }
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(ValueError) as exc_info:
            main_module.main()
    assert "before" in str(exc_info.value).lower() and "INPUT_BEFORE" in str(exc_info.value)


def test_invalid_before_all_zeros_outputs_true(github_output_file):
    """INPUT_BEFORE is 0*40 -> cat-file + git diff run; mock so git diff returns file under path -> changed=true."""
    env = {
        "INPUT_PATH": "mon-dossier",
        "INPUT_BEFORE": "0" * 40,
        "INPUT_AFTER": "def456",
        "GITHUB_OUTPUT": github_output_file,
        "GITHUB_WORKSPACE": str(Path(github_output_file).parent),
    }
    success = MagicMock(returncode=0, stdout="", stderr="")
    diff_with_change = MagicMock(returncode=0, stdout="mon-dossier/foo.txt\n", stderr="")
    with patch.dict(os.environ, env, clear=False):
        with patch("main.subprocess.run", side_effect=[success, success, diff_with_change]):
            main_module.main()
    assert read_output(github_output_file) == "true"


def test_after_empty_exits_with_error(github_output_file, minimal_env):
    """INPUT_AFTER empty -> ValueError (after is required, no try/except in main for it)."""
    minimal_env["INPUT_AFTER"] = ""
    minimal_env["INPUT_BEFORE"] = "abc123"
    with patch.dict(os.environ, minimal_env, clear=False):
        with pytest.raises(ValueError) as exc_info:
            main_module.main()
    assert "after" in str(exc_info.value).lower() and "INPUT_AFTER" in str(exc_info.value)


def test_file_under_path_outputs_true(github_output_file, minimal_env):
    """git diff returns file under path -> changed=true."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "mon-dossier/foo.txt\n"
    mock_result.stderr = ""
    with patch.dict(os.environ, minimal_env, clear=False):
        with patch("main.subprocess.run", return_value=mock_result):
            main_module.main()
    assert read_output(github_output_file) == "true"


def test_no_file_under_path_outputs_false(github_output_file, minimal_env):
    """git diff returns only files outside path -> changed=false."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "other/file.txt\n"
    mock_result.stderr = ""
    with patch.dict(os.environ, minimal_env, clear=False):
        with patch("main.subprocess.run", return_value=mock_result):
            main_module.main()
    assert read_output(github_output_file) == "false"


def test_exact_path_match_outputs_true(github_output_file, minimal_env):
    """git diff returns exactly the path as filename -> changed=true."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "mon-dossier\n"
    mock_result.stderr = ""
    with patch.dict(os.environ, minimal_env, clear=False):
        with patch("main.subprocess.run", return_value=mock_result):
            main_module.main()
    assert read_output(github_output_file) == "true"


def test_path_normalization_trailing_slash(github_output_file, minimal_env):
    """INPUT_PATH with trailing slash still matches path/foo -> changed=true."""
    minimal_env["INPUT_PATH"] = "mon-dossier/"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "mon-dossier/foo.txt\n"
    mock_result.stderr = ""
    with patch.dict(os.environ, minimal_env, clear=False):
        with patch("main.subprocess.run", return_value=mock_result):
            main_module.main()
    assert read_output(github_output_file) == "true"


def test_git_diff_failure_exits_with_error(github_output_file, minimal_env, capfd):
    """git diff returncode != 0 -> exit 1, no changed= in output (cat-file must succeed first)."""
    success = MagicMock(returncode=0, stdout="", stderr="")
    failure = MagicMock(returncode=1, stdout="", stderr="fatal: bad revision")
    with patch.dict(os.environ, minimal_env, clear=False):
        with patch("main.subprocess.run", side_effect=[success, success, failure]):
            with pytest.raises(SystemExit) as exc_info:
                main_module.main()
    assert exc_info.value.code == 1
    assert read_output(github_output_file) == ""
    out, err = capfd.readouterr()
    assert "fatal" in err or "bad revision" in err or "git diff failed" in err


def test_git_not_found_exits_with_error(github_output_file, minimal_env):
    """subprocess.run raises FileNotFoundError in _ensure_commit_exists -> exception propagates."""
    with patch.dict(os.environ, minimal_env, clear=False):
        with patch("main.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                main_module.main()

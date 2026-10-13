import json
import zipfile

import pytest

from src.models.profile import Profile
from src.services.browser.launcher import BrowserLauncher, ProfileBusyError, _LaunchResult
from src.services.profile.transfer import export_to_zip, import_from_zip


def _archive(path, name, files):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("profile.json", json.dumps({"name": name, "os_type": "windows"}))
        for arcname, data in files.items():
            z.writestr(arcname, data)
    return str(path)


def test_import_rejects_traversal_profile_name(tmp_path):
    zip_path = _archive(tmp_path / "p.zip", "..", {})
    ok, msg = import_from_zip(zip_path, str(tmp_path / "data"))
    assert not ok and "name" in msg


def test_import_rejects_zip_slip_entry(tmp_path):
    zip_path = _archive(tmp_path / "p.zip", "good", {"data/../../escaped.txt": "x"})
    ok, msg = import_from_zip(zip_path, str(tmp_path / "data"))
    assert not ok and "Unsafe path" in msg
    assert not (tmp_path / "escaped.txt").exists()


def test_import_extracts_normal_archive(tmp_path):
    zip_path = _archive(tmp_path / "p.zip", "good", {"data/fingerprint.json": "{}"})
    ok, profile = import_from_zip(zip_path, str(tmp_path / "data"))
    assert ok and profile.name == "good"
    assert (tmp_path / "data" / "good" / "fingerprint.json").read_text() == "{}"


@pytest.mark.parametrize("target_exists", [False, True])
def test_export_skips_browser_lock_symlinks_and_keeps_data(tmp_path, target_exists):
    data = tmp_path / "browser"
    data.mkdir()
    (data / "cookies.sqlite").write_bytes(b"persistent cookies")
    target = tmp_path / "external"
    if target_exists:
        target.write_text("outside the profile")
    try:
        (data / "lock").symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks is not permitted on this host")
    ok, archive = export_to_zip(Profile(name="docker-test"), str(data), str(tmp_path))
    assert ok, archive
    with zipfile.ZipFile(archive) as exported:
        assert exported.read("data/cookies.sqlite") == b"persistent cookies"
        assert "data/lock" not in exported.namelist()


def test_exclusive_blocks_second_holder():
    bl = BrowserLauncher()
    with bl.exclusive("p"), pytest.raises(ProfileBusyError), bl.exclusive("p"):
        pass
    with bl.exclusive("p"):  # released after the block
        pass


def test_launch_result_settles_once():
    r = _LaunchResult()
    r.settle(True)
    r.settle(False, "late failure")
    assert r.ok is True and r.error is None

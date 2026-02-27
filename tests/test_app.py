import copy
import pathlib
import importlib.util
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient


# Load the application module from src/app.py so tests work regardless of package layout
src_path = pathlib.Path(__file__).resolve().parent.parent / "src" / "app.py"
spec = importlib.util.spec_from_file_location("app_module", str(src_path))
app_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_mod)

app = app_mod.app
activities = app_mod.activities

# Keep an original deep copy of activities to restore between tests
original_activities = copy.deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities():
    # Restore activities to original state before each test
    activities.clear()
    activities.update(copy.deepcopy(original_activities))
    yield


client = TestClient(app)


def test_root_redirects():
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 307)
    assert resp.headers["location"] == "/static/index.html"


def test_get_activities():
    resp = client.get("/activities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "Chess Club" in data


def test_signup_success():
    email = "new@student.edu"
    activity = quote("Chess Club", safe="")
    resp = client.post(f"/activities/{activity}/signup", params={"email": email})
    assert resp.status_code == 200
    assert f"Signed up {email}" in resp.json().get("message", "")
    # Verify the participant was added
    resp2 = client.get("/activities")
    assert email in resp2.json()["Chess Club"]["participants"]


def test_signup_duplicate():
    email = "duplicate@student.edu"
    activity = quote("Chess Club", safe="")
    r1 = client.post(f"/activities/{activity}/signup", params={"email": email})
    assert r1.status_code == 200
    r2 = client.post(f"/activities/{activity}/signup", params={"email": email})
    assert r2.status_code == 400
    assert r2.json().get("detail") == "Student already signed up"


def test_signup_nonexistent():
    email = "x@y.com"
    activity = quote("Nope", safe="")
    r = client.post(f"/activities/{activity}/signup", params={"email": email})
    assert r.status_code == 404


def test_unregister_success():
    # Use an existing participant from the initial data
    email = "michael@mergington.edu"
    activity = quote("Chess Club", safe="")
    r = client.delete(f"/activities/{activity}/signup", params={"email": email})
    assert r.status_code == 200
    assert f"Unregistered {email}" in r.json().get("message", "")
    # Verify removal
    r2 = client.get("/activities")
    assert email not in r2.json()["Chess Club"]["participants"]


def test_unregister_not_signed_up():
    email = "not@there.edu"
    activity = quote("Chess Club", safe="")
    r = client.delete(f"/activities/{activity}/signup", params={"email": email})
    assert r.status_code == 400
    assert r.json().get("detail") == "Student is not signed up"


def test_unregister_nonexistent():
    email = "a@b.com"
    activity = quote("NoActivity", safe="")
    r = client.delete(f"/activities/{activity}/signup", params={"email": email})
    assert r.status_code == 404

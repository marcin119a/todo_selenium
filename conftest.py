import os
import re
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "http://localhost:5173"
EXISTING_EMAIL = "marcin119a@gmail.com"
EXISTING_PASSWORD = "string"


@pytest.fixture(scope="function")
def driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--window-position=100,100")

    service = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=service, options=options)
    drv.implicitly_wait(8)
    yield drv
    drv.quit()


@pytest.fixture(scope="function")
def driver_logged_in(driver):
    """Driver z już zalogowanym użytkownikiem przez localStorage."""
    driver.get(BASE_URL)
    # Wstrzyknij token przez API login, żeby nie klikać UI za każdym razem
    import requests
    resp = requests.post(
        "http://localhost:5173/auth/login",
        data={"username": EXISTING_EMAIL, "password": EXISTING_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = resp.json().get("access_token", "")
    driver.execute_script(
        f"localStorage.setItem('token', '{token}');"
        f"localStorage.setItem('userEmail', '{EXISTING_EMAIL}');"
    )
    driver.refresh()
    return driver


@pytest.fixture(autouse=True)
def screenshot_on_failure(request, driver):
    yield
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        safe_name = re.sub(r"[^\w\-]", "_", request.node.nodeid)
        folder = os.path.join("screenshots", safe_name)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "screenshot.png")
        driver.save_screenshot(path)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

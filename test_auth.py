"""
Testy E2E – Autentykacja (Selenium + pytest)
Pokrycie:
  - Rejestracja: poprawna (nowy email) + istniejący email
  - Logowanie: poprawne dane + błędne hasło
  - Wylogowanie
  - Persistencja sesji (refresh strony)
"""

import uuid
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5173"
EXISTING_EMAIL = "marcin119a@gmail.com"
EXISTING_PASSWORD = "string"


# ── helpers ───────────────────────────────────────────────────────────────────

def wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def open_app(driver):
    driver.get(BASE_URL)
    # Czyszczenie sesji – żeby zawsze startować z ekranem logowania
    driver.execute_script("localStorage.clear();")
    driver.refresh()
    wait(driver).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".auth-card")))


def switch_to_register(driver):
    btn = wait(driver).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'auth-tab') and text()='Rejestracja']"))
    )
    btn.click()


def fill_auth_form(driver, email, password):
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").clear()
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(email)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").clear()
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)


def submit_form(driver):
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()


def get_error(driver, timeout=6):
    return wait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-error"))
    ).text


def is_logged_in(driver, timeout=8):
    """Sprawdza czy dashboard jest widoczny (topbar z przyciskiem Wyloguj)."""
    try:
        wait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//button[text()='Wyloguj']"))
        )
        return True
    except Exception:
        return False


def is_on_auth_page(driver, timeout=8):
    try:
        wait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".auth-card"))
        )
        return True
    except Exception:
        return False


# ── REJESTRACJA ────────────────────────────────────────────────────────────────

class TestRegistration:

    def test_register_new_user_success(self, driver):
        """Rejestracja z unikalnym emailem → toast sukcesu i powrót do zakładki logowania."""
        open_app(driver)
        switch_to_register(driver)

        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        fill_auth_form(driver, unique_email, "haslo123")
        submit_form(driver)

        # Oczekujemy toastu "Konto utworzone"
        toast = wait(driver).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".toast"))
        )
        assert "Konto utworzone" in toast.text, f"Nieoczekiwany toast: {toast.text}"

        # Po rejestracji aktywna zakładka to Logowanie
        active_tab = wait(driver).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".auth-tab.active"))
        )
        assert active_tab.text == "Logowanie"

    def test_register_existing_email_shows_error(self, driver):
        """Rejestracja z już istniejącym emailem → komunikat błędu."""
        open_app(driver)
        switch_to_register(driver)

        fill_auth_form(driver, EXISTING_EMAIL, EXISTING_PASSWORD)
        submit_form(driver)

        error = get_error(driver)
        assert error, "Brak komunikatu błędu dla istniejącego emaila"
        # Wiadomość powinna zawierać informację o zajętym emailu lub konflikcie
        assert any(
            kw in error.lower()
            for kw in ["już istnieje", "exist", "registered", "zarejestrowany", "email"]
        ), f"Nieoczekiwana treść błędu: {error}"


# ── LOGOWANIE ─────────────────────────────────────────────────────────────────

class TestLogin:

    def test_login_valid_credentials(self, driver):
        """Logowanie poprawnymi danymi → dashboard widoczny, email użytkownika w topbarze."""
        open_app(driver)
        fill_auth_form(driver, EXISTING_EMAIL, EXISTING_PASSWORD)
        submit_form(driver)

        assert is_logged_in(driver), "Dashboard nie pojawił się po poprawnym logowaniu"

        topbar_user = driver.find_element(By.CSS_SELECTOR, ".topbar-user").text
        assert EXISTING_EMAIL in topbar_user, (
            f"Email użytkownika '{EXISTING_EMAIL}' nie widoczny w topbarze (jest: '{topbar_user}')"
        )

    def test_login_wrong_password_shows_error(self, driver):
        """Logowanie błędnym hasłem → komunikat błędu, brak dashboardu."""
        open_app(driver)
        fill_auth_form(driver, EXISTING_EMAIL, "bledne_haslo_xyz")
        submit_form(driver)

        error = get_error(driver)
        assert error, "Brak komunikatu błędu dla błędnego hasła"

        assert not is_logged_in(driver, timeout=3), "Dashboard nie powinien być widoczny po błędnym haśle"

    def test_login_empty_fields_blocked(self, driver):
        """Formularz z pustymi polami nie może zostać wysłany (required HTML5)."""
        open_app(driver)
        # Nie wypełniamy pól – przycisk submit jest wymagany (required), sprawdzamy walidację
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()

        # Strona nie może przejść do dashboardu
        assert not is_logged_in(driver, timeout=3), "Nie powinno dać się zalogować z pustymi polami"
        # Ekran auth nadal widoczny
        assert is_on_auth_page(driver)


# ── WYLOGOWANIE ───────────────────────────────────────────────────────────────

class TestLogout:

    def test_logout_redirects_to_auth(self, driver_logged_in):
        """Kliknięcie 'Wyloguj' → powrót na ekran logowania."""
        driver = driver_logged_in
        assert is_logged_in(driver), "Przed testem użytkownik powinien być zalogowany"

        logout_btn = driver.find_element(By.XPATH, "//button[text()='Wyloguj']")
        logout_btn.click()

        assert is_on_auth_page(driver), "Po wylogowaniu powinien pojawić się ekran logowania"

    def test_logout_clears_token(self, driver_logged_in):
        """Po wylogowaniu token i email usunięte z localStorage."""
        driver = driver_logged_in

        driver.find_element(By.XPATH, "//button[text()='Wyloguj']").click()
        wait(driver).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".auth-card")))

        token = driver.execute_script("return localStorage.getItem('token');")
        email = driver.execute_script("return localStorage.getItem('userEmail');")

        assert token is None, f"Token powinien być usunięty, jest: {token}"
        assert email is None, f"Email powinien być usunięty, jest: {email}"


# ── PERSISTENCJA SESJI ────────────────────────────────────────────────────────

class TestSessionPersistence:

    def test_session_persists_after_page_refresh(self, driver):
        """Po zalogowaniu i odświeżeniu strony użytkownik nadal jest zalogowany."""
        open_app(driver)
        fill_auth_form(driver, EXISTING_EMAIL, EXISTING_PASSWORD)
        submit_form(driver)
        assert is_logged_in(driver), "Logowanie nie powiodło się"

        driver.refresh()

        assert is_logged_in(driver), (
            "Po odświeżeniu strony użytkownik powinien nadal być zalogowany (token w localStorage)"
        )

    def test_no_token_shows_auth_page(self, driver):
        """Bez tokenu w localStorage zawsze wyświetla się ekran logowania."""
        driver.get(BASE_URL)
        driver.execute_script("localStorage.clear();")
        driver.refresh()

        assert is_on_auth_page(driver), "Bez tokenu powinna być widoczna strona logowania"

    def test_logged_in_token_in_localstorage(self, driver):
        """Po poprawnym logowaniu token jest zapisany w localStorage."""
        open_app(driver)
        fill_auth_form(driver, EXISTING_EMAIL, EXISTING_PASSWORD)
        submit_form(driver)
        assert is_logged_in(driver)

        token = driver.execute_script("return localStorage.getItem('token');")
        assert token, "Token powinien być zapisany w localStorage po zalogowaniu"
        assert len(token) > 10, "Token wygląda nieprawidłowo (zbyt krótki)"

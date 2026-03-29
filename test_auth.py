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

    def test_register_existing_email_shows_error(self, driver, existing_user):
        """Rejestracja z już istniejącym emailem → komunikat błędu."""
        existing_email, existing_password = existing_user
        open_app(driver)
        switch_to_register(driver)

        fill_auth_form(driver, existing_email, existing_password)
        submit_form(driver)

        error = get_error(driver)
        assert error, "Brak komunikatu błędu dla istniejącego emaila"
        # Wiadomość powinna zawierać informację o zajętym emailu lub konflikcie
        assert any(
            kw in error.lower()
            for kw in ["już istnieje", "exist", "registered", "zarejestrowany", "email"]
        ), f"Nieoczekiwana treść błędu: {error}"

    def test_register_empty_fields_blocked(self, driver):
        """Formularz rejestracji z pustymi polami nie może zostać wysłany."""
        open_app(driver)
        switch_to_register(driver)
        submit_form(driver)

        # Strona powinna nadal pokazywać ekran auth
        assert is_on_auth_page(driver), "Po próbie wysłania pustego formularza powinien być widoczny ekran auth"
        assert not is_logged_in(driver, timeout=3), "Nie powinno dać się zarejestrować z pustymi polami"

    def test_register_invalid_email_format_blocked(self, driver):
        """Rejestracja z nieprawidłowym formatem emaila → walidacja HTML5 blokuje."""
        open_app(driver)
        switch_to_register(driver)

        email_input = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        email_input.clear()
        email_input.send_keys("nieprawidlowy-email")
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys("haslo123")
        submit_form(driver)

        # Walidacja HTML5 powinna zablokować wysłanie – dashboard nie może się pojawić
        assert not is_logged_in(driver, timeout=3), "Nie powinno dać się zarejestrować z nieprawidłowym emailem"
        assert is_on_auth_page(driver), "Ekran auth powinien być nadal widoczny"

    def test_register_then_login_with_new_credentials(self, driver):
        """Po rejestracji nowego konta użytkownik może się zalogować tymi danymi."""
        open_app(driver)
        switch_to_register(driver)

        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = "haslo123"
        fill_auth_form(driver, unique_email, password)
        submit_form(driver)

        # Czekamy na toast sukcesu i powrót do zakładki logowania
        wait(driver).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".toast")))
        wait(driver).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".auth-tab.active"))
        )

        # Logujemy się nowo utworzonym kontem
        fill_auth_form(driver, unique_email, password)
        submit_form(driver)

        assert is_logged_in(driver), "Nowo zarejestrowany użytkownik powinien móc się zalogować"


# ── LOGOWANIE ─────────────────────────────────────────────────────────────────

class TestLogin:

    def test_login_valid_credentials(self, driver, existing_user):
        """Logowanie poprawnymi danymi → dashboard widoczny, email użytkownika w topbarze."""
        existing_email, existing_password = existing_user
        open_app(driver)
        fill_auth_form(driver, existing_email, existing_password)
        submit_form(driver)

        assert is_logged_in(driver), "Dashboard nie pojawił się po poprawnym logowaniu"

        topbar_user = driver.find_element(By.CSS_SELECTOR, ".topbar-user").text
        assert existing_email in topbar_user, (
            f"Email użytkownika '{existing_email}' nie widoczny w topbarze (jest: '{topbar_user}')"
        )

    def test_login_wrong_password_shows_error(self, driver, existing_user):
        """Logowanie błędnym hasłem → komunikat błędu, brak dashboardu."""
        existing_email, _ = existing_user
        open_app(driver)
        fill_auth_form(driver, existing_email, "bledne_haslo_xyz")
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

    def test_session_persists_after_page_refresh(self, driver, existing_user):
        """Po zalogowaniu i odświeżeniu strony użytkownik nadal jest zalogowany."""
        existing_email, existing_password = existing_user
        open_app(driver)
        fill_auth_form(driver, existing_email, existing_password)
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

    def test_logged_in_token_in_localstorage(self, driver, existing_user):
        """Po poprawnym logowaniu token jest zapisany w localStorage."""
        existing_email, existing_password = existing_user
        open_app(driver)
        fill_auth_form(driver, existing_email, existing_password)
        submit_form(driver)
        assert is_logged_in(driver)

        token = driver.execute_script("return localStorage.getItem('token');")
        assert token, "Token powinien być zapisany w localStorage po zalogowaniu"
        assert len(token) > 10, "Token wygląda nieprawidłowo (zbyt krótki)"

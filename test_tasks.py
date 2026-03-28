"""
Testy E2E – Operacje na zadaniach (Selenium + pytest)
Pokrycie:
  - Dodanie zadania: modal (+ Nowe zadanie) → wypełnienie → zapis → pojawia się na liście
  - Edycja: modal edycji → zmiana danych → zapis
  - Usunięcie: confirm() → znika z listy
  - Status: toggle todo / done
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5173"
TASK_TITLE = "Zadanie testowe Selenium"
TASK_TITLE_EDITED = "Zadanie testowe Selenium (edytowane)"


# ── cleanup fixture ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def cleanup_test_tasks(driver_logged_in):
    """Po każdym teście usuwa wszystkie zadania testowe klikając przycisk usuń."""
    yield
    driver = driver_logged_in
    try:
        driver.execute_script("window.confirm = function() { return true; }")
        for title in (TASK_TITLE, TASK_TITLE_EDITED):
            while True:
                cards = driver.find_elements(
                    By.XPATH,
                    f"//*[contains(@class,'task-card') and .//*[contains(text(),'{title}')]]"
                )
                if not cards:
                    break
                try:
                    del_btn = cards[0].find_element(By.CSS_SELECTOR, ".icon-btn.danger")
                    del_btn.click()
                    WebDriverWait(driver, 5).until(EC.staleness_of(cards[0]))
                except Exception:
                    break
    except Exception:
        pass


# ── helpers ───────────────────────────────────────────────────────────────────

def wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def open_add_task_modal(driver):
    """Klika '+ Nowe zadanie' i czeka na pojawienie się modala."""
    btn = wait(driver).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Nowe zadanie')]"))
    )
    btn.click()
    return wait(driver).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal"))
    )


def add_task(driver, title):
    """Otwiera modal nowego zadania, wypełnia tytuł i zapisuje."""
    modal = open_add_task_modal(driver)
    title_input = modal.find_element(By.CSS_SELECTOR, "input[placeholder='Co chcesz zrobić?']")
    title_input.clear()
    title_input.send_keys(title)
    save_btn = modal.find_element(By.XPATH, ".//button[contains(text(),'Dodaj zadanie')]")
    save_btn.click()
    wait(driver).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-overlay"))
    )


def get_task_item(driver, title, timeout=8):
    """Zwraca element karty zadania zawierający podany tytuł."""
    return wait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(@class,'task-card') and .//*[contains(text(),'{title}')]]")
        )
    )


def task_exists(driver, title, timeout=6):
    """Sprawdza czy zadanie o podanym tytule jest widoczne na liście."""
    try:
        get_task_item(driver, title, timeout)
        return True
    except Exception:
        return False


def task_gone(driver, title, timeout=6):
    """Sprawdza czy zadanie zniknęło z listy."""
    try:
        wait(driver, timeout).until(
            EC.invisibility_of_element_located(
                (By.XPATH, f"//*[contains(@class,'task-card') and .//*[contains(text(),'{title}')]]")
            )
        )
        return True
    except Exception:
        return False


# ── DODANIE ZADANIA ───────────────────────────────────────────────────────────

class TestAddTask:

    def test_add_task_appears_on_list(self, driver_logged_in):
        """Otwarcie modala, wypełnienie formularza i zapis → zadanie pojawia się na liście."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)

        assert task_exists(driver, TASK_TITLE), (
            f"Zadanie '{TASK_TITLE}' nie pojawiło się na liście po dodaniu"
        )

    def test_add_task_clears_input(self, driver_logged_in):
        """Po dodaniu zadania i ponownym otwarciu modala pole tytułu jest puste."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)

        # Otwórz modal ponownie – tytuł powinien być pusty (nowy modal)
        modal = open_add_task_modal(driver)
        title_input = modal.find_element(By.CSS_SELECTOR, "input[placeholder='Co chcesz zrobić?']")
        assert title_input.get_attribute("value") == "", (
            "Pole tytułu powinno być puste przy ponownym otwarciu modala"
        )
        # Zamknij modal
        modal.find_element(By.XPATH, ".//button[contains(text(),'Anuluj')]").click()

    def test_add_task_empty_title_blocked(self, driver_logged_in):
        """Nie można dodać zadania bez tytułu — przycisk 'Dodaj zadanie' jest nieaktywny."""
        driver = driver_logged_in

        modal = open_add_task_modal(driver)
        save_btn = modal.find_element(By.XPATH, ".//button[contains(text(),'Dodaj zadanie')]")

        assert save_btn.get_attribute("disabled") is not None, (
            "Przycisk 'Dodaj zadanie' powinien być nieaktywny gdy tytuł jest pusty"
        )
        # Zamknij modal
        modal.find_element(By.XPATH, ".//button[contains(text(),'Anuluj')]").click()


# ── EDYCJA ZADANIA ────────────────────────────────────────────────────────────

class TestEditTask:

    def test_edit_task_via_modal(self, driver_logged_in):
        """Kliknięcie edytuj → zmiana tytułu → zapis → lista zaktualizowana."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        task_item = get_task_item(driver, TASK_TITLE)

        edit_btn = task_item.find_element(By.CSS_SELECTOR, ".icon-btn[title='Edytuj']")
        edit_btn.click()

        modal = wait(driver).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal"))
        )

        title_field = modal.find_element(By.CSS_SELECTOR, "input[placeholder='Co chcesz zrobić?']")
        title_field.clear()
        title_field.send_keys(TASK_TITLE_EDITED)

        save_btn = modal.find_element(
            By.XPATH, ".//button[contains(text(),'Zapi') or contains(text(),'Save')]"
        )
        save_btn.click()

        wait(driver).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-overlay"))
        )

        assert task_exists(driver, TASK_TITLE_EDITED), (
            f"Edytowany tytuł '{TASK_TITLE_EDITED}' nie pojawił się na liście"
        )

    def test_edit_cancel_keeps_original(self, driver_logged_in):
        """Anulowanie edycji → oryginalna nazwa pozostaje bez zmian."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        task_item = get_task_item(driver, TASK_TITLE)

        edit_btn = task_item.find_element(By.CSS_SELECTOR, ".icon-btn[title='Edytuj']")
        edit_btn.click()

        modal = wait(driver).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal"))
        )

        cancel_btn = modal.find_element(
            By.XPATH, ".//button[contains(text(),'Anuluj') or contains(text(),'Cancel')]"
        )
        cancel_btn.click()

        wait(driver).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-overlay"))
        )

        assert task_exists(driver, TASK_TITLE), (
            f"Oryginalne zadanie '{TASK_TITLE}' powinno nadal być widoczne po anulowaniu edycji"
        )


# ── USUNIĘCIE ZADANIA ─────────────────────────────────────────────────────────

class TestDeleteTask:

    def test_delete_task_disappears_from_list(self, driver_logged_in):
        """Kliknięcie usuń → confirm() → zadanie znika z listy."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        assert task_exists(driver, TASK_TITLE), "Zadanie nie zostało dodane przed usunięciem"

        task_item = get_task_item(driver, TASK_TITLE)
        delete_btn = task_item.find_element(By.CSS_SELECTOR, ".icon-btn.danger")

        driver.execute_script("window.confirm = function() { return true; }")
        delete_btn.click()

        # Sprawdź czy konkretna karta zadania zniknęła z DOM
        wait(driver).until(EC.staleness_of(task_item)), (
            f"Zadanie '{TASK_TITLE}' powinno zniknąć z listy po usunięciu"
        )

    def test_delete_task_shows_toast(self, driver_logged_in):
        """Po usunięciu zadania pojawia się toast 'Zadanie usunięte'."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        assert task_exists(driver, TASK_TITLE), "Zadanie nie zostało dodane przed usunięciem"

        task_item = get_task_item(driver, TASK_TITLE)
        delete_btn = task_item.find_element(By.CSS_SELECTOR, ".icon-btn.danger")

        driver.execute_script("window.confirm = function() { return true; }")
        delete_btn.click()

        toast = wait(driver).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".toast"))
        )
        assert "Zadanie usunięte" in toast.text, (
            f"Oczekiwano toastu 'Zadanie usunięte', otrzymano: '{toast.text}'"
        )

    def test_delete_cancelled_keeps_task(self, driver_logged_in):
        """Odrzucenie confirm() → zadanie pozostaje na liście."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        assert task_exists(driver, TASK_TITLE)

        task_item = get_task_item(driver, TASK_TITLE)
        delete_btn = task_item.find_element(By.CSS_SELECTOR, ".icon-btn.danger")

        driver.execute_script("window.confirm = function() { return false; }")
        delete_btn.click()

        assert task_exists(driver, TASK_TITLE), (
            f"Zadanie '{TASK_TITLE}' powinno pozostać na liście gdy confirm() odrzucony"
        )


# ── ZMIANA STATUSU ────────────────────────────────────────────────────────────

class TestToggleStatus:

    def test_toggle_task_to_done(self, driver_logged_in):
        """Kliknięcie toggle → status zmienia się na 'done'."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        task_item = get_task_item(driver, TASK_TITLE)

        toggle = task_item.find_element(By.CSS_SELECTOR, ".task-check")
        toggle.click()

        updated_item = wait(driver).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 f"//*[contains(@class,'task-card') and contains(@class,'done')"
                 f" and .//*[contains(text(),'{TASK_TITLE}')]]")
            )
        )
        assert updated_item, f"Zadanie '{TASK_TITLE}' powinno mieć status 'done' po przełączeniu"

    def test_toggle_task_back_to_todo(self, driver_logged_in):
        """Dwukrotne kliknięcie toggle → powrót do statusu 'todo'."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        task_item = get_task_item(driver, TASK_TITLE)

        toggle = task_item.find_element(By.CSS_SELECTOR, ".task-check")
        toggle.click()  # → done

        # Poczekaj na toggle w odświeżonym DOM i kliknij ponownie → todo
        toggle = wait(driver).until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 f"//div[contains(@class,'task-card') and contains(@class,'done')"
                 f" and .//div[contains(text(),'{TASK_TITLE}')]]//div[contains(@class,'task-check')]")
            )
        )
        toggle.click()  # → todo

        updated_item = wait(driver).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 f"//*[contains(@class,'task-card') and not(contains(@class,'done'))"
                 f" and .//*[contains(text(),'{TASK_TITLE}')]]")
            )
        )
        assert updated_item, f"Zadanie '{TASK_TITLE}' powinno wrócić do statusu 'todo' po drugim przełączeniu"

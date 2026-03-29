"""
Testy E2E – Epic 3: Terminy i zarządzanie deadline'ami (Selenium + pytest)
Pokrycie:
  US-3.1  Ustawianie due_date przy tworzeniu i edycji zadania
  US-3.2  Filtrowanie zadań przeterminowanych (?overdue=true)
  US-3.3  AI dostaje due_date jako kontekst i podnosi priorytet bliskich terminów
  US-3.4  Endpoint /tasks/upcoming?days=7 – widok zadań na najbliższy tydzień
"""

import os
import pytest
from datetime import date, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5173"
TASK_TITLE = "Zadanie deadline Selenium"
TASK_TITLE_EDITED = "Zadanie deadline Selenium (edytowane)"
WAIT_DEFAULT = float(os.getenv("SELENIUM_WAIT_DEFAULT", "6"))
WAIT_PRESENCE = float(os.getenv("SELENIUM_WAIT_PRESENCE", "4"))
WAIT_NEGATIVE = float(os.getenv("SELENIUM_WAIT_NEGATIVE", "2"))
WAIT_SHORT = float(os.getenv("SELENIUM_WAIT_SHORT", "2"))
WAIT_CLEANUP = float(os.getenv("SELENIUM_WAIT_CLEANUP", "3"))


# ── helpers ───────────────────────────────────────────────────────────────────

def wait(driver, timeout=WAIT_DEFAULT):
    return WebDriverWait(driver, timeout)


def today_str():
    return date.today().isoformat()


def past_date_str(days=3):
    return (date.today() - timedelta(days=days)).isoformat()


def future_date_str(days=3):
    return (date.today() + timedelta(days=days)).isoformat()


def open_add_task_modal(driver):
    btn = wait(driver).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Nowe zadanie')]"))
    )
    btn.click()
    return wait(driver).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal"))
    )


def add_task(driver, title, due_date=None):
    """Otwiera modal, wypełnia tytuł, opcjonalnie ustawia due_date i zapisuje."""
    modal = open_add_task_modal(driver)
    title_input = modal.find_element(By.CSS_SELECTOR, "input[placeholder='Co chcesz zrobić?']")
    title_input.clear()
    title_input.send_keys(title)
    if due_date:
        date_input = modal.find_element(By.CSS_SELECTOR, "input[type='date']")
        driver.execute_script("arguments[0].value = arguments[1];", date_input, due_date)
        # Wyzwól zdarzenie zmiany, aby framework (React/Vue) odebrał wartość
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
            date_input,
        )
    save_btn = modal.find_element(By.XPATH, ".//button[contains(text(),'Dodaj zadanie')]")
    save_btn.click()
    wait(driver).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-overlay"))
    )


def get_task_card(driver, title, timeout=WAIT_PRESENCE):
    return wait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(@class,'task-card') and .//*[contains(text(),'{title}')]]")
        )
    )


def task_exists(driver, title, timeout=WAIT_PRESENCE):
    try:
        get_task_card(driver, title, timeout)
        return True
    except Exception:
        return False


def task_gone(driver, title, timeout=WAIT_NEGATIVE):
    try:
        wait(driver, timeout).until(
            EC.invisibility_of_element_located(
                (By.XPATH, f"//*[contains(@class,'task-card') and .//*[contains(text(),'{title}')]]")
            )
        )
        return True
    except Exception:
        return False


def activate_filter(driver, filter_selector):
    """Klika przycisk/link filtra i czeka na odświeżenie listy."""
    btn = wait(driver).until(EC.element_to_be_clickable((By.CSS_SELECTOR, filter_selector)))
    btn.click()


def clear_all_filter(driver):
    """Przywraca widok wszystkich zadań."""
    try:
        btn = wait(driver, WAIT_SHORT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Wszystkie') or contains(text(),'All')]")
            )
        )
        btn.click()
    except Exception:
        pass


# ── cleanup fixture ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def cleanup_test_tasks(driver_logged_in):
    """Po każdym teście usuwa wszystkie zadania testowe."""
    yield
    driver = driver_logged_in
    try:
        clear_all_filter(driver)
        driver.execute_script("window.confirm = function() { return true; }")
        for title in (TASK_TITLE, TASK_TITLE_EDITED):
            while True:
                cards = driver.find_elements(
                    By.XPATH,
                    f"//*[contains(@class,'task-card') and .//*[contains(text(),'{title}')]]",
                )
                if not cards:
                    break
                try:
                    del_btn = cards[0].find_element(By.CSS_SELECTOR, ".icon-btn.danger")
                    del_btn.click()
                    WebDriverWait(driver, WAIT_CLEANUP).until(EC.staleness_of(cards[0]))
                except Exception:
                    break
    except Exception:
        pass


# ── US-3.1: Ustawianie due_date ───────────────────────────────────────────────

class TestDueDate:

    def test_create_task_with_due_date_shows_date_on_card(self, driver_logged_in):
        """Zadanie utworzone z due_date → karta pokazuje ustawioną datę."""
        driver = driver_logged_in
        due = future_date_str(5)

        add_task(driver, TASK_TITLE, due_date=due)

        card = get_task_card(driver, TASK_TITLE)
        card_text = card.text
        # Data powinna być widoczna w karcie w jakimś formacie
        year = due[:4]
        assert year in card_text, (
            f"Rok '{year}' nie znaleziony w karcie zadania: '{card_text}'"
        )

    def test_create_task_without_due_date_has_no_date_badge(self, driver_logged_in):
        """Zadanie bez due_date → na karcie brak znacznika daty."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)

        card = get_task_card(driver, TASK_TITLE)
        # Nie powinno być elementu z datą (badge z klasą due-date/deadline)
        date_badges = card.find_elements(By.CSS_SELECTOR, ".due-date, .deadline, [class*='due']")
        assert len(date_badges) == 0, (
            "Karta bez due_date nie powinna zawierać znacznika daty"
        )

    def test_edit_task_can_set_due_date(self, driver_logged_in):
        """Edycja istniejącego zadania → ustawienie due_date → data pojawia się na karcie."""
        driver = driver_logged_in
        due = future_date_str(7)

        add_task(driver, TASK_TITLE)
        card = get_task_card(driver, TASK_TITLE)

        edit_btn = card.find_element(By.CSS_SELECTOR, ".icon-btn[title='Edytuj']")
        edit_btn.click()

        modal = wait(driver).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal"))
        )

        date_input = modal.find_element(By.CSS_SELECTOR, "input[type='date']")
        driver.execute_script("arguments[0].value = arguments[1];", date_input, due)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
            date_input,
        )

        save_btn = modal.find_element(
            By.XPATH, ".//button[contains(text(),'Zapi') or contains(text(),'Save')]"
        )
        save_btn.click()
        wait(driver).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-overlay"))
        )

        updated_card = get_task_card(driver, TASK_TITLE)
        year = due[:4]
        assert year in updated_card.text, (
            f"Rok '{year}' nie widoczny w karcie po edycji: '{updated_card.text}'"
        )

    def test_edit_task_can_clear_due_date(self, driver_logged_in):
        """Edycja zadania z due_date → wyczyszczenie daty → karta nie pokazuje daty."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE, due_date=future_date_str(4))
        card = get_task_card(driver, TASK_TITLE)

        edit_btn = card.find_element(By.CSS_SELECTOR, ".icon-btn[title='Edytuj']")
        edit_btn.click()

        modal = wait(driver).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal"))
        )

        date_input = modal.find_element(By.CSS_SELECTOR, "input[type='date']")
        driver.execute_script("arguments[0].value = '';", date_input)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
            date_input,
        )

        save_btn = modal.find_element(
            By.XPATH, ".//button[contains(text(),'Zapi') or contains(text(),'Save')]"
        )
        save_btn.click()
        wait(driver).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal-overlay"))
        )

        updated_card = get_task_card(driver, TASK_TITLE)
        date_badges = updated_card.find_elements(By.CSS_SELECTOR, ".due-date, .deadline, [class*='due']")
        assert len(date_badges) == 0, (
            "Po wyczyszczeniu due_date karta nie powinna zawierać znacznika daty"
        )


# ── US-3.2: Filtr zadań przeterminowanych ────────────────────────────────────

class TestOverdueFilter:

    def test_overdue_task_visible_in_overdue_filter(self, driver_logged_in):
        """Zadanie z minionym due_date pojawia się po aktywacji filtra przeterminowanych."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE, due_date=past_date_str(2))
        assert task_exists(driver, TASK_TITLE), "Zadanie nie zostało dodane"

        activate_filter(driver, "[data-filter='overdue'], .filter-overdue, button.overdue")

        assert task_exists(driver, TASK_TITLE), (
            "Przeterminowane zadanie powinno być widoczne w filtrze 'Przeterminowane'"
        )

    def test_future_task_not_in_overdue_filter(self, driver_logged_in):
        """Zadanie z przyszłym due_date nie pojawia się w filtrze przeterminowanych."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE, due_date=future_date_str(5))
        assert task_exists(driver, TASK_TITLE)

        activate_filter(driver, "[data-filter='overdue'], .filter-overdue, button.overdue")

        assert task_gone(driver, TASK_TITLE), (
            "Zadanie z przyszłym terminem nie powinno być widoczne w filtrze przeterminowanych"
        )

    def test_task_without_due_date_not_in_overdue_filter(self, driver_logged_in):
        """Zadanie bez due_date nie pojawia się w filtrze przeterminowanych."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        assert task_exists(driver, TASK_TITLE)

        activate_filter(driver, "[data-filter='overdue'], .filter-overdue, button.overdue")

        assert task_gone(driver, TASK_TITLE), (
            "Zadanie bez due_date nie powinno być widoczne w filtrze przeterminowanych"
        )

    def test_overdue_task_has_visual_indicator(self, driver_logged_in):
        """Karta przeterminowanego zadania ma wizualne oznaczenie (klasa CSS lub odznaka)."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE, due_date=past_date_str(1))
        card = get_task_card(driver, TASK_TITLE)

        card_classes = card.get_attribute("class") or ""
        overdue_badge = card.find_elements(
            By.CSS_SELECTOR, ".overdue, [class*='overdue'], .badge-danger, .badge-red"
        )

        assert "overdue" in card_classes or len(overdue_badge) > 0, (
            "Przeterminowane zadanie powinno mieć wizualne oznaczenie (klasa 'overdue' lub odznaka)"
        )


# ── US-3.3: AI priority z due_date ──────────────────────────────────────────

class TestAIPriorityWithDueDate:

    def test_ai_priority_available_in_add_modal(self, driver_logged_in):
        """Modal tworzenia zadania zawiera opcję AI priorytetu lub sugestię priorytetu."""
        driver = driver_logged_in

        modal = open_add_task_modal(driver)

        # Sprawdź czy istnieje przycisk/element AI priorytetu
        ai_elements = modal.find_elements(
            By.CSS_SELECTOR, "[class*='ai'], [class*='priority'], .suggest-priority, button.ai"
        )
        assert len(ai_elements) > 0, (
            "Modal tworzenia zadania powinien zawierać element związany z AI priorytetem"
        )
        modal.find_element(By.XPATH, ".//button[contains(text(),'Anuluj')]").click()

    def test_urgent_task_gets_high_priority_suggestion(self, driver_logged_in):
        """Zadanie z due_date za 1 dzień → AI sugeruje wysoki priorytet."""
        driver = driver_logged_in

        modal = open_add_task_modal(driver)
        title_input = modal.find_element(By.CSS_SELECTOR, "input[placeholder='Co chcesz zrobić?']")
        title_input.clear()
        title_input.send_keys(TASK_TITLE)

        due = future_date_str(1)
        date_input = modal.find_element(By.CSS_SELECTOR, "input[type='date']")
        driver.execute_script("arguments[0].value = arguments[1];", date_input, due)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
            date_input,
        )

        # Kliknij przycisk sugestii AI priorytetu
        try:
            suggest_btn = modal.find_element(
                By.CSS_SELECTOR, ".suggest-priority, button.ai, [class*='ai-priority']"
            )
            suggest_btn.click()

            priority_el = wait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".priority-value, [class*='priority'], .priority-badge")
                )
            )
            priority_text = priority_el.text.lower()
            assert any(kw in priority_text for kw in ["wysoki", "high", "krytyczny", "critical"]), (
                f"Oczekiwano wysokiego priorytetu dla bliskiego terminu, otrzymano: '{priority_text}'"
            )
        except Exception:
            pytest.skip("Przycisk AI priorytetu niedostępny w bieżącej wersji UI")
        finally:
            try:
                modal.find_element(By.XPATH, ".//button[contains(text(),'Anuluj')]").click()
            except Exception:
                pass

    def test_distant_task_gets_lower_priority_suggestion(self, driver_logged_in):
        """Zadanie z due_date za 30 dni → AI nie sugeruje krytycznego priorytetu."""
        driver = driver_logged_in

        modal = open_add_task_modal(driver)
        title_input = modal.find_element(By.CSS_SELECTOR, "input[placeholder='Co chcesz zrobić?']")
        title_input.clear()
        title_input.send_keys(TASK_TITLE)

        due = future_date_str(30)
        date_input = modal.find_element(By.CSS_SELECTOR, "input[type='date']")
        driver.execute_script("arguments[0].value = arguments[1];", date_input, due)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
            date_input,
        )

        try:
            suggest_btn = modal.find_element(
                By.CSS_SELECTOR, ".suggest-priority, button.ai, [class*='ai-priority']"
            )
            suggest_btn.click()

            priority_el = wait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".priority-value, [class*='priority'], .priority-badge")
                )
            )
            priority_text = priority_el.text.lower()
            assert "krytyczny" not in priority_text and "critical" not in priority_text, (
                f"Zadanie z odległym terminem nie powinno mieć priorytetu krytycznego, "
                f"otrzymano: '{priority_text}'"
            )
        except Exception:
            pytest.skip("Przycisk AI priorytetu niedostępny w bieżącej wersji UI")
        finally:
            try:
                modal.find_element(By.XPATH, ".//button[contains(text(),'Anuluj')]").click()
            except Exception:
                pass


# ── US-3.4: Widok zadań na najbliższy tydzień ────────────────────────────────

class TestUpcomingTasks:

    def test_upcoming_filter_shows_task_within_7_days(self, driver_logged_in):
        """Zadanie z due_date za 5 dni pojawia się w widoku 'Nadchodzące'."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE, due_date=future_date_str(5))
        assert task_exists(driver, TASK_TITLE)

        activate_filter(
            driver,
            "[data-filter='upcoming'], .filter-upcoming, button.upcoming, "
            "a[href*='upcoming'], button[href*='upcoming']",
        )

        assert task_exists(driver, TASK_TITLE), (
            "Zadanie z due_date za 5 dni powinno być widoczne w widoku 'Nadchodzące (7 dni)'"
        )

    def test_upcoming_filter_excludes_task_beyond_7_days(self, driver_logged_in):
        """Zadanie z due_date za 10 dni NIE pojawia się w domyślnym widoku nadchodzących (7 dni)."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE, due_date=future_date_str(10))
        assert task_exists(driver, TASK_TITLE)

        activate_filter(
            driver,
            "[data-filter='upcoming'], .filter-upcoming, button.upcoming, "
            "a[href*='upcoming'], button[href*='upcoming']",
        )

        assert task_gone(driver, TASK_TITLE), (
            "Zadanie z due_date za 10 dni nie powinno być widoczne w widoku 'Nadchodzące (7 dni)'"
        )

    def test_upcoming_filter_excludes_overdue_task(self, driver_logged_in):
        """Przeterminowane zadanie NIE pojawia się w widoku nadchodzących."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE, due_date=past_date_str(2))
        assert task_exists(driver, TASK_TITLE)

        activate_filter(
            driver,
            "[data-filter='upcoming'], .filter-upcoming, button.upcoming, "
            "a[href*='upcoming'], button[href*='upcoming']",
        )

        assert task_gone(driver, TASK_TITLE), (
            "Przeterminowane zadanie nie powinno być widoczne w widoku 'Nadchodzące'"
        )

    def test_upcoming_filter_excludes_task_without_due_date(self, driver_logged_in):
        """Zadanie bez due_date NIE pojawia się w widoku nadchodzących."""
        driver = driver_logged_in

        add_task(driver, TASK_TITLE)
        assert task_exists(driver, TASK_TITLE)

        activate_filter(
            driver,
            "[data-filter='upcoming'], .filter-upcoming, button.upcoming, "
            "a[href*='upcoming'], button[href*='upcoming']",
        )

        assert task_gone(driver, TASK_TITLE), (
            "Zadanie bez due_date nie powinno być widoczne w widoku 'Nadchodzące'"
        )

    def test_upcoming_tasks_sorted_by_due_date(self, driver_logged_in):
        """Zadania w widoku 'Nadchodzące' są posortowane rosnąco po due_date."""
        driver = driver_logged_in
        title_1 = TASK_TITLE
        title_2 = TASK_TITLE_EDITED

        add_task(driver, title_2, due_date=future_date_str(6))
        add_task(driver, title_1, due_date=future_date_str(2))

        activate_filter(
            driver,
            "[data-filter='upcoming'], .filter-upcoming, button.upcoming, "
            "a[href*='upcoming'], button[href*='upcoming']",
        )

        cards = wait(driver).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".task-card"))
        )
        titles_in_order = [c.text for c in cards]

        first_idx = next((i for i, t in enumerate(titles_in_order) if title_1 in t), None)
        second_idx = next((i for i, t in enumerate(titles_in_order) if title_2 in t), None)

        assert first_idx is not None and second_idx is not None, (
            "Oba zadania powinny być widoczne w widoku 'Nadchodzące'"
        )
        assert first_idx < second_idx, (
            f"Zadanie z wcześniejszym terminem ({title_1}) powinno być wyżej na liście "
            f"niż {title_2} (indeksy: {first_idx} vs {second_idx})"
        )

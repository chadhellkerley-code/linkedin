"""Playwright helpers for real LinkedIn automation (fase 2)."""
from __future__ import annotations

import os
from typing import Tuple

try:  # pragma: no cover
    from playwright.sync_api import BrowserContext, sync_playwright  # type: ignore
except Exception:  # pragma: no cover
    BrowserContext = object  # type: ignore
    sync_playwright = None  # type: ignore


def load_session(context_factory, session_file: str):
    """Create a context loading a saved storage state when available."""
    if os.path.exists(session_file):
        return context_factory(storage_state=session_file)
    return context_factory()


def save_session(context: BrowserContext, session_file: str) -> None:
    """Persist the current storage state to disk."""
    os.makedirs(os.path.dirname(session_file), exist_ok=True)
    context.storage_state(path=session_file)


def login_manual(email: str, session_file: str) -> Tuple[bool, str]:
    """Run a manual login flow with a visible browser and persist the session."""
    if sync_playwright is None:
        return False, "Playwright no está disponible en este entorno."
    try:  # pragma: no cover - requires real browser
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.linkedin.com/login")
            print("Inicie sesión manualmente en la ventana abierta.")
            print("Cuando esté dentro del feed y vea su inicio, vuelva aquí y presione ENTER.")
            input("Presiona ENTER cuando hayas finalizado el login...")
            save_session(context, session_file)
            browser.close()
        return True, "Sesión guardada."
    except Exception as exc:  # pragma: no cover - runtime errors
        return False, f"Error durante el login manual: {exc}"


def send_message_real(session_file: str, lead_url: str, message: str) -> Tuple[bool, str]:
    """Open Chromium with the stored session and send a LinkedIn message."""
    if sync_playwright is None:
        return False, "Playwright no está disponible en este entorno."
    try:  # pragma: no cover - requires real browser
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            context = load_session(browser.new_context, session_file)
            page = context.new_page()
            page.goto(lead_url)
            selectors = [
                "button[aria-label='Message']",
                "button[aria-label='Mensaje']",
                "a[href*='/messaging/thread']",
            ]
            button_found = False
            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.click(selector)
                    button_found = True
                    break
                except Exception:
                    continue
            if not button_found:
                browser.close()
                return False, "No se encontró el botón de mensaje."
            page.fill("div[role='textbox']", message)
            page.keyboard.press("Enter")
            browser.close()
            return True, "ENVIADO"
    except Exception as exc:  # pragma: no cover - runtime errors
        return False, f"Error al enviar mensaje: {exc}"
    return False, "Error desconocido"

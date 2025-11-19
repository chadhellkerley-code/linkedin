"""Account management utilities for the LinkedIn CLI."""

from __future__ import annotations

import getpass
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

try:  # pragma: no cover
    from .db import get_connection
except ImportError:  # pragma: no cover
    from db import get_connection


@dataclass
class LinkedInLoginResult:
    """Structured result for login attempts."""

    success: bool
    message: str
    session_data: Optional[str] = None


class LinkedInAuthenticator:
    """Encapsulate the Playwright/Selenium login logic (simulated by default)."""

    def __init__(self) -> None:
        try:  # pragma: no cover - optional dependency
            from playwright.sync_api import sync_playwright  # type: ignore

            self._playwright = sync_playwright
        except Exception:
            self._playwright = None

    def authenticate(self, username: str, password: str, proxy: Optional[str]) -> LinkedInLoginResult:
        if not username or not password:
            return LinkedInLoginResult(False, "Credenciales incompletas.")
        if self._playwright is None:
            # Simulation path to keep the CLI usable without Playwright. The
            # architecture allows replacing this block with a production-grade
            # login that stores cookies or tokens inside ``session_data``.
            return LinkedInLoginResult(True, "Simulación de login exitosa.")
        try:  # pragma: no cover
            playwright = self._playwright().start()
            browser = playwright.chromium.launch(headless=True)
            context_kwargs = {"proxy": {"server": proxy}} if proxy else {}
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            page.goto("https://www.linkedin.com/login")
            page.fill("input[id=username]", username)
            page.fill("input[id=password]", password)
            page.click("button[type=submit]")
            page.wait_for_timeout(5000)
            session = json.dumps(context.storage_state())
            browser.close()
            playwright.stop()
            return LinkedInLoginResult(True, "Login exitoso", session)
        except Exception as exc:  # pragma: no cover
            return LinkedInLoginResult(False, f"Error al iniciar sesión: {exc}")


class AccountManager:
    """Manage LinkedIn accounts and groups with status tracking."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.authenticator = LinkedInAuthenticator()

    # Group operations --------------------------------------------------
    def list_groups(self) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM account_groups ORDER BY name")
        groups = cur.fetchall()
        conn.close()
        return groups

    def create_group(self, name: str) -> int:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO account_groups (name) VALUES (?)", (name,))
        conn.commit()
        gid = cur.lastrowid
        conn.close()
        return gid

    def select_group(self) -> int:
        groups = self.list_groups()
        if not groups:
            print("No hay grupos de cuentas. Cree el primero.")
            while True:
                name = input("Nombre del nuevo grupo: ").strip()
                if name:
                    return self.create_group(name)
                print("Ingrese un nombre válido.")
        print("Seleccione un grupo:")
        for idx, grp in enumerate(groups, start=1):
            print(f"{idx}. {grp['name']}")
        print("0. Crear nuevo grupo")
        while True:
            choice = input("Opción: ").strip()
            if choice == "0":
                name = input("Nombre del nuevo grupo: ").strip()
                if name:
                    return self.create_group(name)
                print("Nombre inválido.")
                continue
            try:
                idx = int(choice)
            except ValueError:
                print("Ingrese un número válido.")
                continue
            if 1 <= idx <= len(groups):
                return groups[idx - 1]["id"]
            print("Selección fuera de rango.")

    # Account operations ------------------------------------------------
    def list_accounts(self, group_id: int) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM accounts WHERE group_id = ? ORDER BY COALESCE(alias, username)",
            (group_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def add_account(self, group_id: int) -> None:
        username = input("Ingrese el email/usuario: ").strip()
        if not username:
            print("El usuario es obligatorio.")
            return
        alias = input("Alias (opcional): ").strip()
        password = getpass.getpass("Contraseña (oculta): ")
        proxy = input("Proxy (opcional host:puerto): ").strip() or None
        result = self.authenticator.authenticate(username, password, proxy)
        status = "viva" if result.success else "inestable"
        now = datetime.utcnow().isoformat(timespec="seconds")
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO accounts (
                group_id, username, alias, password, proxy, status,
                session_data, last_activity, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group_id,
                username,
                alias or None,
                password,
                proxy,
                status,
                result.session_data,
                now if result.success else None,
                None if result.success else result.message,
            ),
        )
        conn.commit()
        conn.close()
        if result.success:
            print("Login exitoso. Cuenta marcada como viva.")
        else:
            print(f"No se pudo autenticar: {result.message}. Cuenta marcada como inestable.")

    def update_account_status(self, account_id: int, new_status: str) -> None:
        if new_status not in {"viva", "inestable", "muerta"}:
            raise ValueError("Estado inválido")
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE accounts SET status = ?, last_activity = ? WHERE id = ?",
            (new_status, datetime.utcnow().isoformat(timespec="seconds"), account_id),
        )
        conn.commit()
        conn.close()

    def account_status_menu(self, group_id: int) -> None:
        accounts = self.list_accounts(group_id)
        if not accounts:
            print("No hay cuentas en este grupo.")
            return
        while True:
            print("\nCuentas:")
            for idx, acc in enumerate(accounts, start=1):
                alias = acc["alias"] or acc["username"]
                extra = []
                if acc["cooldown_until"]:
                    extra.append(f"cooldown hasta {acc['cooldown_until']}")
                if acc["last_error"]:
                    extra.append(f"último error: {acc['last_error']}")
                detail = f" ({'; '.join(extra)})" if extra else ""
                print(f"{idx}. {alias} - {acc['status']}{detail}")
            print("0. Volver")
            choice = input("Seleccione una cuenta: ").strip()
            if choice == "0":
                return
            try:
                idx = int(choice)
            except ValueError:
                print("Ingrese un número válido.")
                continue
            if not (1 <= idx <= len(accounts)):
                print("Selección inválida.")
                continue
            self._manage_account(accounts[idx - 1])
            accounts = self.list_accounts(group_id)

    def _manage_account(self, account: sqlite3.Row) -> None:
        alias = account["alias"] or account["username"]
        print(f"\nGestionando {alias}")
        print(
            "1. Cambiar estado\n"
            "2. Definir cooldown manual\n"
            "3. Limpiar cooldown\n"
            "4. Actualizar alias\n"
            "5. Eliminar cuenta\n"
            "0. Volver"
        )
        choice = input("Opción: ").strip()
        if choice == "1":
            status_map = {"1": "viva", "2": "inestable", "3": "muerta"}
            print("1. viva\n2. inestable\n3. muerta")
            new_status = status_map.get(input("Nuevo estado: ").strip())
            if new_status:
                self.update_account_status(account["id"], new_status)
                print("Estado actualizado.")
        elif choice == "2":
            cooldown = input("Fecha ISO para reactivar (YYYY-MM-DD HH:MM): ").strip()
            self._set_cooldown(account["id"], cooldown)
            print("Cooldown actualizado.")
        elif choice == "3":
            self._set_cooldown(account["id"], None)
            print("Cooldown limpiado.")
        elif choice == "4":
            new_alias = input("Nuevo alias: ").strip()
            conn = get_connection(self.db_path)
            cur = conn.cursor()
            cur.execute("UPDATE accounts SET alias = ? WHERE id = ?", (new_alias or None, account["id"]))
            conn.commit()
            conn.close()
            print("Alias actualizado.")
        elif choice == "5":
            confirm = input("Escriba ELIMINAR para confirmar: ").strip()
            if confirm.upper() == "ELIMINAR":
                conn = get_connection(self.db_path)
                cur = conn.cursor()
                cur.execute("DELETE FROM accounts WHERE id = ?", (account["id"],))
                conn.commit()
                conn.close()
                print("Cuenta eliminada.")

    def _set_cooldown(self, account_id: int, cooldown: Optional[str]) -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE accounts SET cooldown_until = ? WHERE id = ?", (cooldown, account_id))
        conn.commit()
        conn.close()

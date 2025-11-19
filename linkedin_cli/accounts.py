"""Account management utilities for the LinkedIn CLI."""

from __future__ import annotations

import getpass
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

try:  # pragma: no cover
    from .db import get_connection
    from . import playwright_client
except ImportError:  # pragma: no cover
    from db import get_connection
    import playwright_client


SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")


class AccountManager:
    """Manage LinkedIn accounts and groups with status tracking."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

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
        save_password = input("¿Desea guardar la contraseña? (s/n): ").strip().lower()
        password: Optional[str] = None
        if save_password in {"s", "y", "sí", "si"}:
            password = getpass.getpass("Contraseña (oculta): ")
        proxy = input("Proxy (opcional host:puerto): ").strip() or None

        os.makedirs(SESSIONS_DIR, exist_ok=True)

        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO accounts (
                group_id, username, alias, password, proxy, status,
                session_data, last_activity, last_error
            ) VALUES (?, ?, ?, ?, ?, 'inestable', NULL, NULL, NULL)
            """,
            (group_id, username, alias or None, password, proxy),
        )
        account_id = cur.lastrowid
        conn.commit()

        session_file = os.path.join(SESSIONS_DIR, f"account_{account_id}.json")
        success, message = playwright_client.login_manual(username, session_file)

        status = "viva" if success else "inestable"
        last_activity = datetime.utcnow().isoformat(timespec="seconds") if success else None
        cur.execute(
            """
            UPDATE accounts
               SET status = ?, last_activity = ?, last_error = ?
             WHERE id = ?
            """,
            (
                status,
                last_activity,
                None if success else message,
                account_id,
            ),
        )
        conn.commit()
        conn.close()

        if success:
            print("Login exitoso. Cuenta marcada como viva.")
        else:
            print(f"No se pudo autenticar: {message}. Cuenta marcada como inestable.")

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

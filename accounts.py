"""
accounts.py
-----------------

This module defines ``AccountManager`` for managing LinkedIn accounts and
account groups. It provides functionality to create and select groups,
add accounts, update account statuses and list accounts. Actual LinkedIn
authentication is outside the scope of this CLI; instead, accounts are stored
in the local database with a status indicating whether they are usable.
"""

import getpass
import sqlite3
from typing import List, Tuple
from .db import get_connection


class AccountManager:
    """Manage LinkedIn accounts and account groups."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # Group management -----------------------------------------------------
    def list_groups(self) -> List[sqlite3.Row]:
        """Return a list of all account groups sorted by name."""
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM account_groups ORDER BY name")
        groups = cur.fetchall()
        conn.close()
        return groups

    def create_group(self, name: str) -> int:
        """Create a new account group and return its ID."""
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO account_groups (name) VALUES (?)", (name,))
        conn.commit()
        group_id = cur.lastrowid
        conn.close()
        return group_id

    def select_group(self) -> int:
        """Prompt the user to select an existing group or create one if none exist.

        Returns the selected group ID.
        """
        groups = self.list_groups()
        if not groups:
            print("No hay grupos de cuentas. Cree el primero.")
            while True:
                name = input("Nombre del nuevo grupo: ").strip()
                if name:
                    return self.create_group(name)
                print("Por favor, ingrese un nombre válido.")
        else:
            print("Seleccione un grupo:")
            for idx, grp in enumerate(groups, start=1):
                print(f"{idx}. {grp['name']}")
            print("0. Crear nuevo grupo")
            while True:
                try:
                    choice = int(input("Opción: "))
                except ValueError:
                    print("Ingrese un número válido.")
                    continue
                if choice == 0:
                    name = input("Nombre del nuevo grupo: ").strip()
                    if name:
                        return self.create_group(name)
                    print("Nombre inválido. Inténtelo de nuevo.")
                elif 1 <= choice <= len(groups):
                    return groups[choice - 1]["id"]
                else:
                    print("Selección fuera de rango.")

    # Account management ----------------------------------------------------
    def list_accounts(self, group_id: int) -> List[sqlite3.Row]:
        """Return a list of accounts within the given group."""
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM accounts WHERE group_id = ? ORDER BY username",
            (group_id,),
        )
        accounts = cur.fetchall()
        conn.close()
        return accounts

    def add_account(self, group_id: int) -> None:
        """Interactively prompt for account credentials and add it to the group.

        The password is requested using getpass to avoid echoing in the
        terminal. Session management is beyond the scope of this CLI; however,
        credentials can be stored for future login simulation or integration
        with automation tools.
        """
        username = input("Ingrese el email/usuario de la cuenta: ").strip()
        if not username:
            print("El nombre de usuario no puede estar vacío.")
            return
        password = getpass.getpass("Ingrese la contraseña (oculto): ")
        # In a real integration, here we would attempt a login using
        # Playwright/Selenium and obtain session cookies. For now we just
        # store the credentials and set the status to 'viva'.
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO accounts (group_id, username, password, status)"
            " VALUES (?, ?, ?, 'viva')",
            (group_id, username, password),
        )
        conn.commit()
        conn.close()
        print("Cuenta agregada correctamente y marcada como viva.")

    def update_account_status(self, account_id: int, new_status: str) -> None:
        """Update the status of an account."""
        if new_status not in {"viva", "inestable", "muerta"}:
            raise ValueError("Estado inválido")
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE accounts SET status = ? WHERE id = ?",
            (new_status, account_id),
        )
        conn.commit()
        conn.close()

    def account_status_menu(self, group_id: int) -> None:
        """Show the status of accounts and optionally allow changes."""
        accounts = self.list_accounts(group_id)
        if not accounts:
            print("No hay cuentas en este grupo.")
            return
        # Display accounts with indexes
        print("Cuentas en el grupo:")
        for idx, acc in enumerate(accounts, start=1):
            print(f"{idx}. {acc['username']} - Estado: {acc['status']}")
        print("0. Volver")
        while True:
            try:
                choice = int(input("Seleccione una cuenta para cambiar estado (0 para volver): "))
            except ValueError:
                print("Ingrese un número válido.")
                continue
            if choice == 0:
                return
            if 1 <= choice <= len(accounts):
                account = accounts[choice - 1]
                print(
                    "Seleccione el nuevo estado:\n"
                    "1. viva (activa)\n"
                    "2. inestable\n"
                    "3. muerta (baneada)"
                )
                status_choice = input("Estado: ")
                status_map = {"1": "viva", "2": "inestable", "3": "muerta"}
                new_status = status_map.get(status_choice)
                if new_status:
                    self.update_account_status(account["id"], new_status)
                    print(f"Estado de {account['username']} actualizado a {new_status}.")
                    # Refresh list after update
                    accounts = self.list_accounts(group_id)
                    for idx, acc in enumerate(accounts, start=1):
                        print(f"{idx}. {acc['username']} - Estado: {acc['status']}")
                    print("0. Volver")
                else:
                    print("Opción de estado inválida.")
            else:
                print("Selección fuera de rango.")

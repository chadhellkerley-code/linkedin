"""
autoresponder.py
-----------------------

This module implements a very simple autoresponder configuration for the CLI.
It allows the user to set an API key and prompt for generating replies, and
then activate a loop which periodically checks (simulated) incoming messages
and sends a response. Real integration with LinkedIn messaging APIs is not
provided; instead this module provides a placeholder implementation that
demonstrates how the interface would work.
"""

import random
import sqlite3
import time
from typing import List
from .db import get_connection


class AutoResponder:
    """Configure and run an autoresponder using AI prompts."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # Configuration --------------------------------------------------------
    def set_api_key(self) -> None:
        key = input("Ingrese la API key: ").strip()
        if not key:
            print("La API key no puede estar vacía.")
            return
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            ("api_key", key),
        )
        conn.commit()
        conn.close()
        print("API key guardada correctamente.")

    def set_prompt(self) -> None:
        print("Ingrese el prompt base para las respuestas del bot.")
        print("Termine la entrada con una línea vacía.")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        prompt = "\n".join(lines)
        if not prompt.strip():
            print("El prompt no puede estar vacío.")
            return
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            ("prompt", prompt),
        )
        conn.commit()
        conn.close()
        print("Prompt guardado correctamente.")

    def _get_config(self, key: str) -> str:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row["value"] if row else ""

    # Autoresponder loop ---------------------------------------------------
    def activate_bot(self) -> None:
        from .accounts import AccountManager
        account_manager = AccountManager(self.db_path)
        # Select accounts to monitor
        print("Seleccione el grupo de cuentas para el bot:")
        group_id = account_manager.select_group()
        accounts = [acc for acc in account_manager.list_accounts(group_id) if acc['status'] == 'viva']
        if not accounts:
            print("No hay cuentas activas en este grupo.")
            return
        # Select which accounts to use
        print("Cuentas disponibles para activar el bot:")
        for idx, acc in enumerate(accounts, start=1):
            print(f"{idx}. {acc['username']}")
        print("0. Usar todas")
        choice = input("Seleccione cuentas separadas por coma (o 0 para todas): ").strip()
        selected_accounts: List[sqlite3.Row] = []
        if choice == "0" or not choice:
            selected_accounts = accounts
        else:
            try:
                indexes = [int(x) for x in choice.split(',')]
                for idx in indexes:
                    if 1 <= idx <= len(accounts):
                        selected_accounts.append(accounts[idx - 1])
            except ValueError:
                print("Entrada inválida. Abortando activación.")
                return
        if not selected_accounts:
            print("No se seleccionaron cuentas.")
            return
        # Delay configuration
        try:
            delay_min = float(input("Delay mínimo entre respuestas (segundos): ").strip() or "10")
            delay_max = float(input("Delay máximo entre respuestas (segundos): ").strip() or "60")
            if delay_min < 0 or delay_max < delay_min:
                raise ValueError
        except ValueError:
            print("Delays inválidos.")
            return
        # Check configuration availability
        api_key = self._get_config("api_key")
        prompt = self._get_config("prompt")
        if not api_key or not prompt:
            print("Debe configurar la API key y el prompt antes de activar el bot.")
            return
        print(
            "\nEl bot se activará ahora. Presione Ctrl+C para detenerlo."
        )
        try:
            while True:
                # Simulation: fetch new messages and respond
                for acc in selected_accounts:
                    # In a real implementation we would check the LinkedIn inbox here.
                    # We simulate receiving a message with some probability.
                    if random.random() < 0.2:
                        sender_name = "Prospecto"  # Placeholder sender
                        received_msg = "¿Qué servicios ofreces?"  # Placeholder
                        # Build AI prompt (here we just echo for demonstration)
                        response = f"Respuesta automática a {sender_name}: Gracias por tu mensaje. Pronto te contactaremos."
                        print(
                            f"[Bot] {acc['username']} respondió a {sender_name}: {response}"
                        )
                # Wait before next loop
                delay = random.uniform(delay_min, delay_max)
                time.sleep(delay)
        except KeyboardInterrupt:
            print("\nBot detenido por el usuario.")

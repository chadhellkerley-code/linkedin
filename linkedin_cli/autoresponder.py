"""Autoresponder configuration and simulation."""

from __future__ import annotations

import random
import sqlite3
import time
from dataclasses import dataclass
from typing import List, Optional

try:  # pragma: no cover
    from .db import get_connection
except ImportError:  # pragma: no cover
    from db import get_connection


@dataclass
class BotConfig:
    api_key: str
    prompt: str


class AutoResponder:
    """Manage AI-based automatic replies."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # Configuration helpers ---------------------------------------------
    def _set_config(self, key: str, value: str) -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()

    def _get_config(self, key: str) -> str:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row["value"] if row else ""

    def set_api_key(self) -> None:
        key = input("Ingrese la API key de OpenAI: ").strip()
        if not key:
            print("La API key es obligatoria.")
            return
        self._set_config("api_key", key)
        print("API key guardada.")

    def set_prompt(self) -> None:
        print("Ingrese el prompt base. Línea vacía para finalizar.")
        lines: List[str] = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        prompt = "\n".join(lines).strip()
        if not prompt:
            print("El prompt no puede estar vacío.")
            return
        self._set_config("prompt", prompt)
        print("Prompt guardado.")

    # Bot activation ----------------------------------------------------
    def activate_bot(self) -> None:
        config = BotConfig(api_key=self._get_config("api_key"), prompt=self._get_config("prompt"))
        if not config.api_key or not config.prompt:
            print("Configure la API key y el prompt antes de activar el bot.")
            return
        try:  # pragma: no cover
            from .accounts import AccountManager  # type: ignore
        except ImportError:  # pragma: no cover
            from accounts import AccountManager  # type: ignore
        account_manager = AccountManager(self.db_path)
        print("Seleccione el grupo de cuentas que operará el bot:")
        group_id = account_manager.select_group()
        accounts = [acc for acc in account_manager.list_accounts(group_id) if acc["status"] == "viva"]
        if not accounts:
            print("No hay cuentas activas.")
            return
        print("Cuentas disponibles:")
        for idx, acc in enumerate(accounts, start=1):
            print(f"{idx}. {acc['alias'] or acc['username']}")
        print("0. Todas")
        choice = input("Seleccione cuentas separadas por coma (0 para todas): ").strip()
        selected: List[sqlite3.Row] = []
        if choice in {"0", ""}:
            selected = accounts
        else:
            try:
                indexes = [int(x) for x in choice.split(',')]
            except ValueError:
                print("Entrada inválida.")
                return
            for idx in indexes:
                if 1 <= idx <= len(accounts):
                    selected.append(accounts[idx - 1])
        if not selected:
            print("No se seleccionaron cuentas.")
            return
        try:
            delay_min = float(input("Delay mínimo entre revisiones (segundos): ").strip() or "20")
            delay_max = float(input("Delay máximo entre revisiones (segundos): ").strip() or "60")
            if delay_min < 0 or delay_max < delay_min:
                raise ValueError
        except ValueError:
            print("Delays inválidos.")
            return
        print("\nBot activado. Presione Ctrl+C para detenerlo.")
        try:
            while True:
                for account in selected:
                    incoming = self._simulate_incoming_messages(account)
                    for lead_name, message in incoming:
                        reply = self._craft_reply(config, message)
                        self._send_reply(account, lead_name, reply)
                time.sleep(random.uniform(delay_min, delay_max))
        except KeyboardInterrupt:
            print("\nBot detenido.")

    # Placeholder integrations -----------------------------------------
    def _simulate_incoming_messages(self, account: sqlite3.Row) -> List[tuple[str, str]]:
        # In a real implementation, fetch unread messages from LinkedIn.
        messages: List[tuple[str, str]] = []
        if random.random() < 0.2:
            messages.append(("Lead", "Hola, cuéntame más"))
        return messages

    def _craft_reply(self, config: BotConfig, message: str) -> str:
        # Placeholder for OpenAI call. Here we only echo to keep the CLI offline-friendly.
        base = config.prompt or "Gracias por tu mensaje"
        return f"{base}\n\nMensaje recibido: {message}"

    def _send_reply(self, account: sqlite3.Row, lead_name: str, reply: str) -> None:
        # Real implementation would send the message through LinkedIn automation.
        time.sleep(0.2)
        timestamp = time.strftime("%H:%M:%S")
        alias = account["alias"] or account["username"]
        print(f"[{timestamp}] Cuenta {alias} respondió a {lead_name} – OK")

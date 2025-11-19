"""
messages.py
-------------------

This module defines ``MessageSender`` which orchestrates bulk message
sending from LinkedIn accounts to leads. It prompts the user to select
account and lead groups, configure delays, choose or input message
templates and dispatch messages one by one. Actual delivery to LinkedIn
profiles is simulated via console output; however, the logic includes
delays and per-account limits to mimic real usage.
"""

import datetime
import random
import sqlite3
import time
from typing import List
from .db import get_connection


class MessageSender:
    """Send messages from multiple accounts to multiple leads with delays."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _get_accounts(self, group_id: int) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM accounts WHERE group_id = ? AND status = 'viva'",
            (group_id,),
        )
        accounts = cur.fetchall()
        conn.close()
        return accounts

    def _get_leads(self, group_id: int) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM leads WHERE group_id = ?",
            (group_id,),
        )
        leads = cur.fetchall()
        conn.close()
        return leads

    def _log_message(self, account_id: int, lead_id: int, status: str, error_message: str = "") -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO message_logs (timestamp, account_id, lead_id, status, error_message)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                datetime.datetime.now().isoformat(timespec="seconds"),
                account_id,
                lead_id,
                status,
                error_message,
            ),
        )
        conn.commit()
        conn.close()

    def _render_message(self, template: str, lead: sqlite3.Row) -> str:
        # Replace placeholders with lead data. Unavailable keys remain untouched.
        msg = template
        replacements = {
            "first_name": lead["first_name"] or "",
            "last_name": lead["last_name"] or "",
        }
        for key, value in replacements.items():
            msg = msg.replace(f"{{{key}}}", value)
        return msg

    def send_messages(self) -> None:
        """Interactive flow to send messages to leads."""
        # Select account group
        from .accounts import AccountManager  # local import to avoid circular
        from .leads import LeadManager
        account_manager = AccountManager(self.db_path)
        lead_manager = LeadManager(self.db_path)
        print("Seleccione grupo de cuentas para enviar:")
        acc_group = account_manager.select_group()
        accounts = self._get_accounts(acc_group)
        if not accounts:
            print("No hay cuentas activas (vivas) en este grupo. Agregue cuentas o cambie su estado a 'viva'.")
            return
        print("Seleccione grupo de leads destinatarios:")
        lead_group = lead_manager.select_group()
        leads = self._get_leads(lead_group)
        if not leads:
            print("No hay leads en este grupo.")
            return
        # Ask user for delays and limits
        try:
            delay_min = float(input("Delay mínimo entre mensajes (segundos): ").strip() or "5")
            delay_max = float(input("Delay máximo entre mensajes (segundos): ").strip() or "15")
            if delay_min < 0 or delay_max < delay_min:
                raise ValueError
        except ValueError:
            print("Delays inválidos. Asegúrese de que estén en formato numérico y que el máximo sea mayor o igual al mínimo.")
            return
        try:
            max_per_account = int(
                input("Máximo de mensajes por cuenta en este envío: ").strip() or "10"
            )
            if max_per_account <= 0:
                raise ValueError
        except ValueError:
            print("El número de mensajes por cuenta debe ser un entero positivo.")
            return
        # Ask for message template
        print(
            "\nIngrese la plantilla del mensaje. Puede usar {first_name} y {last_name} como placeholders.\n"
            "Termine la plantilla con una línea vacía."
        )
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        template = "\n".join(lines)
        if not template.strip():
            print("No ingresó una plantilla de mensaje.")
            return
        # Start sending
        lead_iter = iter(leads)
        total_sent = 0
        print("\nIniciando envío de mensajes...\n")
        for acc in accounts:
            sent_for_account = 0
            while sent_for_account < max_per_account:
                try:
                    lead = next(lead_iter)
                except StopIteration:
                    break  # No more leads
                # Compose message
                msg = self._render_message(template, lead)
                # Simulate sending (here we would automate browser actions)
                try:
                    # TODO: integrate with actual LinkedIn automation. For now we print.
                    print(
                        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Cuenta {acc['username']} → "
                        f"{lead['profile_url']} : enviado"
                    )
                    self._log_message(acc['id'], lead['id'], 'sent', '')
                except Exception as exc:
                    err_msg = str(exc)
                    print(
                        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Cuenta {acc['username']} → "
                        f"{lead['profile_url']} : ERROR {err_msg}"
                    )
                    self._log_message(acc['id'], lead['id'], 'error', err_msg)
                sent_for_account += 1
                total_sent += 1
                if delay_max > 0:
                    # Wait a random delay between min and max
                    delay = random.uniform(delay_min, delay_max)
                    time.sleep(delay)
            if sent_for_account >= max_per_account:
                print(f"→ Límite de {max_per_account} mensajes alcanzado para {acc['username']}")
            if total_sent >= len(leads):
                break
        print("\nEnvío finalizado.")

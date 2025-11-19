"""Message sending orchestration for the LinkedIn CLI."""

from __future__ import annotations

import datetime as dt
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
class SendContext:
    account: sqlite3.Row
    lead: sqlite3.Row
    rendered_message: str


class TemplateManager:
    """Simple helper to persist and choose message templates."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def list_templates(self) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM message_templates ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        return rows

    def ensure_default(self) -> None:
        if self.list_templates():
            return
        self.create_template("Default", "Hola {first_name}, un gusto saludarte.")

    def create_template(self, name: str, content: str) -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO message_templates (name, content) VALUES (?, ?)",
            (name, content),
        )
        conn.commit()
        conn.close()

    def select_template(self) -> Optional[sqlite3.Row]:
        self.ensure_default()
        templates = self.list_templates()
        while True:
            print("Seleccione una plantilla:")
            for idx, tpl in enumerate(templates, start=1):
                preview = tpl["content"].replace("\n", " ")
                if len(preview) > 50:
                    preview = preview[:47] + "..."
                print(f"{idx}. {tpl['name']} → {preview}")
            print("0. Crear nueva plantilla")
            choice = input("Opción: ").strip()
            if choice == "0":
                name = input("Nombre de la plantilla: ").strip()
                if not name:
                    print("Nombre inválido.")
                    continue
                print("Ingrese el contenido. Línea vacía para finalizar.")
                lines: List[str] = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                content = "\n".join(lines).strip()
                if not content:
                    print("El contenido no puede estar vacío.")
                    continue
                self.create_template(name, content)
                templates = self.list_templates()
                continue
            try:
                idx = int(choice)
            except ValueError:
                print("Ingrese un número válido.")
                continue
            if 1 <= idx <= len(templates):
                return templates[idx - 1]
            print("Selección fuera de rango.")


class MessageSender:
    """Send LinkedIn messages with human-like pacing and clean logs."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.templates = TemplateManager(db_path)

    # Internal helpers --------------------------------------------------
    def _active_accounts(self, group_id: int) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM accounts
            WHERE group_id = ?
              AND status = 'viva'
              AND (cooldown_until IS NULL OR cooldown_until <= ?)
            ORDER BY COALESCE(alias, username)
            """,
            (group_id, dt.datetime.utcnow().isoformat(timespec="seconds")),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def _leads(self, group_id: int) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM leads WHERE group_id = ? ORDER BY first_name, last_name",
            (group_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def _log_message(self, account_id: int, lead_id: int, status: str, error: str = "") -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO message_logs (timestamp, account_id, lead_id, status, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (dt.datetime.utcnow().isoformat(timespec="seconds"), account_id, lead_id, status, error),
        )
        conn.commit()
        conn.close()

    def _update_account_activity(self, account_id: int, success: bool, error: str = "") -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE accounts
               SET last_activity = ?,
                   last_message_at = CASE WHEN ? THEN ? ELSE last_message_at END,
                   last_error = ?,
                   status = CASE WHEN ? THEN status ELSE 'inestable' END
             WHERE id = ?
            """,
            (
                dt.datetime.utcnow().isoformat(timespec="seconds"),
                1 if success else 0,
                dt.datetime.utcnow().isoformat(timespec="seconds"),
                None if success else error,
                1 if success else 0,
                account_id,
            ),
        )
        conn.commit()
        conn.close()

    def _render(self, template: str, lead: sqlite3.Row) -> str:
        msg = template
        replacements = {
            "first_name": lead["first_name"] or "",
            "last_name": lead["last_name"] or "",
        }
        for key, value in replacements.items():
            msg = msg.replace(f"{{{key}}}", value)
        return msg

    def _dispatch(self, ctx: SendContext) -> None:
        # Placeholder for the real LinkedIn automation.
        # In this reference implementation we just simulate a network call.
        time.sleep(0.2)
        # Could add heuristics here (captcha, banned, etc.).

    # Public API -------------------------------------------------------
    def send_messages(self) -> None:
        try:  # pragma: no cover
            from .accounts import AccountManager  # type: ignore
            from .leads import LeadManager  # type: ignore
        except ImportError:  # pragma: no cover
            from accounts import AccountManager  # type: ignore
            from leads import LeadManager  # type: ignore

        account_manager = AccountManager(self.db_path)
        lead_manager = LeadManager(self.db_path)

        print("Seleccione el grupo de cuentas emisoras:")
        group_id = account_manager.select_group()
        accounts = self._active_accounts(group_id)
        if not accounts:
            print("No hay cuentas vivas disponibles (o están en cooldown).")
            return
        print("Seleccione el grupo de leads:")
        lead_group = lead_manager.select_group()
        leads = self._leads(lead_group)
        if not leads:
            print("No hay leads en este grupo.")
            return
        try:
            delay_min = float(input("Delay mínimo (segundos): ").strip() or "5")
            delay_max = float(input("Delay máximo (segundos): ").strip() or "15")
            if delay_min < 0 or delay_max < delay_min:
                raise ValueError
        except ValueError:
            print("Delays inválidos.")
            return
        try:
            per_account = int(input("Mensajes por cuenta: ").strip() or "10")
            if per_account <= 0:
                raise ValueError
        except ValueError:
            print("Debe ingresar un número entero positivo.")
            return
        template = self.templates.select_template()
        if not template:
            print("No se seleccionó plantilla.")
            return
        template_text = template["content"]

        print("\nIniciando envío controlado...\n")
        lead_iter = iter(leads)
        total_sent = 0
        while True:
            exhausted = True
            for account in accounts:
                sent_for_account = 0
                while sent_for_account < per_account:
                    try:
                        lead = next(lead_iter)
                    except StopIteration:
                        exhausted = True
                        break
                    exhausted = False
                    message = self._render(template_text, lead)
                    ctx = SendContext(account=account, lead=lead, rendered_message=message)
                    alias = account["alias"] or account["username"]
                    lead_name = (lead["first_name"] or "") + " " + (lead["last_name"] or "")
                    lead_name = lead_name.strip() or lead["profile_url"]
                    timestamp = dt.datetime.now().strftime("%H:%M:%S")
                    try:
                        self._dispatch(ctx)
                        self._log_message(account["id"], lead["id"], "sent")
                        self._update_account_activity(account["id"], True)
                        print(f"[{timestamp}] Cuenta {alias} → Lead {lead_name}: ENVIADO")
                    except Exception as exc:  # pragma: no cover - placeholder path
                        error = str(exc)
                        self._log_message(account["id"], lead["id"], "error", error)
                        self._update_account_activity(account["id"], False, error)
                        print(f"[{timestamp}] Cuenta {alias} → Lead {lead_name}: ERROR ({error})")
                        break
                    sent_for_account += 1
                    total_sent += 1
                    if delay_max > 0:
                        time.sleep(random.uniform(delay_min, delay_max))
                if exhausted:
                    break
            if exhausted:
                break
        print(f"\nProceso finalizado. Mensajes enviados: {total_sent}.")

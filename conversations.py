"""Placeholder module for future conversation management."""

from __future__ import annotations

from typing import List

try:  # pragma: no cover
    from .db import get_connection
except ImportError:  # pragma: no cover
    from db import get_connection


class ConversationManager:
    """Store prompts/rules for future handover workflows."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def manage_conversations(self) -> None:
        while True:
            print("\nGestión de conversaciones (placeholder):")
            print("1. Definir prompt/reglas")
            print("2. Ver reglas actuales")
            print("0. Volver")
            choice = input("Opción: ").strip()
            if choice == "1":
                self._set_rules()
            elif choice == "2":
                self._show_rules()
            elif choice == "0":
                return
            else:
                print("Opción inválida.")

    def _set_rules(self) -> None:
        print("Ingrese instrucciones para calificar leads y derivarlos. Línea vacía para finalizar.")
        lines: List[str] = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        rules = "\n".join(lines).strip()
        if not rules:
            print("No se guardó ninguna regla.")
            return
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('conversation_rules', ?)", (rules,))
        conn.commit()
        conn.close()
        print("Reglas guardadas.")

    def _show_rules(self) -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'conversation_rules'")
        row = cur.fetchone()
        conn.close()
        if not row:
            print("Aún no hay reglas cargadas.")
            return
        print("\nReglas actuales:\n----------------")
        print(row["value"])

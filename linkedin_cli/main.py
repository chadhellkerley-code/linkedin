"""
main.py
------------

Entry point for the LinkedIn messaging CLI. This file implements a simple
menu-driven interface that ties together account management, lead
management, message sending, autoresponder configuration and a placeholder
for conversation handling. The database schema is initialized on first run.
"""

import os
import sqlite3
from typing import Tuple

try:  # pragma: no cover
    from .db import init_db, get_connection
    from .accounts import AccountManager
    from .leads import LeadManager
    from .messages import MessageSender
    from .autoresponder import AutoResponder
    from .conversations import ConversationManager
except ImportError:  # pragma: no cover
    from db import init_db, get_connection
    from accounts import AccountManager
    from leads import LeadManager
    from messages import MessageSender
    from autoresponder import AutoResponder
    from conversations import ConversationManager


DB_FILENAME = "data.db"


def ensure_database() -> str:
    """Ensure the database exists and initialize it. Returns the path."""
    db_path = os.path.join(os.path.dirname(__file__), DB_FILENAME)
    # Create the database directory if needed
    init_db(db_path)
    return db_path


def get_counts(db_path: str) -> Tuple[int, int, int]:
    """Return counts of connected, active and banned accounts."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    # connected = total number of accounts
    cur.execute("SELECT COUNT(*) FROM accounts")
    total = cur.fetchone()[0]
    # active = status viva
    cur.execute("SELECT COUNT(*) FROM accounts WHERE status = 'viva'")
    active = cur.fetchone()[0]
    # banned = status muerta
    cur.execute("SELECT COUNT(*) FROM accounts WHERE status = 'muerta'")
    banned = cur.fetchone()[0]
    conn.close()
    return total, active, banned


def main() -> None:
    db_path = ensure_database()
    account_manager = AccountManager(db_path)
    lead_manager = LeadManager(db_path)
    message_sender = MessageSender(db_path)
    autoresponder = AutoResponder(db_path)
    conversation_manager = ConversationManager(db_path)
    while True:
        # Print header and counts
        total, active, banned = get_counts(db_path)
        print("\n==============================")
        print("Mensajería para LinkedIn")
        print("Herramienta de Mati Díaz")
        print("------------------------------")
        print(f"Cuentas conectadas: {total}")
        print(f"Cuentas activas: {active}")
        print(f"Cuentas baneadas: {banned}")
        print("------------------------------")
        print("Menú principal:")
        print("1. Gestionar cuentas")
        print("2. Gestionar leads")
        print("3. Enviar mensajes")
        print("4. Autoresponder")
        print("5. Gestión de conversaciones")
        print("0. Salir")
        choice = input("Seleccione una opción: ").strip()
        if choice == "1":
            group_id = account_manager.select_group()
            # Once group is selected show submenu
            while True:
                print("\nGestión de cuentas - opciones:")
                accounts = account_manager.list_accounts(group_id)
                if accounts:
                    print("Cuentas en el grupo:")
                    for acc in accounts:
                        print(f"- {acc['username']} (estado: {acc['status']})")
                else:
                    print("No hay cuentas en este grupo.")
                print("\n1. Agregar cuentas")
                print("2. Ver/cambiar estado de cuentas")
                print("0. Volver al menú principal")
                sub_choice = input("Seleccione una opción: ").strip()
                if sub_choice == "1":
                    account_manager.add_account(group_id)
                elif sub_choice == "2":
                    account_manager.account_status_menu(group_id)
                elif sub_choice == "0":
                    break
                else:
                    print("Opción inválida.")
        elif choice == "2":
            lead_group_id = lead_manager.select_group()
            lead_manager.manage_leads(lead_group_id)
        elif choice == "3":
            message_sender.send_messages()
        elif choice == "4":
            # Autoresponder menu
            while True:
                print("\nAutoresponder - opciones:")
                print("1. Configurar API key")
                print("2. Configurar prompt del bot")
                print("3. Activar bot")
                print("0. Volver al menú principal")
                sub = input("Seleccione una opción: ").strip()
                if sub == "1":
                    autoresponder.set_api_key()
                elif sub == "2":
                    autoresponder.set_prompt()
                elif sub == "3":
                    autoresponder.activate_bot()
                elif sub == "0":
                    break
                else:
                    print("Opción inválida.")
        elif choice == "5":
            conversation_manager.manage_conversations()
        elif choice == "0":
            print("Saliendo de la herramienta. ¡Hasta luego!")
            break
        else:
            print("Opción inválida.")


if __name__ == "__main__":
    main()

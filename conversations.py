"""
conversations.py
--------------------

Placeholder for future conversation management functionality. This module
currently defines a stub ``ConversationManager`` that simply prints
informational text. It is included to satisfy the menu structure and will be
expanded in later versions to support conversation qualification logic.
"""


class ConversationManager:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def manage_conversations(self) -> None:
        """Stub for conversation management."""
        print(
            "\nGestión de conversaciones aún no está implementado.\n"
            "Aquí se podrán definir reglas y prompts para calificar leads y "
            "notificar a un closer.\n"
        )

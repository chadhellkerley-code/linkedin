"""
leads.py
-------------

This module defines ``LeadManager`` for managing lead groups and individual
leads. It supports creating groups, adding leads manually or from CSV
files, listing leads and simple editing functionality. A lead record stores
basic information such as first name, last name, LinkedIn profile URL and
an optional note.
"""

import csv
import os
import sqlite3
from typing import List

try:  # pragma: no cover
    from .db import get_connection
except ImportError:  # pragma: no cover
    from db import get_connection


class LeadManager:
    """Manage lead groups and leads."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # Group management -----------------------------------------------------
    def list_groups(self) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM lead_groups ORDER BY name")
        groups = cur.fetchall()
        conn.close()
        return groups

    def create_group(self, name: str) -> int:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO lead_groups (name) VALUES (?)", (name,))
        conn.commit()
        group_id = cur.lastrowid
        conn.close()
        return group_id

    def select_group(self) -> int:
        groups = self.list_groups()
        if not groups:
            print("No hay grupos de leads. Cree el primero.")
            while True:
                name = input("Nombre del nuevo grupo de leads: ").strip()
                if name:
                    return self.create_group(name)
                print("Por favor, ingrese un nombre válido.")
        else:
            print("Seleccione un grupo de leads:")
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

    # Lead management ------------------------------------------------------
    def list_leads(self, group_id: int) -> List[sqlite3.Row]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM leads WHERE group_id = ? ORDER BY first_name, last_name",
            (group_id,),
        )
        leads = cur.fetchall()
        conn.close()
        return leads

    def add_lead_manual(self, group_id: int) -> None:
        print("Agregar lead manualmente.")
        first_name = input("Nombre: ").strip()
        last_name = input("Apellido: ").strip()
        profile_url = input("URL del perfil de LinkedIn: ").strip()
        note = input("Nota (opcional): ").strip()
        if not profile_url:
            print("La URL del perfil es obligatoria.")
            return
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO leads (group_id, first_name, last_name, profile_url, note)"
            " VALUES (?, ?, ?, ?, ?)",
            (group_id, first_name, last_name, profile_url, note),
        )
        conn.commit()
        conn.close()
        print("Lead agregado correctamente.")

    def add_leads_from_csv(self, group_id: int) -> None:
        path = input("Ruta del archivo CSV: ").strip()
        if not os.path.isfile(path):
            print("El archivo no existe.")
            return
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            required_fields = {"first_name", "last_name", "profile_url"}
            if not required_fields.issubset(reader.fieldnames or []):
                print("El CSV debe contener las columnas: first_name, last_name, profile_url")
                return
            conn = get_connection(self.db_path)
            cur = conn.cursor()
            count = 0
            for row in reader:
                first = row.get("first_name", "").strip()
                last = row.get("last_name", "").strip()
                url = row.get("profile_url", "").strip()
                note = row.get("note", "").strip() if row.get("note") is not None else ""
                if not url:
                    continue
                cur.execute(
                    "INSERT INTO leads (group_id, first_name, last_name, profile_url, note)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (group_id, first, last, url, note),
                )
                count += 1
            conn.commit()
            conn.close()
            print(f"Se importaron {count} leads desde el CSV.")

    def manage_leads(self, group_id: int) -> None:
        """Interactive submenu for managing leads inside a group."""
        while True:
            leads = self.list_leads(group_id)
            print("\nLeads en este grupo:")
            if not leads:
                print("  (ninguno)")
            else:
                for idx, lead in enumerate(leads, start=1):
                    name = f"{lead['first_name']} {lead['last_name']}".strip()
                    print(f"{idx}. {name} → {lead['profile_url']}")
            print("\nOpciones:")
            print("1. Agregar lead manualmente")
            print("2. Importar leads desde CSV")
            # Placeholder for future editing features
            print("0. Volver")
            choice = input("Seleccione una opción: ").strip()
            if choice == "1":
                self.add_lead_manual(group_id)
            elif choice == "2":
                self.add_leads_from_csv(group_id)
            elif choice == "0":
                break
            else:
                print("Opción inválida.")

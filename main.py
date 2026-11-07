import streamlit as st
import pandas as pd
import sqlite3

# --- اتصال محلي بـ SQLite (لا يحتاج لأي مكتبات خارجية معقدة) ---
def init_db():
    conn = sqlite3.connect('gholoul.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poutres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_poutre TEXT,
            type TEXT,
            etape TEXT,
            specialite_ouvriers TEXT,
            effectif INTEGER,
            statut TEXT,
            date TEXT
        );
    ''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

import os
import psycopg2
from psycopg2 import sql

def get_connection():
    # Render inyecta la variable de entorno DATABASE_URL automáticamente
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Este es un fallback para que funcione localmente si no tienes la variable
        raise Exception("La variable de entorno DATABASE_URL no está configurada.")

    # La URL de Render viene con el esquema 'postgres://', que necesita ser 'postgresql://'
    # para la librería psycopg2.
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    conn = psycopg2.connect(database_url)
    return conn


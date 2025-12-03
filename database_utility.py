"""
database_utility.py: Database Connection Management
Provides a thread-safe utility function to connect to the SQLite database.
The database initialization (schema creation and seeding) is now handled 
by the mcp_server.py file.
"""
import sqlite3
import os

DATABASE_FILE = "service_db.sqlite"

def get_db_connection():
    """
    Returns a thread-safe connection object to the service database.

    The connection is configured for thread safety (check_same_thread=False)
    and uses row_factory to enable dictionary-like access to query results.
    """
    db_conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    db_conn.row_factory = sqlite3.Row  # Enable dictionary-like row access (access columns by name)
    return db_conn


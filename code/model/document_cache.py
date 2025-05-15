import sqlite3

class DocumentCache:
    def __init__(self, db_path="document_cache.db"):
        self.db_path = db_path
        self._initialize()

    def _initialize(self):
        """Create the cache table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_cache (
                    doc_id TEXT PRIMARY KEY,
                    document_text TEXT
                )
            """)
            conn.commit()

    def retrieve_from_document_cache(self, key: str):
        """Retrieve document text by key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT document_text FROM document_cache WHERE doc_id = ?", (key,))
            row = cursor.fetchone()
            return None if row is None else row[0]

    def add_to_document_cache(self, key: str, value: str):
        """Add or update document text in the cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO document_cache (doc_id, document_text)
                VALUES (?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET document_text = excluded.document_text
            """, (key, value))
            conn.commit()
import oracledb
import config

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dsn=config.DSN,
            min=1,
            max=5,
            increment=1
        )
    return _pool

def get_connection():
    """Acquires a connection from the connection pool."""
    return get_pool().acquire()

def query_all(sql, params=None):
    """Executes a SELECT query and returns list of dictionaries with column names."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or {})
        columns = [col[0].lower() for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cursor.close()
        conn.close()

def query_one(sql, params=None):
    """Executes a SELECT query and returns a single row as a dictionary."""
    results = query_all(sql, params)
    return results[0] if results else None

def execute_dml(sql, params=None):
    """Executes an INSERT, UPDATE, or DELETE query and commits."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or {})
        conn.commit()
        return cursor.rowcount
    finally:
        cursor.close()
        conn.close()

def execute_procedure(proc_name, params):
    """Executes a PL/SQL stored procedure."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        result = cursor.callproc(proc_name, params)
        conn.commit()
        return result
    finally:
        cursor.close()
        conn.close()

def execute_function(func_name, return_type, params):
    """Executes a PL/SQL function."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        result = cursor.callfunc(func_name, return_type, params)
        return result
    finally:
        cursor.close()
        conn.close()

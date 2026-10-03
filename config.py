import os
import oracledb

# Configuration for Oracle 19c Database
# Using ORCLPDB pluggable database created for the project
DB_USER = os.getenv("DB_USER", "finance_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "finance123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "1521")
DB_SERVICE = os.getenv("DB_SERVICE", "orclpdb")

DSN = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
SECRET_KEY = os.getenv("SECRET_KEY", "dbms_finance_secret_key_2026")

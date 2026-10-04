import db, bcrypt
from datetime import datetime, timedelta

print("Updating password hashes and seeding demo accounts...")

# Standard bcrypt hash generator
def hash_pw(pw):
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

pw_user = hash_pw('password123')
pw_admin = hash_pw('admin123')

# 1. Update Passwords
db.execute_dml("UPDATE Users SET password_hash = :pw WHERE email = 'harshith@example.com'", {'pw': pw_user})
db.execute_dml("UPDATE Users SET password_hash = :pw WHERE email = 'manideep@example.com'", {'pw': pw_user})
db.execute_dml("UPDATE Users SET password_hash = :pw WHERE email = 'rishvik@example.com'", {'pw': pw_user})
db.execute_dml("UPDATE Users SET password_hash = :pw WHERE email = 'divya@gmail.com'", {'pw': pw_user})
db.execute_dml("UPDATE Users SET password_hash = :pw WHERE email = 'admin@fintrack.com'", {'pw': pw_admin})

# 2. Seed realistic data for Manideep (User 2)
# Salary: 65,000, Accounts: Savings (45,000), Current (20,000)
db.execute_dml("UPDATE Users SET monthly_salary = 65000.00 WHERE user_id = 2")
m_acc = db.query_one("SELECT account_id FROM Accounts WHERE user_id = 2 ORDER BY account_id FETCH FIRST 1 ROWS ONLY")
if m_acc:
    m_aid = m_acc['account_id']
    # Clear and set initial balance
    db.execute_dml("UPDATE Accounts SET balance = 45200.00 WHERE account_id = :aid", {'aid': m_aid})
    
    # Add second account if not exists
    acc_cnt = db.query_one("SELECT count(*) as cnt FROM Accounts WHERE user_id = 2")
    if acc_cnt['cnt'] < 2:
        db.execute_dml("INSERT INTO Accounts (user_id, account_type, balance, status) VALUES (2, 'Current', 20000.00, 'Active')")
        
    # Seed Budgets for Manideep for current month
    cur_month = datetime.now().strftime('%Y-%m')
    for cat_id, limit_amt in [(1, 20000), (2, 9000), (3, 5000), (4, 4000), (5, 4000), (6, 3500), (7, 3000)]:
        db.execute_dml("""
            MERGE INTO Budgets b
            USING (SELECT 2 AS user_id, :cat_id AS category_id, :month AS month, :lim AS limit_amount FROM DUAL) src
            ON (b.user_id = src.user_id AND b.category_id = src.category_id AND b.month = src.month)
            WHEN MATCHED THEN UPDATE SET b.limit_amount = src.limit_amount
            WHEN NOT MATCHED THEN INSERT (user_id, category_id, month, limit_amount) VALUES (src.user_id, src.category_id, src.month, src.limit_amount)
        """, {'cat_id': cat_id, 'month': cur_month, 'lim': limit_amt})

# 3. Seed realistic data for Rishvik (User 3)
# Salary: 72,000, Accounts: Savings (58,000), Wallet (14,000)
db.execute_dml("UPDATE Users SET monthly_salary = 72000.00 WHERE user_id = 3")
r_acc = db.query_one("SELECT account_id FROM Accounts WHERE user_id = 3 ORDER BY account_id FETCH FIRST 1 ROWS ONLY")
if r_acc:
    r_aid = r_acc['account_id']
    db.execute_dml("UPDATE Accounts SET balance = 58400.00 WHERE account_id = :aid", {'aid': r_aid})
    
    acc_cnt = db.query_one("SELECT count(*) as cnt FROM Accounts WHERE user_id = 3")
    if acc_cnt['cnt'] < 2:
        db.execute_dml("INSERT INTO Accounts (user_id, account_type, balance, status) VALUES (3, 'Wallet', 14000.00, 'Active')")

    cur_month = datetime.now().strftime('%Y-%m')
    for cat_id, limit_amt in [(1, 22000), (2, 10000), (3, 6000), (4, 4500), (5, 4500), (6, 4000), (7, 3500)]:
        db.execute_dml("""
            MERGE INTO Budgets b
            USING (SELECT 3 AS user_id, :cat_id AS category_id, :month AS month, :lim AS limit_amount FROM DUAL) src
            ON (b.user_id = src.user_id AND b.category_id = src.category_id AND b.month = src.month)
            WHEN MATCHED THEN UPDATE SET b.limit_amount = src.limit_amount
            WHEN NOT MATCHED THEN INSERT (user_id, category_id, month, limit_amount) VALUES (src.user_id, src.category_id, src.month, src.limit_amount)
        """, {'cat_id': cat_id, 'month': cur_month, 'lim': limit_amt})

# 4. Seed realistic data for K. V. Divya (User 83 - Advisor)
cur_month = datetime.now().strftime('%Y-%m')
for cat_id, limit_amt in [(1, 80000), (2, 35000), (3, 20000), (4, 15000), (5, 15000), (6, 12000), (7, 10000)]:
    db.execute_dml("""
        MERGE INTO Budgets b
        USING (SELECT 83 AS user_id, :cat_id AS category_id, :month AS month, :lim AS limit_amount FROM DUAL) src
        ON (b.user_id = src.user_id AND b.category_id = src.category_id AND b.month = src.month)
        WHEN MATCHED THEN UPDATE SET b.limit_amount = src.limit_amount
        WHEN NOT MATCHED THEN INSERT (user_id, category_id, month, limit_amount) VALUES (src.user_id, src.category_id, src.month, src.limit_amount)
    """, {'cat_id': cat_id, 'month': cur_month, 'lim': limit_amt})

print("Demo accounts updated successfully!")

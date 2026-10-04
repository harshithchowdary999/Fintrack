import db, bcrypt
from datetime import datetime, timedelta

print("=" * 65)
print("  RE-SEEDING CLEAN, REALISTIC DEMO DATA FOR ALL USERS")
print("=" * 65)

def hash_pw(pw):
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

pw_user = hash_pw('password123')
pw_admin = hash_pw('admin123')

# 1. Clean existing records safely
db.execute_dml("DELETE FROM Alerts")
db.execute_dml("DELETE FROM Predictions")
db.execute_dml("DELETE FROM RecurringPayments")
db.execute_dml("DELETE FROM Budgets")
db.execute_dml("DELETE FROM Transactions")
db.execute_dml("DELETE FROM Accounts")
db.execute_dml("DELETE FROM Users")

# 2. Insert Clean Users
# Harshith (User 1)
db.execute_dml("""
    INSERT INTO Users (user_id, name, email, password_hash, role, monthly_salary)
    VALUES (1, 'Harshith K', 'harshith@example.com', :pw, 'USER', 75000.00)
""", {'pw': pw_user})

# Manideep (User 2)
db.execute_dml("""
    INSERT INTO Users (user_id, name, email, password_hash, role, monthly_salary)
    VALUES (2, 'Manideep P', 'manideep@example.com', :pw, 'USER', 65000.00)
""", {'pw': pw_user})

# Rishvik (User 3)
db.execute_dml("""
    INSERT INTO Users (user_id, name, email, password_hash, role, monthly_salary)
    VALUES (3, 'Rishvik K', 'rishvik@example.com', :pw, 'USER', 70000.00)
""", {'pw': pw_user})

# System Administrator (User 4)
db.execute_dml("""
    INSERT INTO Users (user_id, name, email, password_hash, role, monthly_salary)
    VALUES (4, 'System Administrator', 'admin@fintrack.com', :pw, 'ADMIN', 0.00)
""", {'pw': pw_admin})

# Advisor Divya K V (User 5)
db.execute_dml("""
    INSERT INTO Users (user_id, name, email, password_hash, role, monthly_salary)
    VALUES (5, 'Divya K V', 'divya@gmail.com', :pw, 'USER', 120000.00)
""", {'pw': pw_user})

# 3. Create Clean Accounts (Balances start at 0.00, updated by transaction trigger)
accounts_data = [
    # Harshith
    (1, 1, 'Savings', 'Active', '2026-06-01'),
    (2, 1, 'Current', 'Active', '2026-06-01'),
    (3, 1, 'Wallet', 'Active', '2026-06-01'),
    # Manideep
    (4, 2, 'Savings', 'Active', '2026-06-01'),
    (5, 2, 'Current', 'Active', '2026-06-01'),
    # Rishvik
    (6, 3, 'Savings', 'Active', '2026-06-01'),
    (7, 3, 'Wallet', 'Active', '2026-06-01'),
    # Admin
    (8, 4, 'Savings', 'Active', '2026-06-01'),
    # Divya K V
    (9, 5, 'Savings', 'Active', '2026-06-01'),
    (10, 5, 'Current', 'Active', '2026-06-01'),
]

for aid, uid, atype, astatus, dt in accounts_data:
    db.execute_dml("""
        INSERT INTO Accounts (account_id, user_id, account_type, balance, status, opened_at)
        VALUES (:1, :2, :3, 0.00, :4, TO_DATE(:5, 'YYYY-MM-DD'))
    """, [aid, uid, atype, astatus, dt])

# Helper function to add transaction (Trigger automatically adjusts balance!)
def add_txn(aid, cat_id, amt, t_type, dt_str, vendor, desc):
    db.execute_dml("""
        INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
        VALUES (:1, :2, :3, :4, TO_DATE(:5, 'YYYY-MM-DD HH24:MI:SS'), :6, :7)
    """, [aid, cat_id, amt, t_type, dt_str, vendor, desc])

# 4. Seed Historical & October Transactions for Harshith (User 1)
# July Salary & Expenses
add_txn(1, 1, 75000, 'Credit', '2026-07-01 09:00:00', 'Google LLC', 'July Monthly Salary')
add_txn(1, 6, 20000, 'Debit',  '2026-07-02 10:30:00', 'Prestige Housing', 'Apartment Rent')
add_txn(1, 4, 6200,  'Debit',  '2026-07-05 18:45:00', 'Reliance Fresh', 'Monthly Groceries')
add_txn(1, 5, 3100,  'Debit',  '2026-07-12 20:15:00', 'Barbeque Nation', 'Team Lunch')
add_txn(1, 7, 2400,  'Debit',  '2026-07-15 14:00:00', 'BESCOM', 'Electricity Bill')
add_txn(1, 8, 1800,  'Debit',  '2026-07-20 08:30:00', 'Indian Oil', 'Fuel Refill')
add_txn(1, 9, 1500,  'Debit',  '2026-07-25 19:30:00', 'PVR Cinemas', 'Movie & Snacks')

# August Salary & Expenses
add_txn(1, 1, 75000, 'Credit', '2026-08-01 09:00:00', 'Google LLC', 'August Monthly Salary')
add_txn(1, 6, 20000, 'Debit',  '2026-08-02 10:30:00', 'Prestige Housing', 'Apartment Rent')
add_txn(1, 4, 6800,  'Debit',  '2026-08-06 17:30:00', 'Nature Basket', 'Groceries & Fruits')
add_txn(1, 5, 3900,  'Debit',  '2026-08-14 21:00:00', 'Mainland China', 'Family Dinner')
add_txn(1, 7, 2600,  'Debit',  '2026-08-16 11:20:00', 'BESCOM', 'Electricity & Water')
add_txn(1, 8, 2100,  'Debit',  '2026-08-22 09:15:00', 'Uber', 'City Rides')
add_txn(1, 9, 1900,  'Debit',  '2026-08-28 18:00:00', 'BookMyShow', 'Concert Pass')

# September Salary & Freelance & Expenses
add_txn(1, 1, 75000, 'Credit', '2026-09-01 09:00:00', 'Google LLC', 'September Monthly Salary')
add_txn(2, 2, 25000, 'Credit', '2026-09-15 15:00:00', 'Upwork Client', 'Freelance Mobile App')
add_txn(1, 6, 20000, 'Debit',  '2026-09-02 10:30:00', 'Prestige Housing', 'Apartment Rent')
add_txn(1, 4, 7100,  'Debit',  '2026-09-07 19:10:00', 'BigBasket', 'Monthly Groceries')
add_txn(1, 5, 4200,  'Debit',  '2026-09-15 20:30:00', 'Swiggy Gourmet', 'Food Delivery')
add_txn(1, 7, 2700,  'Debit',  '2026-09-18 12:40:00', 'BESCOM', 'Power Utility')
add_txn(1, 8, 2200,  'Debit',  '2026-09-24 16:20:00', 'Shell Fuel', 'Petrol Refill')
add_txn(1, 9, 2100,  'Debit',  '2026-09-29 20:00:00', 'Gaming Arena', 'PlayStation Hub')

# October 2026 (Current Active Month)
add_txn(1, 1, 75000, 'Credit', '2026-10-01 09:00:00', 'Google LLC', 'October Monthly Salary')
add_txn(3, 1, 5000,  'Credit', '2026-10-01 10:00:00', 'Harshith K', 'Wallet Fund Transfer')
add_txn(1, 6, 20000, 'Debit',  '2026-10-02 10:30:00', 'Prestige Housing', 'Apartment Rent October')
add_txn(1, 4, 4500,  'Debit',  '2026-10-03 16:30:00', 'Supermarket DMart', 'Weekly Groceries')
add_txn(1, 5, 1850,  'Debit',  '2026-10-04 19:45:00', 'Starbucks Coffee', 'Coffee & Sandwiches')
add_txn(3, 8, 350,   'Debit',  '2026-10-04 14:15:00', 'Namma Metro', 'Metro SmartCard')

# 5. Seed Manideep (User 2)
add_txn(4, 1, 65000, 'Credit', '2026-10-01 09:00:00', 'Microsoft', 'October Monthly Salary')
add_txn(5, 2, 20000, 'Credit', '2026-10-02 14:00:00', 'Client Retainer', 'Consulting Fee')
add_txn(4, 6, 18000, 'Debit',  '2026-10-02 11:00:00', 'Greenview Villa', 'Monthly Rent')
add_txn(4, 4, 3800,  'Debit',  '2026-10-03 17:00:00', 'Spar Hypermarket', 'Groceries & Household')
add_txn(4, 7, 1900,  'Debit',  '2026-10-04 12:00:00', 'Jio Fiber', 'Broadband & Landline')

# 6. Seed Rishvik (User 3)
add_txn(6, 1, 70000, 'Credit', '2026-10-01 09:00:00', 'Amazon India', 'October Monthly Salary')
add_txn(7, 1, 10000, 'Credit', '2026-10-01 12:00:00', 'Rishvik K', 'Wallet Loading')
add_txn(6, 6, 19000, 'Debit',  '2026-10-02 10:00:00', 'Palm Heights', 'Rent Payment')
add_txn(6, 4, 4200,  'Debit',  '2026-10-03 18:30:00', 'Metro Cash & Carry', 'Monthly Food Stock')
add_txn(7, 5, 1250,  'Debit',  '2026-10-04 20:00:00', 'Zomato', 'Weekend Dinner')

# 7. Seed Advisor Divya K V (User 5)
add_txn(9, 1, 120000, 'Credit', '2026-10-01 09:00:00', 'Amrita University', 'Faculty Monthly Salary')
add_txn(10, 3, 30000, 'Credit', '2026-10-02 11:00:00', 'Mutual Funds', 'Quarterly Dividend')
add_txn(9, 6, 30000,  'Debit',  '2026-10-02 10:00:00', 'Sobha Developers', 'Residence Maintenance & Rent')
add_txn(9, 4, 8500,   'Debit',  '2026-10-03 16:00:00', 'Organic World', 'Monthly Gourmet Groceries')
add_txn(9, 10, 4500,  'Debit',  '2026-10-04 15:30:00', 'Apollo Pharmacy', 'Healthcare & Wellness')

# 8. Seed Smart Budgets for October 2026 for all users
def set_budget(uid, cat_id, lim):
    db.execute_dml("""
        MERGE INTO Budgets b
        USING (SELECT :1 AS user_id, :2 AS category_id, '2026-10' AS month, :3 AS limit_amount FROM DUAL) src
        ON (b.user_id = src.user_id AND b.category_id = src.category_id AND b.month = src.month)
        WHEN MATCHED THEN UPDATE SET b.limit_amount = src.limit_amount
        WHEN NOT MATCHED THEN INSERT (user_id, category_id, month, limit_amount) VALUES (src.user_id, src.category_id, src.month, src.limit_amount)
    """, [uid, cat_id, lim])

# Harshith (50/30/20 standard)
set_budget(1, 6, 21000) # Rent
set_budget(1, 4, 10500) # Groceries
set_budget(1, 5, 6000)  # Food & Dining
set_budget(1, 7, 4500)  # Utilities
set_budget(1, 8, 4500)  # Transport
set_budget(1, 9, 4500)  # Entertainment
set_budget(1, 12, 3500) # Shopping
set_budget(1, 11, 2000) # Subscriptions
set_budget(1, 10, 3000) # Healthcare

# Manideep
set_budget(2, 6, 18000)
set_budget(2, 4, 9000)
set_budget(2, 5, 5000)
set_budget(2, 7, 4000)
set_budget(2, 8, 4000)
set_budget(2, 9, 3500)
set_budget(2, 11, 1500)

# Rishvik
set_budget(3, 6, 20000)
set_budget(3, 4, 9500)
set_budget(3, 5, 5500)
set_budget(3, 7, 4200)
set_budget(3, 8, 4200)
set_budget(3, 9, 3800)
set_budget(3, 11, 1800)

# Divya K V
set_budget(5, 6, 32000)
set_budget(5, 4, 15000)
set_budget(5, 5, 9000)
set_budget(5, 7, 7000)
set_budget(5, 8, 6000)
set_budget(5, 9, 6000)
set_budget(5, 10, 6000)
set_budget(5, 12, 5000)

# 9. Seed Scheduled Recurring Payments (EMIs, Subscriptions)
db.execute_dml("""
    INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
    VALUES (1, 11, 699.00, 'Monthly', DATE '2026-10-15')
""")
db.execute_dml("""
    INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
    VALUES (1, 7, 2500.00, 'Monthly', DATE '2026-10-18')
""")
db.execute_dml("""
    INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
    VALUES (4, 11, 499.00, 'Monthly', DATE '2026-10-12')
""")
db.execute_dml("""
    INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
    VALUES (6, 11, 599.00, 'Monthly', DATE '2026-10-14')
""")

print("Successfully seeded clean, balanced demo data for all users!")

import sys
import app, db, oracledb

print("=" * 60)
print("  FINTRACK SYSTEM INTEGRITY & FEATURE VERIFICATION")
print("=" * 60)

print("\n--- 1. ORACLE DATABASE OBJECTS AUDIT ---")
tables = db.query_all("SELECT table_name FROM user_tables ORDER BY table_name")
print(f"Tables ({len(tables)}): {[t['table_name'] for t in tables]}")

procs = db.query_all("""
    SELECT object_name, object_type, status 
    FROM user_objects 
    WHERE object_type IN ('PROCEDURE', 'FUNCTION', 'TRIGGER', 'VIEW') 
    ORDER BY object_type, object_name
""")
for p in procs:
    print(f"  {p['object_type']:10} | {p['object_name']:32} | Status: {p['status']}")

print("\n--- 2. END-TO-END WORKFLOW & ROUTE AUDIT ---")
client = app.app.test_client()

passed = 0
failed = 0

def assert_test(name, condition, details=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} - {details}")
        failed += 1

# Setup session for Harshith (User 1)
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['user_name'] = 'Harshith K'
    sess['user_email'] = 'harshith@example.com'
    sess['user_role'] = 'USER'

# 1. GET /setup
res = client.get('/setup')
assert_test("GET /setup (Setup Wizard)", res.status_code == 200 and "Save Plan & Launch Dashboard" in res.get_data(as_text=True))

# 2. POST /setup (Save Plan & Launch Dashboard)
categories = db.query_all("SELECT category_id FROM Categories WHERE type = 'Expense'")
acc = db.query_one("SELECT account_id, balance FROM Accounts WHERE user_id = 1 AND status = 'Active' FETCH FIRST 1 ROWS ONLY")
old_bal = float(acc['balance'])

setup_payload = {
    'salary': '65000',
    'employer': 'Amrita Tech Corp',
    'account_id': str(acc['account_id']),
    'deposit_now': 'on'
}
for c in categories:
    setup_payload[f"budget_{c['category_id']}"] = '3500'

res = client.post('/setup', data=setup_payload, follow_redirects=True)
assert_test("POST /setup (Save Plan & Launch Dashboard)", res.status_code == 200 and "rebalanced successfully" in res.get_data(as_text=True))

# Verify balance increased by salary deposit trigger
acc_after = db.query_one("SELECT balance FROM Accounts WHERE account_id = :aid", {'aid': acc['account_id']})
assert_test("Oracle Trigger trg_update_account_balance on Salary Deposit", float(acc_after['balance']) == old_bal + 65000.0)

# Verify Users monthly_salary updated
u = db.query_one("SELECT monthly_salary FROM Users WHERE user_id = 1")
assert_test("Users.monthly_salary updated in Oracle", float(u['monthly_salary']) == 65000.0)

# 3. GET / (Dashboard)
res = client.get('/')
assert_test("GET / (Dashboard Overview & Cycle)", res.status_code == 200 and "Financial Cycle" in res.get_data(as_text=True))

# 4. POST /reduce-salary (Austerity Stored Procedure)
res = client.post('/reduce-salary', data={
    'new_salary': '40000',
    'reduction_reason': 'Economic Salary Downscale Test',
    'strategy': 'LEAN_70_20_10'
}, follow_redirects=True)
assert_test("POST /reduce-salary (PL/SQL handle_salary_reduction)", res.status_code == 200 and "Salary reduction successfully applied" in res.get_data(as_text=True))

# 5. GET /accounts
res = client.get('/accounts')
assert_test("GET /accounts", res.status_code == 200 and "Savings" in res.get_data(as_text=True))

# 6. POST /accounts/create
res = client.post('/accounts/create', data={'account_type': 'Wallet', 'initial_deposit': '500.00'}, follow_redirects=True)
assert_test("POST /accounts/create", res.status_code == 200)

# 7. GET /transactions
res = client.get('/transactions')
assert_test("GET /transactions (Ledger)", res.status_code == 200)

# 8. POST /transactions/create
res = client.post('/transactions/create', data={
    'account_id': str(acc['account_id']),
    'category_id': '2', # Groceries
    'amount': '250.00',
    'txn_type': 'Debit',
    'vendor': 'Reliance Smart',
    'description': 'Weekly Fruits'
}, follow_redirects=True)
assert_test("POST /transactions/create", res.status_code == 200)

# 9. GET /transactions/export
res = client.get('/transactions/export')
assert_test("GET /transactions/export (CSV Download)", res.status_code == 200 and 'text/csv' in res.headers.get('Content-Type', ''))

# 10. GET /budgets
res = client.get('/budgets')
assert_test("GET /budgets", res.status_code == 200)

# 11. GET /recurring
res = client.get('/recurring')
assert_test("GET /recurring", res.status_code == 200)

# 12. GET /predictions
res = client.get('/predictions')
assert_test("GET /predictions", res.status_code == 200)

# 13. POST /predictions/generate
res = client.post('/predictions/generate', follow_redirects=True)
assert_test("POST /predictions/generate (Moving Avg Procedure)", res.status_code == 200)

# 14. GET /transfer
res = client.get('/transfer')
assert_test("GET /transfer", res.status_code == 200)

# 15. Admin Portal with ADMIN user
with client.session_transaction() as sess:
    sess['user_id'] = 4
    sess['user_name'] = 'System Administrator'
    sess['user_email'] = 'admin@fintrack.com'
    sess['user_role'] = 'ADMIN'

res = client.get('/admin')
assert_test("GET /admin (Admin Portal)", res.status_code == 200 and "Admin" in res.get_data(as_text=True))

print("\n" + "=" * 60)
print(f"  AUDIT RESULT: {passed} PASSED, {failed} FAILED")
print("=" * 60)

if failed > 0:
    sys.exit(1)

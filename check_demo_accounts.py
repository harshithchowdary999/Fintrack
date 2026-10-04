import db, bcrypt
import requests

print("=" * 65)
print("       FINTRACK DEMO ACCOUNTS AUDIT & LOGIN TEST")
print("=" * 65)

users = db.query_all('SELECT user_id, name, email, role, monthly_salary, password_hash FROM Users ORDER BY user_id')

all_passwords = ['password123', 'admin123', 'finance123', 'divya123', 'admin', 'password', '123456']

# Also test login via HTTP
base_url = 'http://127.0.0.1:5000'

for u in users:
    found_pwd = None
    for try_pwd in all_passwords:
        try:
            if bcrypt.checkpw(try_pwd.encode('utf-8'), u['password_hash'].encode('utf-8')):
                found_pwd = try_pwd
                break
        except Exception:
            pass
            
    accs = db.query_all('SELECT account_id, account_type, balance, status FROM Accounts WHERE user_id = :usr_id ORDER BY account_id', {'usr_id': u['user_id']})
    txns = db.query_one('SELECT count(*) as cnt FROM Transactions t JOIN Accounts a ON t.account_id = a.account_id WHERE a.user_id = :usr_id', {'usr_id': u['user_id']})
    budgets = db.query_one('SELECT count(*) as cnt FROM Budgets WHERE user_id = :usr_id', {'usr_id': u['user_id']})
    alerts = db.query_one('SELECT count(*) as cnt FROM Alerts WHERE user_id = :usr_id', {'usr_id': u['user_id']})
    
    # Test HTTP login
    login_success = False
    dest_url = None
    if found_pwd:
        s = requests.Session()
        res = s.post(f"{base_url}/login", data={'email': u['email'], 'password': found_pwd}, allow_redirects=True)
        login_success = (res.status_code == 200 and '/login' not in res.url)
        dest_url = res.url
        
    print(f"\n[USER #{u['user_id']}] {u['name']} (Role: {u['role']})")
    print(f"  - Email: {u['email']}")
    print(f"  - Password: '{found_pwd}' (HTTP Login: {'SUCCESS -> ' + str(dest_url) if login_success else 'FAILED'})")
    print(f"  - Monthly Salary: Rs. {u['monthly_salary']:,.2f}")
    print(f"  - Accounts ({len(accs)}):")
    for a in accs:
        print(f"      * A/C #{a['account_id']}: {a['account_type']} | Balance: Rs. {a['balance']:,.2f} | Status: {a['status']}")
    print(f"  - Stats: {txns['cnt']} Transactions | {budgets['cnt']} Budgets | {alerts['cnt']} Alerts")

print("\n" + "=" * 65)

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
import bcrypt
import oracledb
import config
from datetime import datetime
import db
import csv
import io
import calendar

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Utility decorator / helper for login check
def get_current_user():
    if 'user_id' not in session:
        return None
    return {
        'id': session['user_id'],
        'name': session['user_name'],
        'email': session['user_email'],
        'role': session.get('user_role', 'USER')
    }

def mask_email(email):
    """Masks email for privacy compliance (e.g. h******h@example.com)."""
    if not email or '@' not in email:
        return '***@***.***'
    local_part, domain = email.split('@', 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + '***'
    else:
        masked_local = local_part[0] + ('*' * (len(local_part) - 2)) + local_part[-1]
    return f"{masked_local}@{domain}"

def mask_name(name):
    """Masks personal full name (e.g. H******h K)."""
    if not name:
        return '***'
    parts = name.split()
    masked_parts = []
    for p in parts:
        if len(p) <= 2:
            masked_parts.append(p[0] + '*')
        else:
            masked_parts.append(p[0] + ('*' * (len(p) - 2)) + p[-1])
    return ' '.join(masked_parts)

def get_monthly_cycle_data(user_id, month=None):
    """Calculates comprehensive financial cycle metrics, burn rate, and billing schedule for a given month."""
    now = datetime.now()
    if not month:
        month = now.strftime('%Y-%m')

    try:
        year, month_num = map(int, month.split('-'))
    except Exception:
        year, month_num = now.year, now.month
        month = now.strftime('%Y-%m')

    _, total_days = calendar.monthrange(year, month_num)
    is_current_month = (month == now.strftime('%Y-%m'))

    if is_current_month:
        current_day = now.day
        days_remaining = max(0, total_days - current_day)
    elif month < now.strftime('%Y-%m'):
        current_day = total_days
        days_remaining = 0
    else:
        current_day = 1
        days_remaining = total_days - 1

    cycle_progress_percent = round((current_day / total_days) * 100, 1)

    # Inflow (Credits)
    inc_row = db.query_one("""
        SELECT NVL(SUM(t.amount), 0) AS inflow
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        WHERE a.user_id = :usr_id AND t.txn_type = 'Credit' AND TO_CHAR(t.txn_date, 'YYYY-MM') = :m
    """, {'usr_id': user_id, 'm': month})
    cycle_inflow = inc_row['inflow'] if inc_row else 0.0

    # Outflow (Debits)
    exp_row = db.query_one("""
        SELECT NVL(SUM(t.amount), 0) AS outflow
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        WHERE a.user_id = :usr_id AND t.txn_type = 'Debit' AND TO_CHAR(t.txn_date, 'YYYY-MM') = :m
    """, {'usr_id': user_id, 'm': month})
    cycle_outflow = exp_row['outflow'] if exp_row else 0.0

    cycle_net_savings = cycle_inflow - cycle_outflow
    savings_rate = round((cycle_net_savings / cycle_inflow) * 100, 1) if cycle_inflow > 0 else 0.0

    # Budget limit
    b_row = db.query_one("""
        SELECT NVL(SUM(limit_amount), 0) AS total_lim
        FROM Budgets
        WHERE user_id = :usr_id AND month = :m
    """, {'usr_id': user_id, 'm': month})
    total_budget = b_row['total_lim'] if b_row else 0.0
    remaining_budget = max(0.0, total_budget - cycle_outflow)

    # Safe Daily Allowance & Burn Rate
    if days_remaining > 0:
        if total_budget > 0:
            safe_daily_allowance = round(remaining_budget / days_remaining, 2)
        else:
            safe_daily_allowance = round(max(0.0, cycle_net_savings) / days_remaining, 2)
    else:
        safe_daily_allowance = 0.0

    actual_daily_pace = round(cycle_outflow / max(1, current_day), 2)

    if total_budget > 0 and cycle_outflow > total_budget:
        burn_status = 'Over Budget'
    elif total_budget > 0 and actual_daily_pace > (safe_daily_allowance * 1.35) and days_remaining > 5:
        burn_status = 'Pacing Fast'
    else:
        burn_status = 'On Track'

    # Recurring items and cycle timeline
    recurring_all = db.query_all("""
        SELECT r.recurring_id, r.amount, r.frequency, 
               TO_CHAR(r.next_due_date, 'YYYY-MM-DD') AS due_str,
               c.category_name, a.account_type, a.account_id
        FROM RecurringPayments r
        JOIN Accounts a ON r.account_id = a.account_id
        JOIN Categories c ON r.category_id = c.category_id
        WHERE a.user_id = :usr_id
        ORDER BY r.next_due_date ASC
    """, {'usr_id': user_id})

    upcoming_bills = 0.0
    processed_bills = 0.0
    total_monthly_commitments = sum(r['amount'] for r in recurring_all if r['frequency'] == 'Monthly')

    timeline_events = []
    for r in recurring_all:
        due_str = r['due_str']
        try:
            due_dt = datetime.strptime(due_str, '%Y-%m-%d')
            due_day = due_dt.day

            if due_str.startswith(month):
                if is_current_month and due_dt.date() <= now.date():
                    status = 'Due Now'
                    badge_class = 'danger'
                else:
                    days_diff = (due_dt.date() - now.date()).days
                    status = f"Due in {max(0, days_diff)}d" if is_current_month else "Scheduled"
                    badge_class = 'primary'
                    upcoming_bills += r['amount']
                
                timeline_events.append({
                    'day': due_day,
                    'title': r['category_name'],
                    'frequency': r['frequency'],
                    'amount': r['amount'],
                    'status': status,
                    'badge_class': badge_class,
                    'due_date': due_str,
                    'account': f"{r['account_type']} (#{r['account_id']})"
                })
            elif due_dt > datetime(year, month_num, total_days) and is_current_month:
                processed_bills += r['amount']
                timeline_events.append({
                    'day': due_day,
                    'title': r['category_name'],
                    'frequency': r['frequency'],
                    'amount': r['amount'],
                    'status': 'Billed this Cycle',
                    'badge_class': 'success',
                    'due_date': f"{month}-{due_day:02d}",
                    'account': f"{r['account_type']} (#{r['account_id']})"
                })
        except Exception:
            pass

    timeline_events.sort(key=lambda x: x['day'])
    month_name = datetime(year, month_num, 1).strftime('%B %Y')

    return {
        'month': month,
        'month_name': month_name,
        'year': year,
        'month_num': month_num,
        'total_days': total_days,
        'current_day': current_day,
        'days_remaining': days_remaining,
        'is_current_month': is_current_month,
        'cycle_progress_percent': cycle_progress_percent,
        'cycle_inflow': cycle_inflow,
        'cycle_outflow': cycle_outflow,
        'cycle_net_savings': cycle_net_savings,
        'savings_rate': savings_rate,
        'total_budget': total_budget,
        'remaining_budget': remaining_budget,
        'safe_daily_allowance': safe_daily_allowance,
        'actual_daily_pace': actual_daily_pace,
        'burn_status': burn_status,
        'upcoming_bills': upcoming_bills,
        'processed_bills': processed_bills,
        'total_monthly_commitments': total_monthly_commitments,
        'timeline_events': timeline_events,
        'recurring_count': len(recurring_all)
    }

@app.before_request
def require_login():
    open_endpoints = ['login', 'register', 'static']
    if request.endpoint not in open_endpoints and 'user_id' not in session:
        return redirect(url_for('login'))

    # Restrict ADMIN users from regular consumer banking pages
    if session.get('user_role') == 'ADMIN':
        user_endpoints = [
            'dashboard', 'setup', 'accounts', 'create_account', 'toggle_account_status',
            'transactions', 'create_transaction', 'export_transactions',
            'transfer', 
            'budgets', 'set_budget', 'reduce_salary',
            'recurring', 'add_recurring', 'run_recurring_procedure', 
            'predictions', 'generate_predictions_procedure'
        ]
        if request.endpoint in user_endpoints:
            return redirect(url_for('admin_portal'))

@app.context_processor
def inject_global_data():
    user = get_current_user()
    alerts = []
    if user:
        alerts = db.query_all(
            "SELECT * FROM Alerts WHERE user_id = :usr_id AND is_read = 0 ORDER BY created_at DESC FETCH FIRST 5 ROWS ONLY",
            {'usr_id': user['id']}
        )
    return {'current_user': user, 'unread_alerts': alerts, 'current_year_month': datetime.now().strftime('%Y-%m')}

# --- AUTHENTICATION ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        user = db.query_one("SELECT * FROM Users WHERE email = :email", {'email': email})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user.get('role', 'USER')
            flash(f"Welcome back, {user['name']}!", "success")
            if session['user_role'] == 'ADMIN':
                return redirect(url_for('admin_portal'))
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        salary_str = request.form.get('initial_salary', '').strip()
        try:
            salary_amount = float(salary_str) if salary_str else 0.0
        except ValueError:
            salary_amount = 0.0
            
        employer = request.form.get('employer', '').strip() or 'Employer / Salary'

        if not name or not email or not password:
            flash("All required fields must be filled.", "danger")
            return render_template('register.html')

        existing = db.query_one("SELECT user_id FROM Users WHERE email = :email", {'email': email})
        if existing:
            flash("An account with this email already exists.", "warning")
            return render_template('register.html')

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            user_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute(
                "INSERT INTO Users (name, email, password_hash, role, monthly_salary) VALUES (:1, :2, :3, 'USER', :4) RETURNING user_id INTO :5",
                [name, email, hashed_pw, salary_amount, user_id_var]
            )
            new_uid = int(user_id_var.getvalue()[0])
            
            # Create a default Savings account
            acc_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute(
                "INSERT INTO Accounts (user_id, account_type, balance) VALUES (:1, 'Savings', 0.00) RETURNING account_id INTO :2",
                [new_uid, acc_id_var]
            )
            new_acc_id = int(acc_id_var.getvalue()[0])

            # If user specified an initial salary or opening balance, record it as a Credit transaction
            # The database trigger trg_update_account_balance will automatically update the account balance!
            if salary_amount > 0:
                cursor.execute(
                    """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                       VALUES (:1, 1, :2, 'Credit', SYSDATE, :3, 'Monthly Salary / Initial Deposit')""",
                    [new_acc_id, salary_amount, employer]
                )

            conn.commit()
            
            session['user_id'] = new_uid
            session['user_name'] = name
            session['user_email'] = email
            session['user_role'] = 'USER'

            flash("Account registered! Welcome to FinTrack. Let's configure your monthly salary and category budgets.", "success")
            return redirect(url_for('setup', new=1))
        except Exception as e:
            conn.rollback()
            flash(f"Registration error: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Onboarding Setup Wizard & Salary/Budget Rebalancer for new and existing users."""
    user = get_current_user()
    current_month = datetime.now().strftime('%Y-%m')

    user_info = db.query_one(
        "SELECT user_id, name, email, NVL(monthly_salary, 0) AS monthly_salary FROM Users WHERE user_id = :usr_id",
        {'usr_id': user['id']}
    )
    user_accounts = db.query_all(
        "SELECT account_id, account_type, balance, status FROM Accounts WHERE user_id = :usr_id AND status = 'Active' ORDER BY account_id",
        {'usr_id': user['id']}
    )
    categories = db.query_all(
        "SELECT category_id, category_name FROM Categories WHERE type = 'Expense' ORDER BY category_id"
    )

    if request.method == 'POST':
        try:
            salary = float(request.form.get('salary', 0) or 0)
        except (ValueError, TypeError):
            salary = 0.0

        employer = request.form.get('employer', '').strip() or 'Employer Salary'
        account_id = int(request.form.get('account_id', 0) or 0)
        deposit_now = request.form.get('deposit_now') == 'on'

        # 1. Update baseline monthly salary in Users table
        db.execute_dml(
            "UPDATE Users SET monthly_salary = :sal WHERE user_id = :usr_id",
            {'sal': salary, 'usr_id': user['id']}
        )

        # 2. Deposit salary if requested and valid
        if deposit_now and salary > 0 and account_id > 0:
            acc = db.query_one(
                "SELECT account_id, account_type, status FROM Accounts WHERE account_id = :aid AND user_id = :usr_id",
                {'aid': account_id, 'usr_id': user['id']}
            )
            if acc and acc.get('status') == 'Active':
                try:
                    db.execute_dml(
                        """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                           VALUES (:1, 1, :2, 'Credit', SYSDATE, :3, 'Monthly Salary Credit')""",
                        [account_id, salary, employer]
                    )
                except Exception as e:
                    flash(f"Note on salary deposit: {str(e)}", "warning")

        # 3. Upsert Category Budgets for the active month using Oracle MERGE
        merge_sql = """
            MERGE INTO Budgets b
            USING (SELECT :usr_id AS user_id, :cat_id AS category_id, :month AS month, :limit_amt AS limit_amount FROM dual) src
            ON (b.user_id = src.user_id AND b.category_id = src.category_id AND b.month = src.month)
            WHEN MATCHED THEN
                UPDATE SET b.limit_amount = src.limit_amount
            WHEN NOT MATCHED THEN
                INSERT (user_id, category_id, month, limit_amount)
                VALUES (src.user_id, src.category_id, src.month, src.limit_amount)
        """
        budgets_saved_count = 0
        for cat in categories:
            raw_val = request.form.get(f'budget_{cat["category_id"]}', 0)
            try:
                limit_amt = float(raw_val or 0)
            except (ValueError, TypeError):
                limit_amt = 0.0

            if limit_amt > 0:
                db.execute_dml(merge_sql, {
                    'usr_id': user['id'],
                    'cat_id': cat['category_id'],
                    'month': current_month,
                    'limit_amt': limit_amt
                })
                budgets_saved_count += 1
            else:
                db.execute_dml(
                    "DELETE FROM Budgets WHERE user_id = :usr_id AND category_id = :cat_id AND month = :month",
                    {'usr_id': user['id'], 'cat_id': cat['category_id'], 'month': current_month}
                )

        if request.args.get('new') == '1':
            flash(f"🎉 Welcome to FinTrack! Your monthly salary of ₹{salary:,.2f} and {budgets_saved_count} category budgets are active.", "success")
        else:
            flash(f"✅ Monthly salary updated to ₹{salary:,.2f} and {budgets_saved_count} category budgets rebalanced successfully!", "success")

        return redirect(url_for('dashboard'))

    # GET Request: Fetch existing budgets
    existing_budgets = db.query_all(
        "SELECT category_id, limit_amount FROM Budgets WHERE user_id = :usr_id AND month = :month",
        {'usr_id': user['id'], 'month': current_month}
    )
    existing_budget_map = {b['category_id']: b['limit_amount'] for b in existing_budgets}

    current_salary = user_info.get('monthly_salary', 0.0) if user_info else 0.0
    if current_salary == 0:
        current_salary = 60000.00

    is_new = request.args.get('new') == '1' or (len(existing_budget_map) == 0 and (not user_info or user_info.get('monthly_salary', 0) == 0))

    return render_template(
        'setup.html',
        current_salary=current_salary,
        employer='Employer Salary',
        accounts=user_accounts,
        categories=categories,
        existing_budget_map=existing_budget_map,
        current_month=current_month,
        is_new=is_new
    )

# --- CORE APPLICATION ROUTES ---

@app.route('/')
def dashboard():
    user = get_current_user()
    current_month = datetime.now().strftime('%Y-%m')

    # 1. Total Net Balance across accounts
    acc_summary = db.query_one(
        "SELECT NVL(SUM(balance), 0) AS total_balance, COUNT(account_id) AS total_accounts FROM Accounts WHERE user_id = :usr_id",
        {'usr_id': user['id']}
    )
    total_balance = acc_summary['total_balance'] if acc_summary else 0.0
    total_accounts = acc_summary['total_accounts'] if acc_summary else 0

    # 2. Total Monthly Expense using Stored Function get_monthly_total
    total_expense = db.execute_function("get_monthly_total", oracledb.NUMBER, [user['id'], current_month]) or 0.0

    # 3. Total Monthly Income
    income_res = db.query_one("""
        SELECT NVL(SUM(t.amount), 0) AS total_income
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        WHERE a.user_id = :usr_id 
          AND t.txn_type = 'Credit' 
          AND TO_CHAR(t.txn_date, 'YYYY-MM') = :month
    """, {'usr_id': user['id'], 'month': current_month})
    total_income = income_res['total_income'] if income_res else 0.0

    # 4. Recent Transactions (Guaranteed newest on top by transaction_id)
    recent_transactions = db.query_all("""
        SELECT t.transaction_id, t.amount, t.txn_type, TO_CHAR(t.txn_date, 'YYYY-MM-DD') AS formatted_date, 
               t.vendor, t.description, c.category_name, a.account_type
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        JOIN Categories c ON t.category_id = c.category_id
        WHERE a.user_id = :usr_id
        ORDER BY t.transaction_id DESC
        FETCH FIRST 8 ROWS ONLY
    """, {'usr_id': user['id']})

    # 5. Active Budgets vs Actual Spend (from Database View v_budget_vs_actual)
    budgets = db.query_all("""
        SELECT * FROM v_budget_vs_actual 
        WHERE user_id = :usr_id AND month = :month
        ORDER BY percent_used DESC
    """, {'usr_id': user['id'], 'month': current_month})

    # 6. Monthly Spending by Category for Chart.js
    category_spend = db.query_all("""
        SELECT c.category_name, SUM(t.amount) AS total
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        JOIN Categories c ON t.category_id = c.category_id
        WHERE a.user_id = :usr_id AND t.txn_type = 'Debit' AND TO_CHAR(t.txn_date, 'YYYY-MM') = :month
        GROUP BY c.category_name
        ORDER BY total DESC
    """, {'usr_id': user['id'], 'month': current_month})

    cycle = get_monthly_cycle_data(user['id'], current_month)

    # Active user accounts for quick transactions & salary deposits
    user_accounts = db.query_all(
        "SELECT account_id, account_type, balance, status FROM Accounts WHERE user_id = :usr_id AND status = 'Active' ORDER BY account_id",
        {'usr_id': user['id']}
    )

    # User profile salary for deficit checks
    user_info = db.query_one(
        "SELECT NVL(monthly_salary, 0) AS monthly_salary FROM Users WHERE user_id = :usr_id",
        {'usr_id': user['id']}
    )
    monthly_salary = float(user_info['monthly_salary']) if user_info and user_info.get('monthly_salary') else 0.0
    total_budget_limits = sum(float(b.get('limit_amount', 0) or 0) for b in budgets)
    
    # Check if spending or budget commitments exceed salary
    is_salary_deficit = False
    deficit_amount = 0.0
    if monthly_salary > 0:
        if total_budget_limits > monthly_salary:
            is_salary_deficit = True
            deficit_amount = total_budget_limits - monthly_salary
        elif total_expense > monthly_salary:
            is_salary_deficit = True
            deficit_amount = total_expense - monthly_salary

    return render_template(
        'index.html',
        total_balance=total_balance,
        total_accounts=total_accounts,
        total_expense=total_expense,
        total_income=total_income,
        recent_transactions=recent_transactions,
        budgets=budgets,
        category_spend=category_spend,
        current_month=current_month,
        cycle=cycle,
        accounts=user_accounts,
        monthly_salary=monthly_salary,
        total_budget_limits=total_budget_limits,
        is_salary_deficit=is_salary_deficit,
        deficit_amount=deficit_amount
    )

@app.route('/reduce-salary', methods=['POST'])
def reduce_salary():
    """Dynamically applies a salary reduction / pay cut and invokes Oracle PL/SQL handle_salary_reduction."""
    user = get_current_user()
    current_month = datetime.now().strftime('%Y-%m')
    
    try:
        new_salary = float(request.form.get('new_salary', 0) or 0)
    except (ValueError, TypeError):
        new_salary = 0.0

    reduction_reason = request.form.get('reduction_reason', '').strip() or 'Salary Reduction / Variable Income'
    strategy = request.form.get('strategy', 'LEAN_70_20_10').strip()

    if new_salary <= 0:
        flash("Please enter a valid reduced salary amount greater than zero.", "danger")
        return redirect(request.referrer or url_for('dashboard'))

    conn = db.get_connection()
    cur = conn.cursor()
    try:
        old_salary_var = cur.var(oracledb.NUMBER)
        adjusted_budget_var = cur.var(oracledb.NUMBER)
        status_var = cur.var(oracledb.STRING)

        cur.callproc("handle_salary_reduction", [
            user['id'],
            new_salary,
            reduction_reason,
            strategy,
            current_month,
            old_salary_var,
            adjusted_budget_var,
            status_var
        ])
        
        status_res = status_var.getvalue()
        old_sal = old_salary_var.getvalue() or 0.0
        adj_budget = adjusted_budget_var.getvalue() or 0.0

        if status_res and status_res.startswith('ERROR'):
            flash(f"Database error executing salary reduction: {status_res}", "danger")
        else:
            diff = old_sal - new_salary
            strategy_names = {
                'LEAN_70_20_10': '70/20/10 Lean Cut',
                'SURVIVAL_80_20': '80/20 Emergency Survival',
                'PROPORTIONAL': 'Proportional Downscale'
            }
            strat_label = strategy_names.get(strategy, strategy)
            flash(
                f"📉 Salary reduction successfully applied via Oracle PL/SQL! Monthly income adjusted from ₹{old_sal:,.2f} to ₹{new_salary:,.2f} (-₹{diff:,.2f}). "
                f"All category budgets were automatically downscaled to ₹{adj_budget:,.2f} using the {strat_label} strategy to prevent overdrafts.",
                "warning"
            )
    except Exception as e:
        flash(f"Error applying salary reduction: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('dashboard'))

@app.route('/accounts')
def accounts():
    user = get_current_user()
    user_accounts = db.query_all(
        "SELECT account_id, account_type, balance, status, TO_CHAR(opened_at, 'YYYY-MM-DD') AS opened_date FROM Accounts WHERE user_id = :usr_id ORDER BY account_id",
        {'usr_id': user['id']}
    )
    return render_template('accounts.html', accounts=user_accounts)

@app.route('/accounts/toggle-status/<int:account_id>', methods=['POST'])
def toggle_account_status(account_id):
    user = get_current_user()
    acc = db.query_one("SELECT status FROM Accounts WHERE account_id = :aid AND user_id = :usr_id", {'aid': account_id, 'usr_id': user['id']})
    if not acc:
        flash("Account not found.", "danger")
        return redirect(url_for('accounts'))
    new_status = 'Frozen' if acc['status'] == 'Active' else 'Active'
    db.execute_dml("UPDATE Accounts SET status = :st WHERE account_id = :aid AND user_id = :usr_id", {'st': new_status, 'aid': account_id, 'usr_id': user['id']})
    flash(f"Account #{account_id} status successfully changed to {new_status}!", "success")
    return redirect(url_for('accounts'))

@app.route('/accounts/create', methods=['POST'])
def create_account():
    user = get_current_user()
    account_type = request.form.get('account_type')
    initial_balance = float(request.form.get('initial_balance', 0.0) or 0.0)

    if account_type not in ['Savings', 'Current', 'Credit', 'Wallet']:
        flash("Invalid account type selected.", "danger")
        return redirect(url_for('accounts'))

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        acc_id_var = cursor.var(oracledb.NUMBER)
        cursor.execute(
            "INSERT INTO Accounts (user_id, account_type, balance) VALUES (:1, :2, 0.00) RETURNING account_id INTO :3",
            [user['id'], account_type, acc_id_var]
        )
        new_acc_id = int(acc_id_var.getvalue()[0])

        # If initial balance > 0, log an initial Credit transaction so trigger maintains balance
        if initial_balance > 0:
            # Category 1 = Salary or opening credit
            cursor.execute(
                """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
                   VALUES (:1, 1, :2, 'Credit', SYSDATE, 'Initial Opening Balance')""",
                [new_acc_id, initial_balance]
            )

        conn.commit()
        flash(f"{account_type} account created successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error creating account: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('accounts'))

@app.route('/salary/deposit', methods=['POST'])
def deposit_salary():
    """Allows users to record their monthly salary or income deposit with automatic trigger balance update."""
    user = get_current_user()
    try:
        account_id = int(request.form.get('account_id', 0))
        amount = float(request.form.get('amount', 0))
    except (ValueError, TypeError):
        flash("Invalid salary amount or account selected.", "danger")
        return redirect(request.referrer or url_for('dashboard'))

    if amount <= 0:
        flash("Salary amount must be strictly greater than zero.", "danger")
        return redirect(request.referrer or url_for('dashboard'))

    employer = request.form.get('employer', '').strip() or 'Employer / Salary'
    description = request.form.get('description', '').strip() or 'Monthly Salary Credit'
    salary_date = request.form.get('salary_date', '').strip()

    # Verify that the account belongs to the user and is Active
    acc = db.query_one(
        "SELECT account_id, account_type, status FROM Accounts WHERE account_id = :aid AND user_id = :usr_id",
        {'aid': account_id, 'usr_id': user['id']}
    )
    if not acc:
        flash("Selected account not found or access denied.", "danger")
        return redirect(request.referrer or url_for('dashboard'))

    if acc.get('status') == 'Frozen':
        flash(f"Cannot deposit salary: Account #{account_id} is Frozen. Please unfreeze it first.", "danger")
        return redirect(request.referrer or url_for('dashboard'))

    try:
        # Category 1 = Salary (Income)
        # Database trigger trg_update_account_balance automatically adds this amount to the account balance!
        if salary_date:
            db.execute_dml(
                """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                   VALUES (:1, 1, :2, 'Credit', TO_DATE(:3 || ' ' || TO_CHAR(SYSDATE, 'HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS'), :4, :5)""",
                [account_id, amount, salary_date, employer, description]
            )
        else:
            db.execute_dml(
                """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                   VALUES (:1, 1, :2, 'Credit', SYSDATE, :3, :4)""",
                [account_id, amount, employer, description]
            )
        flash(f"🎉 Monthly salary of ₹{amount:,.2f} successfully credited to your {acc['account_type']} account! Live balance updated by trigger.", "success")
    except Exception as e:
        flash(f"Failed to record salary deposit: {str(e)}", "danger")

    return redirect(request.referrer or url_for('dashboard'))

@app.route('/transactions')
def transactions():
    user = get_current_user()
    category_id = request.args.get('category_id')
    account_id = request.args.get('account_id')
    txn_type = request.args.get('type')
    month = request.args.get('month', '').strip()
    search_q = request.args.get('q', '').strip()

    sql = """
        SELECT t.transaction_id, t.account_id, t.amount, t.txn_type, 
               TO_CHAR(t.txn_date, 'YYYY-MM-DD') AS formatted_date, 
               t.vendor, t.description, c.category_name, a.account_type
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        JOIN Categories c ON t.category_id = c.category_id
        WHERE a.user_id = :usr_id
    """
    params = {'usr_id': user['id']}

    if category_id:
        sql += " AND t.category_id = :cat_id"
        params['cat_id'] = category_id
    if account_id:
        sql += " AND t.account_id = :acc_id"
        params['acc_id'] = account_id
    if txn_type:
        sql += " AND t.txn_type = :ttype"
        params['ttype'] = txn_type
    if month:
        sql += " AND TO_CHAR(t.txn_date, 'YYYY-MM') = :month"
        params['month'] = month
    if search_q:
        sql += " AND (LOWER(t.description) LIKE :q OR LOWER(t.vendor) LIKE :q)"
        params['q'] = f"%{search_q.lower()}%"

    sql += " ORDER BY t.txn_date DESC, t.transaction_id DESC"

    txn_list = db.query_all(sql, params)
    user_accounts = db.query_all("SELECT account_id, account_type FROM Accounts WHERE user_id = :usr_id", {'usr_id': user['id']})
    categories = db.query_all("SELECT category_id, category_name, type FROM Categories ORDER BY category_name")

    # Available distinct months for filtering
    available_months = db.query_all("""
        SELECT DISTINCT TO_CHAR(t.txn_date, 'YYYY-MM') AS month_str
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        WHERE a.user_id = :usr_id
        ORDER BY month_str DESC
    """, {'usr_id': user['id']})

    # Filtered financial statistics
    filtered_inflow = sum(t['amount'] for t in txn_list if t['txn_type'] == 'Credit')
    filtered_outflow = sum(t['amount'] for t in txn_list if t['txn_type'] == 'Debit')
    net_cashflow = filtered_inflow - filtered_outflow

    return render_template(
        'transactions.html',
        transactions=txn_list,
        accounts=user_accounts,
        categories=categories,
        available_months=available_months,
        selected_cat=category_id,
        selected_acc=account_id,
        selected_type=txn_type,
        selected_month=month,
        search_q=search_q,
        filtered_inflow=filtered_inflow,
        filtered_outflow=filtered_outflow,
        net_cashflow=net_cashflow
    )

@app.route('/transactions/export')
def export_transactions():
    """Generates an RFC-compliant CSV statement for filtered ledger transactions."""
    user = get_current_user()
    category_id = request.args.get('category_id')
    account_id = request.args.get('account_id')
    txn_type = request.args.get('type')
    month = request.args.get('month', '').strip()
    search_q = request.args.get('q', '').strip()

    sql = """
        SELECT t.transaction_id, t.account_id, t.amount, t.txn_type, 
               TO_CHAR(t.txn_date, 'YYYY-MM-DD') AS formatted_date, 
               t.vendor, t.description, c.category_name, a.account_type
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        JOIN Categories c ON t.category_id = c.category_id
        WHERE a.user_id = :usr_id
    """
    params = {'usr_id': user['id']}

    if category_id:
        sql += " AND t.category_id = :cat_id"
        params['cat_id'] = category_id
    if account_id:
        sql += " AND t.account_id = :acc_id"
        params['acc_id'] = account_id
    if txn_type:
        sql += " AND t.txn_type = :ttype"
        params['ttype'] = txn_type
    if month:
        sql += " AND TO_CHAR(t.txn_date, 'YYYY-MM') = :month"
        params['month'] = month
    if search_q:
        sql += " AND (LOWER(t.description) LIKE :q OR LOWER(t.vendor) LIKE :q)"
        params['q'] = f"%{search_q.lower()}%"

    sql += " ORDER BY t.txn_date DESC, t.transaction_id DESC"

    txn_list = db.query_all(sql, params)

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Ref #', 'Date', 'Account Type', 'Category', 'Vendor / Payee', 'Type', 'Amount (INR)', 'Description'])
    for t in txn_list:
        writer.writerow([
            f"TXN-{t['transaction_id']:05d}",
            t['formatted_date'],
            t['account_type'],
            t['category_name'],
            t['vendor'] or 'N/A',
            t['txn_type'],
            f"{t['amount']:.2f}",
            t['description'] or ''
        ])

    file_label = month if month else 'Statement'
    filename = f"FinTrack_{file_label}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/transactions/create', methods=['POST'])
def create_transaction():
    user = get_current_user()
    try:
        account_id = int(request.form.get('account_id', 0))
        category_id = int(request.form.get('category_id', 0))
        amount = float(request.form.get('amount', 0))
    except (ValueError, TypeError):
        flash("Invalid transaction input values.", "danger")
        return redirect(url_for('transactions'))

    txn_type = request.form.get('txn_type', 'Debit')
    vendor = request.form.get('vendor', '').strip()
    raw_desc = request.form.get('description', '').strip()
    txn_date = request.form.get('txn_date')

    if amount <= 0:
        flash("Transaction amount must be strictly greater than zero.", "danger")
        return redirect(url_for('transactions'))

    # Security check: Verify account belongs to current user
    acc = db.query_one("SELECT account_id, status, balance FROM Accounts WHERE account_id = :aid AND user_id = :usr_id", {'aid': account_id, 'usr_id': user['id']})
    if not acc:
        flash("Selected account not found or access denied.", "danger")
        return redirect(url_for('transactions'))

    # Business rule: Disallow debit on frozen accounts
    if acc.get('status') == 'Frozen' and txn_type == 'Debit':
        flash(f"Transaction rejected: Account #{account_id} is FROZEN. Please unfreeze it in the Accounts tab before spending.", "danger")
        return redirect(url_for('transactions'))

    # Business rule: Insufficient funds check for debit transactions
    if txn_type == 'Debit' and acc['balance'] < amount:
        flash(f"Transaction rejected: Insufficient funds in Account #{account_id} (Available balance: ₹{acc['balance']:,.2f}).", "danger")
        return redirect(url_for('transactions'))

    if vendor and raw_desc:
        description = f"{vendor} - {raw_desc}"
    elif vendor:
        description = f"Payment to {vendor}" if txn_type == 'Debit' else f"Payment from {vendor}"
    else:
        description = raw_desc or ('Credit Deposit' if txn_type == 'Credit' else 'Expense Payment')

    try:
        if txn_date:
            db.execute_dml(
                """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                   VALUES (:1, :2, :3, :4, TO_DATE(:5 || ' ' || TO_CHAR(SYSDATE, 'HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS'), :6, :7)""",
                [account_id, category_id, amount, txn_type, txn_date, vendor or None, description]
            )
        else:
            db.execute_dml(
                """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                   VALUES (:1, :2, :3, :4, SYSDATE, :5, :6)""",
                [account_id, category_id, amount, txn_type, vendor or None, description]
            )
        flash("Transaction recorded successfully! Account balance and monthly cycle updated.", "success")
    except Exception as e:
        flash(f"Transaction failed: {str(e)}", "danger")

    return redirect(url_for('transactions'))

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    user = get_current_user()
    user_accounts = db.query_all("SELECT account_id, account_type, balance, status FROM Accounts WHERE user_id = :usr_id", {'usr_id': user['id']})
    categories = db.query_all("SELECT category_id, category_name FROM Categories WHERE type = 'Expense' ORDER BY category_name")

    # Frequent Payees / Quick Vendor Pay list
    frequent_payees = db.query_all("""
        SELECT t.vendor, t.category_id, c.category_name, 
               COUNT(*) AS payment_count,
               MAX(t.amount) AS last_amount,
               ROUND(AVG(t.amount), 2) AS avg_amount
        FROM Transactions t
        JOIN Accounts a ON t.account_id = a.account_id
        JOIN Categories c ON t.category_id = c.category_id
        WHERE a.user_id = :usr_id AND t.vendor IS NOT NULL
        GROUP BY t.vendor, t.category_id, c.category_name
        ORDER BY payment_count DESC, MAX(t.txn_date) DESC
        FETCH FIRST 6 ROWS ONLY
    """, {'usr_id': user['id']})

    if request.method == 'POST':
        transfer_type = request.form.get('transfer_type', 'internal')
        
        if transfer_type == 'vendor':
            # Pay External Vendor / Merchant / Friend
            try:
                from_acc = int(request.form.get('from_account', 0))
                category_id = int(request.form.get('category_id', 0))
                amount = float(request.form.get('amount', 0))
            except (ValueError, TypeError):
                flash("Invalid payment inputs.", "danger")
                return redirect(url_for('transfer'))

            vendor_name = request.form.get('vendor_name', '').strip()
            raw_note = request.form.get('description', '').strip()

            # Clean and informative description combining vendor and user memo
            if raw_note:
                description = f"Payment to {vendor_name} ({raw_note})"
            else:
                description = f"Payment to {vendor_name}"

            txn_date = request.form.get('txn_date')

            if not vendor_name:
                flash("Vendor/Payee name is required.", "danger")
                return redirect(url_for('transfer'))
            if amount <= 0:
                flash("Payment amount must be greater than zero.", "danger")
                return redirect(url_for('transfer'))

            # Check balance & account status
            src_acc = db.query_one("SELECT balance, status FROM Accounts WHERE account_id = :aid AND user_id = :usr_id", {'aid': from_acc, 'usr_id': user['id']})
            if not src_acc:
                flash("Source account not found.", "danger")
                return redirect(url_for('transfer'))
            if src_acc.get('status') == 'Frozen':
                flash(f"Payment aborted: Account #{from_acc} is FROZEN. Please unfreeze it in the Accounts tab before transferring.", "danger")
                return redirect(url_for('transfer'))
            if src_acc['balance'] < amount:
                flash(f"Payment aborted: Insufficient funds in source account (Balance: ₹{src_acc['balance']:,.2f}).", "danger")
                return redirect(url_for('transfer'))

            # Insert Debit transaction for vendor payment (trigger updates balance)
            try:
                if txn_date:
                    db.execute_dml(
                        """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                           VALUES (:1, :2, :3, 'Debit', TO_DATE(:4 || ' ' || TO_CHAR(SYSDATE, 'HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS'), :5, :6)""",
                        [from_acc, category_id, amount, txn_date, vendor_name, description]
                    )
                else:
                    db.execute_dml(
                        """INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, vendor, description)
                           VALUES (:1, :2, :3, 'Debit', SYSDATE, :4, :5)""",
                        [from_acc, category_id, amount, vendor_name, description]
                    )
                flash(f"Payment of ₹{amount:,.2f} to '{vendor_name}' processed successfully!", "success")
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f"Vendor payment failed: {str(e)}", "danger")

        else:
            # Internal Inter-Account Transfer (using stored procedure)
            try:
                from_acc = int(request.form.get('from_account', 0))
                to_acc = int(request.form.get('to_account', 0))
                amount = float(request.form.get('amount', 0))
            except (ValueError, TypeError):
                flash("Invalid transfer inputs. Please verify account numbers and amount.", "danger")
                return redirect(url_for('transfer'))

            raw_desc = request.form.get('description', '').strip()

            if amount <= 0:
                flash("Transfer amount must be greater than zero.", "danger")
                return redirect(url_for('transfer'))

            if from_acc == to_acc:
                flash("Transfer aborted: Source and destination accounts must be different.", "danger")
                return redirect(url_for('transfer'))

            src_acc = db.query_one("SELECT status FROM Accounts WHERE account_id = :aid AND user_id = :usr_id", {'aid': from_acc, 'usr_id': user['id']})
            if not src_acc:
                flash("Source account not found or access denied.", "danger")
                return redirect(url_for('transfer'))
            if src_acc.get('status') == 'Frozen':
                flash(f"Transfer aborted: Source account #{from_acc} is FROZEN. Please unfreeze it before transferring.", "danger")
                return redirect(url_for('transfer'))

            from_info = db.query_one("SELECT account_type FROM Accounts WHERE account_id = :aid", {'aid': from_acc})
            to_info = db.query_one("SELECT account_type FROM Accounts WHERE account_id = :aid", {'aid': to_acc})
            from_name = from_info['account_type'] if from_info else f"A/C #{from_acc}"
            to_name = to_info['account_type'] if to_info else f"A/C #{to_acc}"

            transfer_desc = f"Transfer: {from_name} → {to_name}"
            if raw_desc and raw_desc != 'Inter-account transfer':
                transfer_desc += f" ({raw_desc})"

            conn = db.get_connection()
            cursor = conn.cursor()
            try:
                status_var = cursor.var(oracledb.STRING)
                cursor.callproc("transfer_funds", [from_acc, to_acc, amount, transfer_desc, status_var])
                conn.commit()
                flash(f"Transfer Success: {status_var.getvalue()}", "success")
                return redirect(url_for('dashboard'))
            except oracledb.DatabaseError as e:
                conn.rollback()
                error_obj, = e.args
                flash(f"Transfer Aborted & Rolled Back: {error_obj.message}", "danger")
            finally:
                cursor.close()
                conn.close()

    return render_template('transfer.html', accounts=user_accounts, categories=categories, frequent_payees=frequent_payees)

@app.route('/budgets', methods=['GET', 'POST'])
def budgets():
    user = get_current_user()
    current_month = datetime.now().strftime('%Y-%m')
    selected_month = request.args.get('month', current_month)

    if request.method == 'POST':
        category_id = int(request.form.get('category_id'))
        month = request.form.get('month')
        limit_amount = float(request.form.get('limit_amount', 0))

        if limit_amount <= 0:
            flash("Budget limit must be greater than zero.", "danger")
        else:
            try:
                # Upsert budget
                db.execute_dml("""
                    MERGE INTO Budgets b
                    USING (SELECT :usr_id AS user_id, :cat_id AS category_id, :month AS month, :lim AS limit_amount FROM DUAL) src
                    ON (b.user_id = src.user_id AND b.category_id = src.category_id AND b.month = src.month)
                    WHEN MATCHED THEN
                        UPDATE SET b.limit_amount = src.limit_amount
                    WHEN NOT MATCHED THEN
                        INSERT (user_id, category_id, month, limit_amount)
                        VALUES (src.user_id, src.category_id, src.month, src.limit_amount)
                """, {'usr_id': user['id'], 'cat_id': category_id, 'month': month, 'lim': limit_amount})
                flash("Budget saved successfully!", "success")
            except Exception as e:
                flash(f"Error saving budget: {str(e)}", "danger")

        return redirect(url_for('budgets', month=selected_month))

    # Pull straight from Database View v_budget_vs_actual
    budget_items = db.query_all("""
        SELECT * FROM v_budget_vs_actual
        WHERE user_id = :usr_id AND month = :month
        ORDER BY percent_used DESC
    """, {'usr_id': user['id'], 'month': selected_month})

    expense_categories = db.query_all("SELECT category_id, category_name FROM Categories WHERE type = 'Expense' ORDER BY category_name")

    cycle = get_monthly_cycle_data(user['id'], selected_month)

    user_info = db.query_one("SELECT NVL(monthly_salary, 0) AS monthly_salary FROM Users WHERE user_id = :usr_id", {'usr_id': user['id']})
    monthly_salary = float(user_info['monthly_salary']) if user_info and user_info.get('monthly_salary') else 0.0

    return render_template(
        'budgets.html',
        budgets=budget_items,
        categories=expense_categories,
        selected_month=selected_month,
        cycle=cycle,
        monthly_salary=monthly_salary
    )

@app.route('/recurring')
def recurring():
    user = get_current_user()
    items = db.query_all("""
        SELECT r.recurring_id, r.account_id, r.amount, r.frequency, 
               TO_CHAR(r.next_due_date, 'YYYY-MM-DD') AS due_date_str,
               c.category_name, a.account_type,
               CASE WHEN TRUNC(r.next_due_date) <= TRUNC(SYSDATE) THEN 1 ELSE 0 END AS is_due
        FROM RecurringPayments r
        JOIN Accounts a ON r.account_id = a.account_id
        JOIN Categories c ON r.category_id = c.category_id
        WHERE a.user_id = :usr_id
        ORDER BY r.next_due_date ASC
    """, {'usr_id': user['id']})

    user_accounts = db.query_all("SELECT account_id, account_type FROM Accounts WHERE user_id = :usr_id", {'usr_id': user['id']})
    categories = db.query_all("SELECT category_id, category_name FROM Categories WHERE type = 'Expense' ORDER BY category_name")

    cycle = get_monthly_cycle_data(user['id'], datetime.now().strftime('%Y-%m'))

    return render_template('recurring.html', recurring=items, accounts=user_accounts, categories=categories, cycle=cycle)

@app.route('/recurring/create', methods=['POST'])
def create_recurring():
    account_id = request.form.get('account_id')
    category_id = request.form.get('category_id')
    amount = float(request.form.get('amount', 0))
    frequency = request.form.get('frequency')
    next_due_date = request.form.get('next_due_date')

    if amount <= 0:
        flash("Amount must be greater than zero.", "danger")
        return redirect(url_for('recurring'))

    try:
        db.execute_dml("""
            INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
            VALUES (:1, :2, :3, :4, TO_DATE(:5, 'YYYY-MM-DD'))
        """, [account_id, category_id, amount, frequency, next_due_date])
        flash("Recurring schedule created successfully!", "success")
    except Exception as e:
        flash(f"Failed to create recurring payment: {str(e)}", "danger")

    return redirect(url_for('recurring'))

@app.route('/recurring/run', methods=['POST'])
def run_recurring_procedure():
    """Triggers the stored procedure generate_recurring_transactions using Cursors."""
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        out_count = cursor.var(oracledb.NUMBER)
        cursor.callproc("generate_recurring_transactions", [out_count])
        conn.commit()
        cnt = int(out_count.getvalue())
        flash(f"Procedure Executed: Successfully auto-logged {cnt} due payment(s) via PL/SQL Cursor!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error running recurring procedure: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('recurring'))

@app.route('/predictions')
def predictions():
    user = get_current_user()
    current_date = datetime.now()
    # Target next month
    if current_date.month == 12:
        next_month = f"{current_date.year + 1}-01"
    else:
        next_month = f"{current_date.year}-{current_date.month + 1:02d}"

    # 1. Existing predictions in table
    pred_list = db.query_all("""
        SELECT p.prediction_id, p.month, p.predicted_amount, p.method, c.category_name
        FROM Predictions p
        JOIN Categories c ON p.category_id = c.category_id
        WHERE p.user_id = :usr_id
        ORDER BY p.month DESC, p.predicted_amount DESC
    """, {'usr_id': user['id']})

    # 2. Window Function Trend Analysis (Directly demonstrating SQL analytic function)
    window_data = db.query_all("""
        SELECT 
            c.category_name,
            month_str,
            monthly_sum,
            ROUND(AVG(monthly_sum) OVER (
                PARTITION BY c.category_id 
                ORDER BY month_str 
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ), 2) AS moving_avg_3m
        FROM (
            SELECT 
                t.category_id,
                TO_CHAR(t.txn_date, 'YYYY-MM') AS month_str,
                SUM(t.amount) AS monthly_sum
            FROM Transactions t
            JOIN Accounts a ON t.account_id = a.account_id
            WHERE a.user_id = :usr_id AND t.txn_type = 'Debit'
            GROUP BY t.category_id, TO_CHAR(t.txn_date, 'YYYY-MM')
        ) s
        JOIN Categories c ON s.category_id = c.category_id
        ORDER BY c.category_name, month_str ASC
    """, {'usr_id': user['id']})

    return render_template(
        'predictions.html',
        predictions=pred_list,
        window_trends=window_data,
        target_month=next_month
    )

@app.route('/predictions/generate', methods=['POST'])
def generate_predictions_procedure():
    user = get_current_user()
    target_month = request.form.get('target_month')

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        out_count = cursor.var(oracledb.NUMBER)
        cursor.callproc("generate_monthly_predictions", [user['id'], target_month, out_count])
        conn.commit()
        cnt = int(out_count.getvalue())
        flash(f"Predictions Generated: Successfully forecasted spending for {cnt} categories using SQL Window Moving Averages!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error generating predictions: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('predictions'))

@app.route('/alerts/dismiss/<int:alert_id>', methods=['POST'])
def dismiss_alert(alert_id):
    db.execute_dml("UPDATE Alerts SET is_read = 1 WHERE alert_id = :aid", {'aid': alert_id})
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/admin')
def admin_portal():
    user = get_current_user()
    if not user or user.get('role') != 'ADMIN':
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for('dashboard'))

    # 1. System Summary Metrics (Strictly non-monetary system telemetry)
    stats = db.query_one("""
        SELECT 
            (SELECT COUNT(*) FROM Users) AS total_users,
            (SELECT COUNT(*) FROM Accounts) AS total_accounts,
            (SELECT COUNT(*) FROM Transactions) AS total_txns
        FROM DUAL
    """)

    # 2. Privacy-Masked User Directory (NO user balances selected or exposed!)
    raw_users = db.query_all("""
        SELECT 
            u.user_id,
            u.name,
            u.email,
            u.role,
            TO_CHAR(u.created_at, 'YYYY-MM-DD') AS join_date,
            COUNT(a.account_id) AS account_count
        FROM Users u
        LEFT JOIN Accounts a ON u.user_id = a.user_id
        GROUP BY u.user_id, u.name, u.email, u.role, TO_CHAR(u.created_at, 'YYYY-MM-DD')
        ORDER BY u.user_id ASC
    """)

    masked_users = []
    for u in raw_users:
        is_self = (u['user_id'] == user['id'])
        masked_users.append({
            'user_id': u['user_id'],
            'display_name': u['name'] if is_self else mask_name(u['name']),
            'raw_name': u['name'],
            'display_email': u['email'] if is_self else mask_email(u['email']),
            'raw_email': u['email'],
            'role': u['role'],
            'join_date': u['join_date'],
            'account_count': u['account_count'],
            'is_masked': not is_self,
            'is_self': is_self
        })

    # 3. System Security & Budget Trigger Audit
    system_alerts = db.query_all("""
        SELECT alert_id, user_id, message, alert_type, TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS alert_time
        FROM Alerts
        ORDER BY created_at DESC
        FETCH FIRST 8 ROWS ONLY
    """)

    return render_template(
        'admin.html',
        stats=stats,
        users=masked_users,
        system_alerts=system_alerts
    )

@app.route('/admin/users/create', methods=['POST'])
def admin_create_user():
    user = get_current_user()
    if not user or user.get('role') != 'ADMIN':
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for('login'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'USER').strip().upper()

    if not name or not email or not password:
        flash("All fields (Full Name, Email Address, Password) are required.", "danger")
        return redirect(url_for('admin_portal'))

    if role not in ('USER', 'ADMIN'):
        role = 'USER'

    existing = db.query_one("SELECT user_id FROM Users WHERE email = :email", {'email': email})
    if existing:
        flash(f"Account creation failed: Email '{email}' is already registered in the system.", "danger")
        return redirect(url_for('admin_portal'))

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        user_id_var = cursor.var(oracledb.NUMBER)
        cursor.execute(
            "INSERT INTO Users (name, email, password_hash, role) VALUES (:1, :2, :3, :4) RETURNING user_id INTO :5",
            [name, email, hashed_pw, role, user_id_var]
        )
        new_uid = int(user_id_var.getvalue()[0])

        # If regular consumer user, provision a default Savings Account
        if role == 'USER':
            cursor.execute(
                "INSERT INTO Accounts (user_id, account_type, balance, status) VALUES (:1, 'Savings', 0.00, 'Active')",
                [new_uid]
            )
        conn.commit()
        flash(f"Successfully created account for '{name}' (User ID: #USR-{new_uid:04d}) with role '{role}'.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Database error creating user: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_portal'))

@app.route('/admin/users/toggle-role/<int:target_user_id>', methods=['POST'])
def admin_toggle_role(target_user_id):
    user = get_current_user()
    if not user or user.get('role') != 'ADMIN':
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for('login'))

    if target_user_id == user['id']:
        flash("Security policy violation: You cannot alter your own administrative role.", "warning")
        return redirect(url_for('admin_portal'))

    target = db.query_one("SELECT user_id, name, role FROM Users WHERE user_id = :target_id", {'target_id': target_user_id})
    if not target:
        flash("Target user account not found.", "danger")
        return redirect(url_for('admin_portal'))

    new_role = 'ADMIN' if target['role'] == 'USER' else 'USER'
    try:
        db.execute_dml("UPDATE Users SET role = :r WHERE user_id = :target_id", {'r': new_role, 'target_id': target_user_id})
        flash(f"Role updated successfully: User '{target['name']}' (#USR-{target_user_id:04d}) is now an '{new_role}'.", "success")
    except Exception as e:
        flash(f"Failed to change role: {str(e)}", "danger")

    return redirect(url_for('admin_portal'))

@app.route('/admin/users/delete/<int:target_user_id>', methods=['POST'])
def admin_delete_user(target_user_id):
    user = get_current_user()
    if not user or user.get('role') != 'ADMIN':
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for('login'))

    if target_user_id == user['id']:
        flash("Security policy violation: You cannot delete your own active administrator account.", "danger")
        return redirect(url_for('admin_portal'))

    target = db.query_one("SELECT user_id, name FROM Users WHERE user_id = :target_id", {'target_id': target_user_id})
    if not target:
        flash("Target user account not found or already removed.", "danger")
        return redirect(url_for('admin_portal'))

    try:
        # All associated records (accounts, transactions, recurring, budgets, alerts, predictions)
        # are automatically cascade deleted by Oracle ON DELETE CASCADE foreign keys.
        db.execute_dml("DELETE FROM Users WHERE user_id = :target_id", {'target_id': target_user_id})
        flash(f"User '{target['name']}' (#USR-{target_user_id:04d}) and all relational records were permanently deleted via ON DELETE CASCADE.", "success")
    except Exception as e:
        flash(f"Failed to delete user: {str(e)}", "danger")

    return redirect(url_for('admin_portal'))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)

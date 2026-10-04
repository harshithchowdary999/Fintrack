# Personal Finance Management with Spending Prediction

**University DBMS Project**  
- **K. Harshith** — `BL.SC.U4AIE24125`
- **P. Manideep** — `BL.SC.U4AIE24162`
- **K. Rishvik** — `BL.SC.U4AIE24126`

**Database Engine:** Oracle Database 19c Enterprise Edition (PDB: `ORCLPDB`)  
**Backend:** Python 3 + Flask  
**Database Driver:** `python-oracledb` (Thin mode, native connection)

---

## 1. Project Overview & Objective

Most personal finance tools only report static past expenditures. This project designs and implements a **Third Normal Form (3NF) relational database** in **Oracle 19c** to manage accounts, transactions, multi-month budgets, and automated recurring payments.

On top of this normalized schema, the system applies **SQL Analytic Window Functions** (`AVG() OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN ...)`) to compute 3-month rolling averages and forecast next-month category spending directly on the database engine.

---

## 2. Relational Schema (3NF Normalization)

The database consists of 7 normalized entities with primary keys, foreign keys, and strict integrity constraints:

1. **`Users`** (`user_id` PK, `name`, `email` UNIQUE, `password_hash`, `role`, `created_at`)
   - *Constraint:* `CHECK (role IN ('ADMIN', 'USER'))`
2. **`Accounts`** (`account_id` PK, `user_id` FK -> Users, `account_type`, `balance`, `status`, `opened_at`)
   - *Constraints:* `CHECK (account_type IN ('Savings', 'Current', 'Credit', 'Wallet'))`, `CHECK (status IN ('Active', 'Frozen'))`
3. **`Categories`** (`category_id` PK, `category_name` UNIQUE, `type`)
   - *Constraint:* `CHECK (type IN ('Income', 'Expense'))`
4. **`Transactions`** (`transaction_id` PK, `account_id` FK -> Accounts, `category_id` FK -> Categories, `amount`, `txn_type`, `txn_date`, `vendor`, `description`)
   - *Constraints:* `CHECK (amount > 0)`, `CHECK (txn_type IN ('Credit', 'Debit'))`
5. **`Budgets`** (`budget_id` PK, `user_id` FK -> Users, `category_id` FK -> Categories, `month`, `limit_amount`)
   - *Constraints:* `CHECK (limit_amount > 0)`, `UNIQUE (user_id, category_id, month)`
6. **`RecurringPayments`** (`recurring_id` PK, `account_id` FK -> Accounts, `category_id` FK -> Categories, `amount`, `frequency`, `next_due_date`)
   - *Constraints:* `CHECK (amount > 0)`, `CHECK (frequency IN ('Weekly', 'Monthly', 'Yearly'))`
7. **`Predictions`** (`prediction_id` PK, `user_id` FK -> Users, `category_id` FK -> Categories, `month`, `predicted_amount`, `method`)
   - *Constraints:* `UNIQUE (user_id, category_id, month)`
8. **`Alerts`** (`alert_id` PK, `user_id` FK -> Users, `message`, `alert_type`, `is_read`, `created_at`)
   - Trigger-populated notification table for real-time budget overrun warnings.

---

## 3. Advanced DBMS Features Implemented

| DBMS Feature | Implementation in Oracle 19c | Purpose |
| :--- | :--- | :--- |
| **Triggers** | `trg_update_account_balance` | Automatically adjusts `Accounts.balance` on `INSERT` or `DELETE` on `Transactions`. |
| **Compound Trigger** | `trg_check_budget_overrun` | Evaluates total monthly category debit spend vs allocated budget limit without mutating table errors; logs warnings to `Alerts`. |
| **Stored Procedure** | `transfer_funds` | Full **ACID** guarantee: locks row with `FOR UPDATE`, validates balance, debits source & credits destination, commits or rolls back on exception. |
| **PL/SQL Cursors** | `generate_recurring_transactions` | Declares explicit cursor for due payments (`next_due_date <= SYSDATE`), generates transaction records, and increments due date using `ADD_MONTHS`. |
| **Stored Function** | `get_monthly_total` | Returns aggregated spend for a user in a given month (`YYYY-MM`). |
| **Database Views** | `v_monthly_category_summary`, `v_budget_vs_actual` | Joins budgets with dynamic monthly debit sums, calculating remaining budget and status (`ON_TRACK`, `WARNING`, `EXCEEDED`). |
| **Window Functions** | `AVG() OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` | Computes moving averages of category expenditure across past months to populate `Predictions`. |
| **B-Tree Indexes** | `idx_txn_acc_date`, `idx_txn_cat`, `idx_txn_vendor`, `idx_budget_user_month`, `idx_recurring_due` | Optimizes date-range transaction ledger filtering, vendor lookups, and budget joins with logarithmic lookup cost. |

---

## 4. File Structure (Organized & Simple)

```
DBMS_project/
├── app.py                      # Flask Web Application routes and controller logic
├── config.py                   # Oracle 19c connection parameters (DSN, port, user)
├── db.py                       # Reusable Oracle 19c query, procedure & function helpers
├── init_db.py                  # One-click database schema, views, triggers & seed installer
├── test_plsql.py               # Comprehensive CLI test script for all PL/SQL objects
├── requirements.txt            # Python dependencies (flask, oracledb, bcrypt)
├── sql/                        # Raw standalone SQL & PL/SQL source scripts
│   ├── 01_schema.sql           # DDL table creation and constraints
│   ├── 02_views.sql            # v_monthly_category_summary and v_budget_vs_actual
│   ├── 03_procedures.sql       # transfer_funds, generate_recurring_transactions, functions
│   ├── 04_triggers.sql         # trg_update_account_balance, trg_check_budget_overrun
│   ├── 05_seed.sql             # Realistic multi-month sample transactions and budgets
│   └── 06_window_prediction.sql# Analytical SQL query for trend forecasting
├── static/
│   └── css/style.css           # Clean, professional, human-designed UI stylesheet
└── templates/                  # Human-organized, responsive Jinja2 templates
    ├── base.html               # Base layout with navigation and alerts
    ├── index.html              # Main dashboard (metrics, charts, recent activity)
    ├── accounts.html           # Account cards & creation modal
    ├── transactions.html       # Filterable transaction ledger & recording modal
    ├── transfer.html           # Interactive ACID fund transfer demonstration
    ├── budgets.html            # Category budget health from database view
    ├── recurring.html          # Subscriptions & one-click Cursor procedure execution
    ├── predictions.html        # Window function moving average forecasts & charts
    ├── login.html              # Clean sign-in page
    └── register.html           # New user registration page
```

---

## 5. How to Run the Project

### Prerequisites:
- Oracle Database 19c running on `localhost:1521` (Service: `orclpdb`)
- Python 3.10+ installed

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Initialize / Reset Oracle Database (if needed)
```bash
python init_db.py
```
*This drops and re-creates all tables, views, triggers, stored procedures, and loads 4 months of realistic transaction data.*

### Step 3: Run the Web Application
```bash
python app.py
```
Open your browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

### Demo Login Credentials:
- **Regular User:** `harshith@example.com` &bull; Password: `pass123`
- **Administrator:** `admin@fintrack.com` &bull; Password: `admin123`

---

## 6. Data Privacy & RBAC (Role-Based Access Control)

To satisfy modern financial data privacy standards (GDPR, PCI-DSS):
- **Role Separation:** Enforced at the schema level (`CHECK (role IN ('ADMIN', 'USER'))`).
- **Data Masking:** Administrators have platform-level visibility (liquidity, transaction throughput, active accounts), but **sensitive personal identifiable information (PII) is masked with asterisks**:
  - Email: `h******h@example.com`
  - Name: `H******h K`
  - Passwords: Encrypted with Bcrypt and completely inaccessible to administrators.
  - Personal Bank Cards & Specific Receipts: Hidden from administrative inspection to preserve user privacy.

---

## 7. Viva Demonstration Guide

1. **ACID Demonstration (`/transfer`):**
   - Transfer ₹5,000 from Savings to Current: Observe atomic balance update on both accounts.
   - Attempt to transfer ₹999,999: Observe `ORA-20005: Insufficient balance` rollback without partial state corruption.
2. **Trigger Demonstration (`/transactions`):**
   - Record an expense transaction: Watch the account balance update automatically via `trg_update_account_balance`.
   - If the expense pushes a category spend over its monthly limit, see `trg_check_budget_overrun` generate an alert banner.
3. **PL/SQL Cursor Demonstration (`/recurring`):**
   - Click **"Process Due Payments"**: The `generate_recurring_transactions` procedure scans due entries with a cursor, logs the transactions, and advances `next_due_date`.
4. **Window Function Predictions (`/predictions`):**
   - Click **"Compute Forecast"**: The procedure evaluates `AVG(...) OVER (...)` across preceding months to project the next month's spending.
5. **Admin Privacy Console (`/admin`):**
   - Log in as `admin@fintrack.com` / `admin123`: Review platform health and verified asterisks-masked user privacy directory.

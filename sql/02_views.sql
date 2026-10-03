-- ====================================================================
-- Project: Personal Finance Management with Spending Prediction
-- File: 02_views.sql
-- Description: Database views for reporting and budget monitoring
-- ====================================================================

-- 1. Monthly Category Summary View
-- Aggregates transactions by user, category, and month
CREATE OR REPLACE VIEW v_monthly_category_summary AS
SELECT 
    a.user_id,
    c.category_id,
    c.category_name,
    c.type AS category_type,
    TO_CHAR(t.txn_date, 'YYYY-MM') AS month,
    SUM(t.amount) AS total_amount,
    COUNT(t.transaction_id) AS txn_count
FROM Transactions t
JOIN Accounts a ON t.account_id = a.account_id
JOIN Categories c ON t.category_id = c.category_id
GROUP BY 
    a.user_id, 
    c.category_id, 
    c.category_name, 
    c.type, 
    TO_CHAR(t.txn_date, 'YYYY-MM');

-- 2. Budget vs Actual Spending View
-- Compares allocated category limits against real-time actual debits
CREATE OR REPLACE VIEW v_budget_vs_actual AS
SELECT 
    b.budget_id,
    b.user_id,
    b.category_id,
    c.category_name,
    b.month,
    b.limit_amount,
    NVL(actual.total_spent, 0) AS actual_spent,
    (b.limit_amount - NVL(actual.total_spent, 0)) AS remaining_amount,
    CASE 
        WHEN NVL(actual.total_spent, 0) > b.limit_amount THEN 'EXCEEDED'
        WHEN NVL(actual.total_spent, 0) >= (0.85 * b.limit_amount) THEN 'WARNING'
        ELSE 'ON_TRACK'
    END AS status,
    ROUND(CASE 
        WHEN b.limit_amount > 0 THEN (NVL(actual.total_spent, 0) / b.limit_amount) * 100 
        ELSE 0 
    END, 2) AS percent_used
FROM Budgets b
JOIN Categories c ON b.category_id = c.category_id
LEFT JOIN (
    SELECT 
        a.user_id,
        t.category_id,
        TO_CHAR(t.txn_date, 'YYYY-MM') AS month,
        SUM(t.amount) AS total_spent
    FROM Transactions t
    JOIN Accounts a ON t.account_id = a.account_id
    WHERE t.txn_type = 'Debit'
    GROUP BY a.user_id, t.category_id, TO_CHAR(t.txn_date, 'YYYY-MM')
) actual ON b.user_id = actual.user_id 
        AND b.category_id = actual.category_id 
        AND b.month = actual.month;

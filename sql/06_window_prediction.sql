-- ====================================================================
-- Project: Personal Finance Management with Spending Prediction
-- File: 06_window_prediction.sql
-- Description: SQL Analytic Window Functions for Trend Analysis
--              and Moving Average Spending Prediction
-- ====================================================================

-- Demonstrates Window Function: AVG() OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN ...)
-- Computes the 3-month rolling average for every spending category
SELECT 
    category_id,
    category_name,
    month_str AS spending_month,
    monthly_sum AS actual_month_spend,
    ROUND(AVG(monthly_sum) OVER (
        PARTITION BY category_id 
        ORDER BY month_str 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_3month_avg,
    ROUND(monthly_sum - AVG(monthly_sum) OVER (
        PARTITION BY category_id 
        ORDER BY month_str 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS variance_from_trend
FROM (
    SELECT 
        c.category_id,
        c.category_name,
        TO_CHAR(t.txn_date, 'YYYY-MM') AS month_str,
        SUM(t.amount) AS monthly_sum
    FROM Transactions t
    JOIN Accounts a ON t.account_id = a.account_id
    JOIN Categories c ON t.category_id = c.category_id
    WHERE a.user_id = 1
      AND t.txn_type = 'Debit'
    GROUP BY c.category_id, c.category_name, TO_CHAR(t.txn_date, 'YYYY-MM')
)
ORDER BY category_name, month_str;

-- ====================================================================
-- Project: Personal Finance Management with Spending Prediction
-- File: 03_procedures.sql
-- Description: Stored Procedures & Functions (ACID Fund Transfer,
--              Cursor-based Recurring Auto-Log, Monthly Total Function,
--              and Window-Function Predictions)
-- ====================================================================

-- 1. Function: get_monthly_total
-- Returns the total expense (Debit) for a given user and month ('YYYY-MM')
CREATE OR REPLACE FUNCTION get_monthly_total (
    p_user_id IN NUMBER,
    p_month   IN VARCHAR2
) RETURN NUMBER
IS
    v_total NUMBER(12,2) := 0;
BEGIN
    SELECT NVL(SUM(t.amount), 0)
    INTO v_total
    FROM Transactions t
    JOIN Accounts a ON t.account_id = a.account_id
    WHERE a.user_id = p_user_id
      AND t.txn_type = 'Debit'
      AND TO_CHAR(t.txn_date, 'YYYY-MM') = p_month;

    RETURN v_total;
EXCEPTION
    WHEN OTHERS THEN
        RETURN 0;
END;
/

-- 2. Stored Procedure: transfer_funds
-- Demonstrates ACID properties (Atomicity, Consistency, Isolation, Durability)
-- Transfers money between two accounts with balance validation and rollback.
CREATE OR REPLACE PROCEDURE transfer_funds (
    p_from_account IN NUMBER,
    p_to_account   IN NUMBER,
    p_amount       IN NUMBER,
    p_description  IN VARCHAR2,
    p_out_status   OUT VARCHAR2
)
IS
    v_from_balance NUMBER(12,2);
    v_cat_id       NUMBER;
    v_from_user    NUMBER;
    v_to_user      NUMBER;
BEGIN
    -- Validation 1: Amount must be strictly positive
    IF p_amount <= 0 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Transfer amount must be greater than zero.');
    END IF;

    -- Validation 2: Source and destination must be distinct accounts
    IF p_from_account = p_to_account THEN
        RAISE_APPLICATION_ERROR(-20002, 'Source and destination accounts must be different.');
    END IF;

    -- Validation 3: Verify source account exists and lock row for update (Isolation)
    BEGIN
        SELECT balance, user_id INTO v_from_balance, v_from_user
        FROM Accounts
        WHERE account_id = p_from_account
        FOR UPDATE;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20003, 'Source account does not exist.');
    END;

    -- Validation 4: Verify destination account exists
    BEGIN
        SELECT user_id INTO v_to_user
        FROM Accounts
        WHERE account_id = p_to_account;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20004, 'Destination account does not exist.');
    END;

    -- Validation 5: Sufficient balance check (Atomicity & Consistency guarantee)
    IF v_from_balance < p_amount THEN
        RAISE_APPLICATION_ERROR(-20005, 'Insufficient balance in source account. Current balance: ' || v_from_balance);
    END IF;

    -- Find or create a 'Transfer' category
    BEGIN
        SELECT category_id INTO v_cat_id 
        FROM Categories 
        WHERE category_name = 'Transfer' AND ROWNUM = 1;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            INSERT INTO Categories (category_name, type) 
            VALUES ('Transfer', 'Expense')
            RETURNING category_id INTO v_cat_id;
    END;

    -- Insert Debit transaction for Source Account (Trigger automatically reduces source balance)
    INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
    VALUES (
        p_from_account, 
        v_cat_id, 
        p_amount, 
        'Debit', 
        SYSDATE, 
        NVL(p_description, 'Fund Transfer to Acc #' || p_to_account)
    );

    -- Insert Credit transaction for Destination Account (Trigger automatically increases destination balance)
    INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
    VALUES (
        p_to_account, 
        v_cat_id, 
        p_amount, 
        'Credit', 
        SYSDATE, 
        NVL(p_description, 'Fund Transfer from Acc #' || p_from_account)
    );

    -- Commit transaction to persist all changes atomically
    COMMIT;
    p_out_status := 'SUCCESS: Transferred ' || TO_CHAR(p_amount, 'FM999,999,990.00') || ' successfully.';

EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        p_out_status := 'FAILED: ' || SQLERRM;
        RAISE;
END;
/

-- 3. Stored Procedure: generate_recurring_transactions
-- Uses a PL/SQL CURSOR to iterate through due subscriptions and EMIs,
-- records transactions, and updates the next due date.
CREATE OR REPLACE PROCEDURE generate_recurring_transactions (
    p_out_count OUT NUMBER
)
IS
    CURSOR cur_recurring IS
        SELECT recurring_id, account_id, category_id, amount, frequency, next_due_date
        FROM RecurringPayments
        WHERE TRUNC(next_due_date) <= TRUNC(SYSDATE)
        FOR UPDATE;

    v_count NUMBER := 0;
    v_next_date DATE;
    v_cat_name VARCHAR2(60);
BEGIN
    FOR rec IN cur_recurring LOOP
        -- Retrieve category name for transaction description
        SELECT category_name INTO v_cat_name
        FROM Categories WHERE category_id = rec.category_id;

        -- 1. Create transaction entry
        INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
        VALUES (
            rec.account_id,
            rec.category_id,
            rec.amount,
            'Debit',
            SYSDATE,
            'Auto-Recurring: ' || v_cat_name || ' (' || rec.frequency || ')'
        );

        -- 2. Compute next due date based on frequency
        IF UPPER(rec.frequency) = 'WEEKLY' THEN
            v_next_date := rec.next_due_date + 7;
        ELSIF UPPER(rec.frequency) = 'YEARLY' THEN
            v_next_date := ADD_MONTHS(rec.next_due_date, 12);
        ELSE -- Default to Monthly
            v_next_date := ADD_MONTHS(rec.next_due_date, 1);
        END IF;

        -- 3. Update the recurring payment schedule
        UPDATE RecurringPayments
        SET next_due_date = v_next_date
        WHERE CURRENT OF cur_recurring;

        v_count := v_count + 1;
    END LOOP;

    COMMIT;
    p_out_count := v_count;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        p_out_count := 0;
        RAISE;
END;
/

-- 4. Stored Procedure: generate_monthly_predictions
-- Uses Window Function (Moving Average over preceding months) to forecast
-- category-wise spending for the upcoming month and writes to Predictions table.
CREATE OR REPLACE PROCEDURE generate_monthly_predictions (
    p_user_id      IN NUMBER,
    p_target_month IN VARCHAR2, -- e.g. '2026-11'
    p_out_count    OUT NUMBER
)
IS
    v_count NUMBER := 0;
BEGIN
    -- Upsert moving average forecast into Predictions table using SQL Window Function
    MERGE INTO Predictions p
    USING (
        WITH MonthlySpend AS (
            SELECT 
                a.user_id,
                t.category_id,
                TO_CHAR(t.txn_date, 'YYYY-MM') AS month_str,
                SUM(t.amount) AS monthly_sum
            FROM Transactions t
            JOIN Accounts a ON t.account_id = a.account_id
            WHERE a.user_id = p_user_id
              AND t.txn_type = 'Debit'
            GROUP BY a.user_id, t.category_id, TO_CHAR(t.txn_date, 'YYYY-MM')
        ),
        MovingAverages AS (
            SELECT 
                user_id,
                category_id,
                month_str,
                ROUND(AVG(monthly_sum) OVER (
                    PARTITION BY user_id, category_id 
                    ORDER BY month_str 
                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                ), 2) AS moving_avg_spend,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id, category_id 
                    ORDER BY month_str DESC
                ) AS rn
            FROM MonthlySpend
        )
        SELECT 
            user_id,
            category_id,
            p_target_month AS month,
            moving_avg_spend AS predicted_amount,
            'moving_avg_3m' AS method
        FROM MovingAverages
        WHERE rn = 1
    ) src
    ON (p.user_id = src.user_id AND p.category_id = src.category_id AND p.month = src.month)
    WHEN MATCHED THEN
        UPDATE SET 
            p.predicted_amount = src.predicted_amount,
            p.method = src.method
    WHEN NOT MATCHED THEN
        INSERT (user_id, category_id, month, predicted_amount, method)
        VALUES (src.user_id, src.category_id, src.month, src.predicted_amount, src.method);

    v_count := SQL%ROWCOUNT;
    COMMIT;
    p_out_count := v_count;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        p_out_count := 0;
        RAISE;
END;
/

-- ====================================================================
-- Project: Personal Finance Management with Spending Prediction
-- File: 04_triggers.sql
-- Description: Triggers for automatic balance updates and budget monitoring
-- ====================================================================

-- 1. Trigger: trg_update_account_balance
-- Keeps Accounts.balance denormalized and synchronized automatically
-- whenever a transaction is inserted or deleted.
CREATE OR REPLACE TRIGGER trg_update_account_balance
AFTER INSERT OR DELETE ON Transactions
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        IF :NEW.txn_type = 'Credit' THEN
            UPDATE Accounts 
            SET balance = balance + :NEW.amount 
            WHERE account_id = :NEW.account_id;
        ELSIF :NEW.txn_type = 'Debit' THEN
            UPDATE Accounts 
            SET balance = balance - :NEW.amount 
            WHERE account_id = :NEW.account_id;
        END IF;
    ELSIF DELETING THEN
        BEGIN
            IF :OLD.txn_type = 'Credit' THEN
                UPDATE Accounts 
                SET balance = balance - :OLD.amount 
                WHERE account_id = :OLD.account_id;
            ELSIF :OLD.txn_type = 'Debit' THEN
                UPDATE Accounts 
                SET balance = balance + :OLD.amount 
                WHERE account_id = :OLD.account_id;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                -- If parent Account is being cascade-deleted, suppress mutating table exception
                NULL;
        END;
    END IF;
END;
/

-- 2. Compound Trigger: trg_check_budget_overrun
-- Solves mutating table restriction in Oracle while monitoring budget limits.
-- Collects newly inserted debit transactions, checks total spend vs budget limit,
-- and logs an alert if limit is exceeded.
CREATE OR REPLACE TRIGGER trg_check_budget_overrun
FOR INSERT ON Transactions
COMPOUND TRIGGER

    TYPE t_txn_record IS RECORD (
        account_id   Transactions.account_id%TYPE,
        category_id  Transactions.category_id%TYPE,
        txn_date     Transactions.txn_date%TYPE,
        txn_type     Transactions.txn_type%TYPE
    );
    TYPE t_txn_list IS TABLE OF t_txn_record INDEX BY PLS_INTEGER;
    g_txns t_txn_list;
    g_count PLS_INTEGER := 0;

    AFTER EACH ROW IS
    BEGIN
        IF :NEW.txn_type = 'Debit' THEN
            g_count := g_count + 1;
            g_txns(g_count).account_id := :NEW.account_id;
            g_txns(g_count).category_id := :NEW.category_id;
            g_txns(g_count).txn_date := :NEW.txn_date;
            g_txns(g_count).txn_type := :NEW.txn_type;
        END IF;
    END AFTER EACH ROW;

    AFTER STATEMENT IS
        v_user_id      NUMBER;
        v_month        VARCHAR2(7);
        v_total_spent  NUMBER(12,2);
        v_limit        NUMBER(12,2);
        v_cat_name     VARCHAR2(60);
        v_alert_exists NUMBER;
    BEGIN
        FOR i IN 1..g_count LOOP
            -- Determine the user owning the account
            BEGIN
                SELECT user_id INTO v_user_id
                FROM Accounts WHERE account_id = g_txns(i).account_id;
            EXCEPTION
                WHEN NO_DATA_FOUND THEN CONTINUE;
            END;

            v_month := TO_CHAR(g_txns(i).txn_date, 'YYYY-MM');

            -- Retrieve the category budget limit for this month
            BEGIN
                SELECT b.limit_amount, c.category_name
                INTO v_limit, v_cat_name
                FROM Budgets b
                JOIN Categories c ON b.category_id = c.category_id
                WHERE b.user_id = v_user_id
                  AND b.category_id = g_txns(i).category_id
                  AND b.month = v_month;
            EXCEPTION
                WHEN NO_DATA_FOUND THEN
                    CONTINUE; -- No budget set for this category
            END;

            -- Calculate total debit spending in this category for the month
            SELECT NVL(SUM(t.amount), 0)
            INTO v_total_spent
            FROM Transactions t
            JOIN Accounts a ON t.account_id = a.account_id
            WHERE a.user_id = v_user_id
              AND t.category_id = g_txns(i).category_id
              AND t.txn_type = 'Debit'
              AND TO_CHAR(t.txn_date, 'YYYY-MM') = v_month;

            -- If spend exceeds limit, check if alert was already logged today
            IF v_total_spent > v_limit THEN
                SELECT COUNT(*) INTO v_alert_exists
                FROM Alerts
                WHERE user_id = v_user_id
                  AND message LIKE '%' || v_cat_name || '%' || v_month || '%'
                  AND TRUNC(created_at) = TRUNC(SYSDATE);

                IF v_alert_exists = 0 THEN
                    INSERT INTO Alerts (user_id, message, alert_type, is_read, created_at)
                    VALUES (
                        v_user_id,
                        'Budget Overrun: Category "' || v_cat_name || '" reached ' || 
                        TO_CHAR(v_total_spent, 'FM999,990.00') || ' exceeding limit of ' || 
                        TO_CHAR(v_limit, 'FM999,990.00') || ' for ' || v_month || '.',
                        'BUDGET_OVERRUN',
                        0,
                        SYSDATE
                    );
                END IF;
            END IF;
        END LOOP;

        -- Reset state
        g_count := 0;
        g_txns.DELETE;
    END AFTER STATEMENT;

END trg_check_budget_overrun;
/

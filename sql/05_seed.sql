-- ====================================================================
-- Project: Personal Finance Management with Spending Prediction
-- File: 05_seed.sql
-- Description: Realistic seed data for categories, users, accounts,
--              historical transactions (for window function trend),
--              budgets, and recurring payments.
-- ====================================================================

-- 1. Categories
INSERT INTO Categories (category_name, type) VALUES ('Salary', 'Income');
INSERT INTO Categories (category_name, type) VALUES ('Freelancing', 'Income');
INSERT INTO Categories (category_name, type) VALUES ('Investments', 'Income');
INSERT INTO Categories (category_name, type) VALUES ('Groceries', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Food & Dining', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Rent & Housing', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Utilities', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Transportation', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Entertainment', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Healthcare', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Subscriptions', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Shopping', 'Expense');
INSERT INTO Categories (category_name, type) VALUES ('Transfer', 'Expense');

-- 2. Users (Password is 'pass123' for regular users, 'admin123' for admin)
INSERT INTO Users (name, email, password_hash, role) 
VALUES ('Harshith K', 'harshith@example.com', '$2b$12$5KyFFZYZtfTSq45nbEpin.Y0tiLRf6xB/4VUNzyKI4kssKXeSQIoK', 'USER');

INSERT INTO Users (name, email, password_hash, role) 
VALUES ('Manideep P', 'manideep@example.com', '$2b$12$5KyFFZYZtfTSq45nbEpin.Y0tiLRf6xB/4VUNzyKI4kssKXeSQIoK', 'USER');

INSERT INTO Users (name, email, password_hash, role) 
VALUES ('Rishvik K', 'rishvik@example.com', '$2b$12$5KyFFZYZtfTSq45nbEpin.Y0tiLRf6xB/4VUNzyKI4kssKXeSQIoK', 'USER');

INSERT INTO Users (name, email, password_hash, role) 
VALUES ('System Administrator', 'admin@fintrack.com', '$2b$12$ZuJLjWbBvnJWsntSXKXJy.c6UK6GRPe0ZlEm60VaBTpUxYmDDyQBy', 'ADMIN');

-- 3. Accounts for User 1 (Harshith)
-- Note: Balances start at 0.00 and are updated dynamically by trg_update_account_balance
INSERT INTO Accounts (user_id, account_type, balance, opened_at) 
VALUES (1, 'Savings', 0.00, DATE '2026-06-01');

INSERT INTO Accounts (user_id, account_type, balance, opened_at) 
VALUES (1, 'Current', 0.00, DATE '2026-06-01');

INSERT INTO Accounts (user_id, account_type, balance, opened_at) 
VALUES (1, 'Wallet', 0.00, DATE '2026-06-01');

-- Accounts for User 2 (Manideep)
INSERT INTO Accounts (user_id, account_type, balance, opened_at) 
VALUES (2, 'Savings', 0.00, DATE '2026-06-01');

-- 4. Initial Credits / Salaries (Trigger automatically adds to account balances)
-- Category 1 = Salary
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 1, 75000.00, 'Credit', DATE '2026-07-01', 'Monthly Salary July');

INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 1, 75000.00, 'Credit', DATE '2026-08-01', 'Monthly Salary August');

INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 1, 75000.00, 'Credit', DATE '2026-09-01', 'Monthly Salary September');

INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 1, 75000.00, 'Credit', DATE '2026-10-01', 'Monthly Salary October');

-- Current Account credit
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (2, 2, 25000.00, 'Credit', DATE '2026-09-15', 'Freelance Project Payout');

-- Wallet credit
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (3, 1, 5000.00, 'Credit', DATE '2026-10-01', 'Wallet Top-up from Bank');

-- 5. Historical Multi-Month Debits for Harshith (Account 1)
-- Categories: 4=Groceries, 5=Food & Dining, 6=Rent, 7=Utilities, 8=Transport, 9=Entertainment, 11=Subscriptions

-- July 2026 Expenses
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 6, 20000.00, 'Debit', DATE '2026-07-02', 'Apartment Rent July');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 4, 6200.00, 'Debit', DATE '2026-07-05', 'Monthly Supermarket Groceries');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 5, 3100.00, 'Debit', DATE '2026-07-12', 'Weekend Dining & Outing');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 7, 2400.00, 'Debit', DATE '2026-07-15', 'Electricity & Water Bill');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 8, 1800.00, 'Debit', DATE '2026-07-20', 'Fuel & Metro card refill');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 9, 1500.00, 'Debit', DATE '2026-07-25', 'Movie tickets and bowling');

-- August 2026 Expenses
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 6, 20000.00, 'Debit', DATE '2026-08-02', 'Apartment Rent August');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 4, 6800.00, 'Debit', DATE '2026-08-06', 'Supermarket & Organic Mart');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 5, 3900.00, 'Debit', DATE '2026-08-14', 'Family Restaurant Dinner');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 7, 2600.00, 'Debit', DATE '2026-08-16', 'Electricity & Gas Utility');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 8, 2100.00, 'Debit', DATE '2026-08-22', 'Cab & Petrol');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 9, 2000.00, 'Debit', DATE '2026-08-28', 'Music Concert entry');

-- September 2026 Expenses
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 6, 20000.00, 'Debit', DATE '2026-09-02', 'Apartment Rent September');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 4, 7100.00, 'Debit', DATE '2026-09-07', 'Wholesale Grocery Supplies');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 5, 4200.00, 'Debit', DATE '2026-09-18', 'Dinner & Cafe Coffee');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 7, 2800.00, 'Debit', DATE '2026-09-19', 'Power Grid Utility Bill');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 8, 1950.00, 'Debit', DATE '2026-09-24', 'Metro Pass & Uber');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 9, 1800.00, 'Debit', DATE '2026-09-29', 'Gaming & Arcade');

-- Current Month (October 2026) initial transactions
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 6, 20000.00, 'Debit', DATE '2026-10-01', 'Apartment Rent October');
INSERT INTO Transactions (account_id, category_id, amount, txn_type, txn_date, description)
VALUES (1, 4, 3200.00, 'Debit', DATE '2026-10-01', 'Weekly Groceries');

-- 6. Budgets for October 2026 (User 1)
INSERT INTO Budgets (user_id, category_id, month, limit_amount)
VALUES (1, 4, '2026-10', 8000.00); -- Groceries limit

INSERT INTO Budgets (user_id, category_id, month, limit_amount)
VALUES (1, 5, '2026-10', 4000.00); -- Food & Dining limit

INSERT INTO Budgets (user_id, category_id, month, limit_amount)
VALUES (1, 6, '2026-10', 21000.00); -- Rent limit

INSERT INTO Budgets (user_id, category_id, month, limit_amount)
VALUES (1, 7, '2026-10', 3000.00); -- Utilities limit

INSERT INTO Budgets (user_id, category_id, month, limit_amount)
VALUES (1, 8, '2026-10', 2500.00); -- Transportation limit

INSERT INTO Budgets (user_id, category_id, month, limit_amount)
VALUES (1, 9, '2026-10', 2000.00); -- Entertainment limit

-- 7. Recurring Payments (due today or upcoming)
-- Category 11 = Subscriptions, Category 7 = Utilities, Category 6 = Rent
INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
VALUES (1, 11, 499.00, 'Monthly', TRUNC(SYSDATE)); -- Netflix, due today for auto-log demonstration!

INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
VALUES (1, 11, 199.00, 'Monthly', TRUNC(SYSDATE) + 5); -- Spotify

INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
VALUES (1, 7, 999.00, 'Monthly', TRUNC(SYSDATE) + 10); -- Fiber Broadband

INSERT INTO RecurringPayments (account_id, category_id, amount, frequency, next_due_date)
VALUES (1, 6, 20000.00, 'Monthly', ADD_MONTHS(TRUNC(SYSDATE), 1)); -- Next month's rent

COMMIT;

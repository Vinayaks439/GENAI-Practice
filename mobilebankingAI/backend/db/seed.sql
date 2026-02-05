-- Seed data for Mobile Banking AI testing
-- This creates sample users, accounts, loans, and investments

-- Insert test users
INSERT INTO users (id, username, password_hash, full_name, email, created_at) VALUES
(1, 'johndoe', 'hashed_password_123', 'John Doe', 'john.doe@example.com', NOW()),
(2, 'janesmith', 'hashed_password_456', 'Jane Smith', 'jane.smith@example.com', NOW()),
(3, 'bobwilson', 'hashed_password_789', 'Bob Wilson', 'bob.wilson@example.com', NOW()),
(4, 'alicebrown', 'hashed_password_abc', 'Alice Brown', 'alice.brown@example.com', NOW()),
(5, 'admin', 'admin_hash_secret', 'System Admin', 'admin@bank.com', NOW())
ON CONFLICT DO NOTHING;

-- Insert accounts for users
INSERT INTO accounts (id, user_id, account_number, type, balance) VALUES
-- John Doe's accounts
(1, 1, '1234567890', 'savings', 15000.00),
(2, 1, '1234567891', 'checking', 2500.50),
-- Jane Smith's accounts
(3, 2, '2345678901', 'savings', 50000.00),
(4, 2, '2345678902', 'checking', 8750.25),
-- Bob Wilson's accounts
(5, 3, '3456789012', 'savings', 3200.00),
-- Alice Brown's accounts
(6, 4, '4567890123', 'savings', 125000.00),
(7, 4, '4567890124', 'checking', 15000.00),
-- Admin's test account
(8, 5, '9999999999', 'savings', 1000000.00)
ON CONFLICT DO NOTHING;

-- Insert loans
INSERT INTO loans (id, user_id, amount, status, interest_rate) VALUES
(1, 1, 5000.00, 'approved', 0.08),
(2, 1, 10000.00, 'pending', 0.075),
(3, 2, 25000.00, 'approved', 0.065),
(4, 3, 2000.00, 'pending', 0.09)
ON CONFLICT DO NOTHING;

-- Insert mutual fund holdings
INSERT INTO mutual_funds (id, user_id, fund_name, units_held, current_value) VALUES
(1, 1, 'Large Cap Growth Fund', 50.25, 6306.38),
(2, 1, 'Tech Innovation Fund', 10.00, 2103.00),
(3, 2, 'Blue Chip Equity Fund', 100.00, 8975.00),
(4, 2, 'Bond Fund', 200.00, 10560.00),
(5, 4, 'Emerging Markets Fund', 500.00, 22600.00)
ON CONFLICT DO NOTHING;

-- Insert sample transactions
INSERT INTO transactions (id, account_id, amount, type, description, timestamp) VALUES
(1, 1, 1000.00, 'credit', 'Salary deposit', NOW() - INTERVAL '5 days'),
(2, 1, -150.00, 'debit', 'Electricity bill payment', NOW() - INTERVAL '4 days'),
(3, 1, -500.00, 'debit', 'Transfer to checking', NOW() - INTERVAL '3 days'),
(4, 2, 500.00, 'credit', 'Transfer from savings', NOW() - INTERVAL '3 days'),
(5, 2, -75.50, 'debit', 'Online shopping', NOW() - INTERVAL '2 days'),
(6, 3, 5000.00, 'credit', 'Bonus payment', NOW() - INTERVAL '1 day'),
(7, 1, -200.00, 'debit', 'MF Investment: Large Cap Growth Fund', NOW()),
(8, 6, 10000.00, 'credit', 'Wire transfer received', NOW() - INTERVAL '7 days')
ON CONFLICT DO NOTHING;

-- Update sequences to avoid conflicts
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
SELECT setval('accounts_id_seq', (SELECT MAX(id) FROM accounts));
SELECT setval('loans_id_seq', (SELECT MAX(id) FROM loans));
SELECT setval('mutual_funds_id_seq', (SELECT MAX(id) FROM mutual_funds));
SELECT setval('transactions_id_seq', (SELECT MAX(id) FROM transactions));

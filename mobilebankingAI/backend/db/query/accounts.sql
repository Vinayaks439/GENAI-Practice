-- name: CreateAccount :one
INSERT INTO accounts (
    user_id,
    account_number,
    type,
    balance
) VALUES (
    $1,
    $2,
    $3,
    $4
) RETURNING *;

-- name: GetAccountByID :one
SELECT * FROM accounts
WHERE id = $1;

-- name: ListAccountsByUserID :many
SELECT * FROM accounts
WHERE user_id = $1
ORDER BY id;

-- name: UpdateAccountBalance :one
UPDATE accounts
SET balance = $2
WHERE id = $1
RETURNING *;

-- name: AddAccountBalance :one
UPDATE accounts
SET balance = balance + $2
WHERE id = $1
RETURNING *;

-- name: DeleteAccountByID :exec
DELETE FROM accounts
WHERE id = $1;
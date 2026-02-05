-- name: CreateTransaction :one
INSERT INTO transactions (
    account_id,
    amount,
    type,
    description,
    timestamp
) VALUES (
    $1,
    $2,
    $3,
    $4,
    NOW()
) RETURNING *;

-- name: GetTransactionByID :one
SELECT * FROM transactions
WHERE id = $1;

-- name: ListTransactionsByAccountID :many
SELECT * FROM transactions  
WHERE account_id = $1
ORDER BY timestamp DESC
LIMIT $2 OFFSET $3; 

-- name: DeleteTransactionByID :exec
DELETE FROM transactions
WHERE id = $1;

-- name: ListAllTransactions :many
SELECT * FROM transactions
ORDER BY timestamp DESC
LIMIT $1 OFFSET $2;

-- name: ListTransactionsByType :many
SELECT * FROM transactions
WHERE type = $1
ORDER BY timestamp DESC
LIMIT $2 OFFSET $3;
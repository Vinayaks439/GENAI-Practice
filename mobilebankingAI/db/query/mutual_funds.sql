-- name: CreateMutualFund :one
INSERT INTO mutual_funds (
    user_id,
    fund_name,
    units_held,
    current_value
) VALUES (
    $1,
    $2,
    $3,
    $4
) RETURNING *;

-- name: GetMutualFundByID :one
SELECT * FROM mutual_funds
WHERE id = $1;

-- name: ListMutualFunds :many
SELECT * FROM mutual_funds
ORDER BY id
LIMIT $1 OFFSET $2;

-- name: UpdateMutualFundValue :one
UPDATE mutual_funds
SET current_value = $2
WHERE id = $1
RETURNING *;

-- name: DeleteMutualFundByID :exec
DELETE FROM mutual_funds
WHERE id = $1;

-- name: ListMutualFundsByUserID :many
SELECT * FROM mutual_funds
WHERE user_id = $1
ORDER BY id
LIMIT $2 OFFSET $3;
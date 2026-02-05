-- name: CreateLoan :one
INSERT INTO loans (
    user_id,
    amount,
    interest_rate,
    status
) VALUES (
    $1,
    $2,
    $3,
    $4
) RETURNING *;

-- name: GetLoanByID :one
SELECT * FROM loans
WHERE id = $1;


-- name: ListLoansByUserID :many
SELECT * FROM loans
WHERE user_id = $1  
ORDER BY id
LIMIT $2 OFFSET $3;


-- name: UpdateLoanStatus :one
UPDATE loans
SET status = $2
WHERE id = $1
RETURNING *;

-- name: DeleteLoanByID :exec
DELETE FROM loans
WHERE id = $1;


-- name: ListAllLoans :many
SELECT * FROM loans
ORDER BY id;
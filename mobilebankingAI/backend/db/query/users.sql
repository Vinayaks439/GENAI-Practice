-- name: CreateUser :one
INSERT INTO users (
    username, 
    password_hash, 
    full_name, 
    email, 
    created_at
) VALUES (
    $1, 
    $2, 
    $3,
    $4, 
    NOW()
) RETURNING *;

-- name: GetUserByUsername :one
SELECT * FROM users 
WHERE username = $1;

-- name: GetUserByID :one
SELECT * FROM users
WHERE id = $1;

-- name: ListUsers :many
SELECT * FROM users
ORDER BY id
LIMIT $1 OFFSET $2;

-- name: DeleteUserByID :exec
DELETE FROM users
WHERE id = $1;
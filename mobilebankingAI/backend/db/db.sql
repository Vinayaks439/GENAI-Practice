CREATE TABLE "users" (
  "id" integer PRIMARY KEY,
  "username" varchar,
  "password_hash" varchar,
  "full_name" varchar,
  "email" varchar,
  "created_at" timestamp
);

CREATE TABLE "accounts" (
  "id" integer PRIMARY KEY,
  "user_id" integer,
  "account_number" varchar UNIQUE,
  "type" varchar,
  "balance" decimal
);

CREATE TABLE "transactions" (
  "id" integer PRIMARY KEY,
  "account_id" integer,
  "amount" decimal,
  "type" varchar,
  "description" text,
  "timestamp" timestamp
);

CREATE TABLE "loans" (
  "id" integer PRIMARY KEY,
  "user_id" integer,
  "amount" decimal,
  "status" varchar,
  "interest_rate" decimal
);

CREATE TABLE "mutual_funds" (
  "id" integer PRIMARY KEY,
  "user_id" integer,
  "fund_name" varchar,
  "units_held" decimal,
  "current_value" decimal
);

ALTER TABLE "accounts" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "transactions" ADD FOREIGN KEY ("account_id") REFERENCES "accounts" ("id");

ALTER TABLE "loans" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "mutual_funds" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

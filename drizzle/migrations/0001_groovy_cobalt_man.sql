CREATE TABLE "health_records" (
	"id" text PRIMARY KEY NOT NULL,
	"data_type" text NOT NULL,
	"start_time" text,
	"end_time" text,
	"date" text,
	"numeric_value" double precision,
	"payload" jsonb NOT NULL,
	"updated_at" bigint
);

CREATE TABLE "sync_state" (
	"data_type" text PRIMARY KEY NOT NULL,
	"last_synced_at" bigint,
	"status" text NOT NULL,
	"record_count" integer DEFAULT 0 NOT NULL,
	"error" text,
	"updated_at" bigint
);

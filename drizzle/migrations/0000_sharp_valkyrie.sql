CREATE TABLE "daily_metrics" (
	"date" text NOT NULL,
	"metric" text NOT NULL,
	"value" double precision,
	"updated_at" bigint,
	CONSTRAINT "daily_metrics_date_metric_pk" PRIMARY KEY("date","metric")
);
--> statement-breakpoint
CREATE TABLE "exercises" (
	"id" text PRIMARY KEY NOT NULL,
	"type" text,
	"display_name" text,
	"start_time" text,
	"duration_s" bigint,
	"calories" double precision,
	"distance_mm" double precision,
	"steps" integer,
	"avg_hr" integer,
	"raw" jsonb,
	"updated_at" bigint
);
--> statement-breakpoint
CREATE TABLE "meta" (
	"key" text PRIMARY KEY NOT NULL,
	"value" text
);
--> statement-breakpoint
CREATE TABLE "tokens" (
	"id" integer PRIMARY KEY NOT NULL,
	"access_token" text,
	"refresh_token" text,
	"expiry" bigint,
	"scope" text,
	"updated_at" bigint
);

CREATE TABLE "food_logs" (
	"id" text PRIMARY KEY NOT NULL,
	"date" text NOT NULL,
	"meal" text NOT NULL,
	"name" text NOT NULL,
	"calories" double precision,
	"protein_g" double precision,
	"carbs_g" double precision,
	"fat_g" double precision,
	"notes" text,
	"created_at" bigint,
	"updated_at" bigint
);

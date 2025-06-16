CREATE TABLE IF NOT EXISTS "cms_users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"password_hash" text NOT NULL,
	"full_name" text,
	"phone" text,
	"role" text,
	"profile_completed" boolean DEFAULT false,
	"email_verified" boolean DEFAULT false,
	"is_active" boolean DEFAULT true,
	"college_details" jsonb,
	"affiliated_university" jsonb,
	"address_details" jsonb,
	"logo_urls" jsonb,
	"college_name" text,
	"status" text DEFAULT 'pending',
	"parent_id" text,
	"model_access" jsonb,
	"result_format" jsonb,
	"last_login" timestamp,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp DEFAULT now(),
	CONSTRAINT "cms_users_email_unique" UNIQUE("email")
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "otp_codes" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"code" text NOT NULL,
	"expires_at" timestamp NOT NULL,
	"used" boolean DEFAULT false,
	"created_at" timestamp DEFAULT now()
);

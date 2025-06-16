import { pgTable, text, integer, boolean, jsonb, timestamp, uuid } from 'drizzle-orm/pg-core';
import { sql } from 'drizzle-orm';

export const cmsUsers = pgTable('cms_users', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  email: text('email').unique().notNull(),
  passwordHash: text('password_hash').notNull(),
  fullName: text('full_name'),
  phone: text('phone'),
  role: text('role'), // 'admin', 'staff', 'principal', etc.
  
  // Profile completion
  profileCompleted: boolean('profile_completed').default(false),
  emailVerified: boolean('email_verified').default(false),
  isActive: boolean('is_active').default(true),
  
  // College registration data (stored as JSON)
  collegeDetails: jsonb('college_details'),
  affiliatedUniversity: jsonb('affiliated_university'),
  addressDetails: jsonb('address_details'),
  logoUrls: jsonb('logo_urls'),
  
  // Additional fields to match frontend expectations
  collegeName: text('college_name'),
  status: text('status').default('pending'),
  parentId: text('parent_id'),
  modelAccess: jsonb('model_access'),
  resultFormat: jsonb('result_format'),
  
  // Timestamps
  lastLogin: timestamp('last_login'),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const otpCodes = pgTable('otp_codes', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  email: text('email').notNull(),
  code: text('code').notNull(),
  expiresAt: timestamp('expires_at').notNull(),
  used: boolean('used').default(false),
  createdAt: timestamp('created_at').defaultNow(),
});

export type CMSUser = typeof cmsUsers.$inferSelect;
export type NewCMSUser = typeof cmsUsers.$inferInsert;
export type OTPCode = typeof otpCodes.$inferSelect;
export type NewOTPCode = typeof otpCodes.$inferInsert;
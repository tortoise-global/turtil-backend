import { z } from 'zod';

// Request schemas
export const SendOTPRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
});

export const VerifyOTPRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  otp: z.string().length(6, 'OTP must be 6 digits'),
});

export const CompleteSignupRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  otp: z.string().length(6, 'OTP must be 6 digits'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const LoginRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  password: z.string().min(1, 'Password is required'),
});

export const UpdateUserRequestSchema = z.object({
  fullName: z.string().optional(),
  phone: z.string().optional(),
  role: z.string().optional(),
  collegeDetails: z.object({
    name: z.string(),
    type: z.string(),
    website: z.string().optional(),
    establishedYear: z.number().optional(),
    accreditation: z.string().optional(),
  }).optional(),
  affiliatedUniversity: z.object({
    name: z.string(),
    state: z.string(),
    country: z.string(),
  }).optional(),
  addressDetails: z.object({
    street: z.string(),
    city: z.string(),
    state: z.string(),
    pincode: z.string(),
    country: z.string(),
  }).optional(),
  logoUrls: z.object({
    college: z.string().url().optional(),
    university: z.string().url().optional(),
  }).optional(),
});

// Response schemas
export const AuthResponseSchema = z.object({
  accessToken: z.string(),
  tokenType: z.string(),
  cmsUserId: z.string(),
  role: z.string().optional(),
  profileCompleted: z.boolean(),
});

export const UserResponseSchema = z.object({
  id: z.string(),
  email: z.string(),
  fullName: z.string().nullable(),
  phone: z.string().nullable(),
  role: z.string().nullable(),
  profileCompleted: z.boolean(),
  emailVerified: z.boolean(),
  isActive: z.boolean(),
  collegeDetails: z.any().nullable(),
  affiliatedUniversity: z.any().nullable(),
  addressDetails: z.any().nullable(),
  logoUrls: z.any().nullable(),
  collegeName: z.string().nullable(),
  status: z.string(),
  parentId: z.string().nullable(),
  modelAccess: z.any().nullable(),
  resultFormat: z.any().nullable(),
  lastLogin: z.string().nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const SuccessResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

export const ErrorResponseSchema = z.object({
  error: z.string(),
  detail: z.string().optional(),
  errorCode: z.string().optional(),
  requestId: z.string().optional(),
});

// Type exports
export type SendOTPRequest = z.infer<typeof SendOTPRequestSchema>;
export type VerifyOTPRequest = z.infer<typeof VerifyOTPRequestSchema>;
export type CompleteSignupRequest = z.infer<typeof CompleteSignupRequestSchema>;
export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type UpdateUserRequest = z.infer<typeof UpdateUserRequestSchema>;
export type AuthResponse = z.infer<typeof AuthResponseSchema>;
export type UserResponse = z.infer<typeof UserResponseSchema>;
export type SuccessResponse = z.infer<typeof SuccessResponseSchema>;
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
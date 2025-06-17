import { OpenAPIHono, createRoute } from '@hono/zod-openapi';
import { z } from 'zod';
import { authService } from '../services/auth';
import { authenticateToken } from '../middleware/auth';
import {
  SendOTPRequestSchema,
  VerifyOTPRequestSchema,
  CompleteSignupRequestSchema,
  LoginRequestSchema,
  UpdateUserRequestSchema,
  AuthResponseSchema,
  UserResponseSchema,
  SuccessResponseSchema,
  ErrorResponseSchema,
} from '../schemas/auth';

const auth = new OpenAPIHono();

// Send OTP route
const sendOTPRoute = createRoute({
  method: 'post',
  path: '/send-signup-otp',
  request: {
    body: {
      content: {
        'application/json': {
          schema: SendOTPRequestSchema,
        },
      },
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: SuccessResponseSchema,
        },
      },
      description: 'OTP sent successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Bad request',
    },
    500: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Internal server error',
    },
  },
  tags: ['Authentication'],
  summary: 'Send OTP for signup',
  description: 'Send a verification OTP to the provided email address for signup',
});

auth.openapi(sendOTPRoute, async (c) => {
  try {
    const { email } = c.req.valid('json');
    const result = await authService.sendSignupOTP(email);
    return c.json(result);
  } catch (error: any) {
    console.error('Send OTP error:', error);
    return c.json({ 
      error: 'Database error',
      detail: 'An error occurred while processing your request',
      errorCode: 'DATABASE_ERROR',
      requestId: Date.now().toString()
    }, 500);
  }
});

// Verify OTP route
const verifyOTPRoute = createRoute({
  method: 'post',
  path: '/verify-signup-otp',
  request: {
    body: {
      content: {
        'application/json': {
          schema: VerifyOTPRequestSchema,
        },
      },
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: SuccessResponseSchema.extend({ verified: z.boolean() }),
        },
      },
      description: 'OTP verified successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Invalid or expired OTP',
    },
  },
  tags: ['Authentication'],
  summary: 'Verify OTP for signup',
  description: 'Verify the OTP sent to the email address',
});

auth.openapi(verifyOTPRoute, async (c) => {
  try {
    const { email, otp } = c.req.valid('json');
    const result = await authService.verifySignupOTP(email, otp);
    return c.json(result);
  } catch (error: any) {
    console.error('Verify OTP error:', error);
    return c.json({ 
      error: error.message,
      detail: error.message,
      errorCode: 'VALIDATION_ERROR'
    }, 400);
  }
});

// Complete signup route
const completeSignupRoute = createRoute({
  method: 'post',
  path: '/complete-signup',
  request: {
    body: {
      content: {
        'application/json': {
          schema: CompleteSignupRequestSchema,
        },
      },
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: SuccessResponseSchema.extend({ userId: z.string() }),
        },
      },
      description: 'Signup completed successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Invalid request data',
    },
  },
  tags: ['Authentication'],
  summary: 'Complete user signup',
  description: 'Complete the signup process with OTP verification and password setup',
});

auth.openapi(completeSignupRoute, async (c) => {
  try {
    const { email, otp, password } = c.req.valid('json');
    const result = await authService.completeSignup(email, otp, password);
    return c.json({
      message: result.message,
      success: result.success,
      userId: result.userId
    });
  } catch (error: any) {
    console.error('Complete signup error:', error);
    return c.json({ 
      error: error.message,
      detail: error.message,
      errorCode: 'VALIDATION_ERROR'
    }, 400);
  }
});

// Login route
const loginRoute = createRoute({
  method: 'post',
  path: '/login',
  request: {
    body: {
      content: {
        'application/json': {
          schema: LoginRequestSchema,
        },
      },
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: AuthResponseSchema,
        },
      },
      description: 'Login successful',
    },
    401: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Invalid credentials',
    },
  },
  tags: ['Authentication'],
  summary: 'User login',
  description: 'Authenticate user with email and password',
});

auth.openapi(loginRoute, async (c) => {
  try {
    const { email, password } = c.req.valid('json');
    const result = await authService.login(email, password);
    return c.json(result);
  } catch (error: any) {
    console.error('Login error:', error);
    return c.json({ 
      error: 'Incorrect username or password',
      detail: 'Incorrect username or password',
      requestId: Date.now().toString()
    }, 401);
  }
});

// Get user route
const getUserRoute = createRoute({
  method: 'get',
  path: '/users/{userId}',
  request: {
    params: z.object({
      userId: z.string(),
    }),
    headers: z.object({
      authorization: z.string(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: UserResponseSchema,
        },
      },
      description: 'User details retrieved successfully',
    },
    401: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Unauthorized',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'User not found',
    },
  },
  tags: ['Users'],
  summary: 'Get user by ID',
  description: 'Retrieve user details by user ID',
});

auth.openapi(getUserRoute, authenticateToken, async (c) => {
  try {
    const { userId } = c.req.valid('param');
    const user = await authService.getUserById(userId);
    
    // Format response with simplified user model
    const response = {
      id: user.id,
      email: user.email,
      fullName: user.fullName,
      phone: user.phone,
      role: user.role,
      departmentId: user.departmentId,
      hodId: user.hodId,
      collegeId: user.collegeId,
      staffType: user.staffType,
      jobTitle: user.jobTitle,
      isActive: user.isActive,
      lastLogin: user.lastLogin?.toISOString() || null,
      createdAt: user.createdAt?.toISOString() || '',
      updatedAt: user.updatedAt?.toISOString() || ''
    };
    
    return c.json(response);
  } catch (error: any) {
    console.error('Get user error:', error);
    return c.json({ 
      error: 'User not found',
      detail: 'CMSUser not found'
    }, 404);
  }
});

// Update user route
const updateUserRoute = createRoute({
  method: 'put',
  path: '/users/{userId}',
  request: {
    params: z.object({
      userId: z.string(),
    }),
    headers: z.object({
      authorization: z.string(),
    }),
    body: {
      content: {
        'application/json': {
          schema: UpdateUserRequestSchema,
        },
      },
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: UserResponseSchema,
        },
      },
      description: 'User updated successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Bad request',
    },
    401: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Unauthorized',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'User not found',
    },
  },
  tags: ['Users'],
  summary: 'Update user profile',
  description: 'Update user profile information',
});

auth.openapi(updateUserRoute, authenticateToken, async (c) => {
  try {
    const { userId } = c.req.valid('param');
    const updates = c.req.valid('json');
    
    console.log('Updating user:', userId, 'with data:', updates);
    
    // Map frontend field names to database field names
    const dbUpdates: any = {};
    
    Object.keys(updates).forEach(key => {
      const value = updates[key as keyof typeof updates];
      if (value !== undefined) {
        switch (key) {
          case 'collegeDetails':
            dbUpdates.collegeDetails = value;
            break;
          case 'affiliatedUniversity':
            dbUpdates.affiliatedUniversity = value;
            break;
          case 'addressDetails':
            dbUpdates.addressDetails = value;
            break;
          case 'logoUrls':
            dbUpdates.logoUrls = value;
            break;
          default:
            dbUpdates[key] = value;
        }
      }
    });
    
    const updatedUser = await authService.updateUser(userId, dbUpdates);
    
    // Format response with simplified user model
    const response = {
      id: updatedUser.id,
      email: updatedUser.email,
      fullName: updatedUser.fullName,
      phone: updatedUser.phone,
      role: updatedUser.role,
      departmentId: updatedUser.departmentId,
      hodId: updatedUser.hodId,
      collegeId: updatedUser.collegeId,
      staffType: updatedUser.staffType,
      jobTitle: updatedUser.jobTitle,
      isActive: updatedUser.isActive,
      lastLogin: updatedUser.lastLogin?.toISOString() || null,
      createdAt: updatedUser.createdAt?.toISOString() || '',
      updatedAt: updatedUser.updatedAt?.toISOString() || ''
    };
    
    console.log('User updated successfully:', response);
    return c.json(response);
  } catch (error: any) {
    console.error('Update user error:', error);
    return c.json({ 
      error: 'Failed to update user',
      detail: error.message
    }, 400);
  }
});

export default auth;
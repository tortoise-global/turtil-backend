import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { eq, and } from 'drizzle-orm';
import { db } from '../db';
import { cmsUsers, otpCodes, type CMSUser, type NewCMSUser } from '../db/schema';
import { emailService } from './email';
import { generateOTP } from '../utils/otp';
import { redisService } from './redis';

export class AuthService {
  async sendSignupOTP(email: string): Promise<{ success: boolean; message: string }> {
    try {
      // Check if user already exists
      const existingUsers = await db.select().from(cmsUsers).where(eq(cmsUsers.email, email));
      if (existingUsers.length > 0) {
        throw new Error('Email already registered');
      }

      // Generate OTP
      const otp = generateOTP();
      const expiresAt = new Date(Date.now() + (parseInt(process.env.OTP_EXPIRY_MINUTES || '5') * 60 * 1000));

      // Save OTP to database
      await db.insert(otpCodes).values({
        email,
        code: otp,
        expiresAt,
      });

      // Send email
      await emailService.sendOTP(email, otp);

      return {
        success: true,
        message: 'OTP sent successfully to your email address'
      };
    } catch (error) {
      console.error('Send OTP error:', error);
      throw error;
    }
  }

  async verifySignupOTP(email: string, otp: string): Promise<{ success: boolean; message: string; verified: boolean }> {
    try {
      const now = new Date();
      
      const otpRecords = await db.select()
        .from(otpCodes)
        .where(
          and(
            eq(otpCodes.email, email),
            eq(otpCodes.code, otp),
            eq(otpCodes.used, false)
          )
        );
      
      const otpRecord = otpRecords[0];

      if (!otpRecord || otpRecord.expiresAt < now) {
        throw new Error('Invalid or expired OTP');
      }

      return {
        success: true,
        message: 'OTP verified successfully. You can now set your password.',
        verified: true
      };
    } catch (error) {
      console.error('Verify OTP error:', error);
      throw error;
    }
  }

  async completeSignup(email: string, otp: string, password: string): Promise<{ success: boolean; message: string; userId: string }> {
    try {
      // Verify OTP one more time
      const now = new Date();
      
      const otpRecords = await db.select()
        .from(otpCodes)
        .where(
          and(
            eq(otpCodes.email, email),
            eq(otpCodes.code, otp),
            eq(otpCodes.used, false)
          )
        );
      
      const otpRecord = otpRecords[0];

      if (!otpRecord || otpRecord.expiresAt < now) {
        throw new Error('Invalid or expired OTP');
      }

      // Check if user was created in the meantime
      const existingUsers = await db.select().from(cmsUsers).where(eq(cmsUsers.email, email));
      if (existingUsers.length > 0) {
        throw new Error('Email already registered');
      }

      // Hash password
      const passwordHash = await bcrypt.hash(password, 10);

      // Create user as Principal (first user is always principal)
      const newUsers = await db.insert(cmsUsers).values({
        email,
        passwordHash,
        role: 'principal',
        isActive: true,
      }).returning();
      
      const newUser = newUsers[0];

      // Mark OTP as used
      await db.update(otpCodes)
        .set({ used: true })
        .where(eq(otpCodes.id, otpRecord.id));

      return {
        success: true,
        message: 'Signup completed successfully. Please login to complete your profile.',
        userId: newUser.id
      };
    } catch (error) {
      console.error('Complete signup error:', error);
      throw error;
    }
  }

  async login(userName: string, password: string): Promise<{ accessToken: string; tokenType: string; cmsUserId: string; role?: string; profileCompleted: boolean }> {
    try {
      // Find user by email
      const users = await db.select().from(cmsUsers).where(eq(cmsUsers.email, userName));
      const user = users[0];
      
      if (!user || !await bcrypt.compare(password, user.passwordHash)) {
        throw new Error('Incorrect username or password');
      }

      if (!user.isActive) {
        throw new Error('Account is deactivated');
      }

      // Update last login
      await db.update(cmsUsers)
        .set({ lastLogin: new Date() })
        .where(eq(cmsUsers.id, user.id));

      // Generate JWT token
      const token = jwt.sign(
        { 
          userId: user.id,
          email: user.email,
          role: user.role,
        },
        process.env.JWT_SECRET!,
        { expiresIn: process.env.JWT_EXPIRES_IN || '30m' }
      );

      return {
        accessToken: token,
        tokenType: 'bearer',
        cmsUserId: user.id,
        role: user.role || undefined,
        profileCompleted: true // Always true in simplified model
      };
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  async getUserById(userId: string): Promise<CMSUser> {
    // Try to get from cache first
    const cachedUser = await redisService.getCachedUser(userId);
    if (cachedUser) {
      return cachedUser;
    }

    // If not in cache, get from database
    const users = await db.select().from(cmsUsers).where(eq(cmsUsers.id, userId));
    if (users.length === 0) {
      throw new Error('User not found');
    }
    const user = users[0];

    // Cache the user data
    await redisService.cacheUser(userId, user);
    
    return user;
  }

  async updateUser(userId: string, updates: Partial<CMSUser>): Promise<CMSUser> {
    try {
      updates.updatedAt = new Date();

      const updatedUsers = await db.update(cmsUsers)
        .set(updates)
        .where(eq(cmsUsers.id, userId))
        .returning();
      
      const updatedUser = updatedUsers[0];

      if (!updatedUser) {
        throw new Error('User not found');
      }

      // Invalidate user cache after update
      await redisService.invalidateUserCache(userId);

      return updatedUser;
    } catch (error) {
      console.error('Update user error:', error);
      throw error;
    }
  }

  verifyToken(token: string): any {
    try {
      return jwt.verify(token, process.env.JWT_SECRET!);
    } catch (error) {
      throw new Error('Invalid token');
    }
  }
}

export const authService = new AuthService();
import type { Context, Next } from 'hono';
import { authService } from '../services/auth';
import { redisService } from '../services/redis';

export interface AuthUser {
  userId: string;
  email: string;
  role?: string;
  profileCompleted: boolean;
}

export async function authenticateToken(c: Context, next: Next) {
  const authHeader = c.req.header('authorization');
  const token = authHeader?.split(' ')[1];

  if (!token) {
    return c.json({ error: 'Access token required' }, 401);
  }

  try {
    // Check if token is blacklisted
    const isBlacklisted = await redisService.isTokenBlacklisted(token);
    if (isBlacklisted) {
      return c.json({ error: 'Token has been revoked' }, 403);
    }

    const decoded = authService.verifyToken(token);
    c.set('user', decoded);
    await next();
  } catch (error) {
    return c.json({ error: 'Invalid or expired token' }, 403);
  }
}
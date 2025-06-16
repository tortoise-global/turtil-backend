import { Redis } from '@upstash/redis';

class RedisService {
  private client: Redis;

  constructor() {
    this.client = new Redis({
      url: process.env.UPSTASH_REDIS_URL!,
      token: process.env.UPSTASH_REDIS_TOKEN!,
    });
  }

  // User caching
  async cacheUser(userId: string, userData: any): Promise<void> {
    const ttl = parseInt(process.env.REDIS_USER_CACHE_TTL || '300'); // 5 minutes default
    await this.client.setex(`user:${userId}`, ttl, JSON.stringify(userData));
  }

  async getCachedUser(userId: string): Promise<any | null> {
    const cached = await this.client.get(`user:${userId}`);
    return cached ? JSON.parse(cached as string) : null;
  }

  async invalidateUserCache(userId: string): Promise<void> {
    await this.client.del(`user:${userId}`);
  }

  // Token blacklist for logout functionality
  async blacklistToken(token: string): Promise<void> {
    const ttl = parseInt(process.env.REDIS_BLACKLIST_TTL || '86400'); // 24 hours default
    await this.client.setex(`blacklist:${token}`, ttl, 'true');
  }

  async isTokenBlacklisted(token: string): Promise<boolean> {
    const result = await this.client.get(`blacklist:${token}`);
    return result === 'true';
  }

  // OTP caching (optional - can reduce database load)
  async cacheOTP(email: string, otp: string, expiresInSeconds: number): Promise<void> {
    await this.client.setex(`otp:${email}`, expiresInSeconds, otp);
  }

  async getCachedOTP(email: string): Promise<string | null> {
    const otp = await this.client.get(`otp:${email}`);
    return otp as string | null;
  }

  async invalidateOTP(email: string): Promise<void> {
    await this.client.del(`otp:${email}`);
  }

  // Rate limiting
  async incrementRateLimit(key: string, windowSeconds: number): Promise<number> {
    const current = await this.client.incr(key);
    if (current === 1) {
      await this.client.expire(key, windowSeconds);
    }
    return current;
  }

  async getRateLimit(key: string): Promise<number> {
    const current = await this.client.get(key);
    return current ? parseInt(current as string) : 0;
  }

  // Session management
  async createSession(sessionId: string, userId: string, expiresInSeconds: number): Promise<void> {
    await this.client.setex(`session:${sessionId}`, expiresInSeconds, userId);
  }

  async getSession(sessionId: string): Promise<string | null> {
    const userId = await this.client.get(`session:${sessionId}`);
    return userId as string | null;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.del(`session:${sessionId}`);
  }

  // Health check
  async ping(): Promise<boolean> {
    try {
      const result = await this.client.ping();
      return result === 'PONG';
    } catch (error) {
      console.error('Redis ping failed:', error);
      return false;
    }
  }
}

export const redisService = new RedisService();
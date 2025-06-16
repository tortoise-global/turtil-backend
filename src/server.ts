import { OpenAPIHono } from '@hono/zod-openapi';
import { swaggerUI } from '@hono/swagger-ui';
import { initializeDatabase } from './db';
import authRoutes from './routes/auth';
import { redisService } from './services/redis';

const app = new OpenAPIHono();

// Custom CORS middleware
app.use('*', async (c, next) => {
  const origin = c.req.header('origin');
  const allowedOrigins = process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000'];
  
  if (allowedOrigins.includes('*') || (origin && allowedOrigins.includes(origin))) {
    c.header('Access-Control-Allow-Origin', origin || '*');
  }
  
  c.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  c.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  c.header('Access-Control-Allow-Credentials', 'true');
  
  if (c.req.method === 'OPTIONS') {
    return c.text('', 200);
  }
  
  await next();
});

// Health check
app.get('/health', async (c) => {
  const redisHealth = await redisService.ping();
  
  return c.json({
    status: redisHealth ? 'healthy' : 'degraded',
    timestamp: Date.now() / 1000,
    services: {
      database: 'connected',
      redis: redisHealth ? 'connected' : 'disconnected'
    },
    metrics: {
      requests: { total: 0, average_duration: 0 },
      database: { total_queries: 0, average_duration: 0 },
      errors: { total: 0 },
      auth: { successful_logins: 0, failed_logins: 0, failure_rate: 0 }
    },
    environment: process.env.NODE_ENV || 'development',
    version: '1.0.0'
  });
});

// OpenAPI documentation
app.doc('/openapi.json', {
  openapi: '3.0.0',
  info: {
    version: '1.0.0',
    title: 'CMS Backend API',
    description: 'Content Management System Backend API with Authentication',
  },
  servers: [
    {
      url: process.env.NODE_ENV === 'production' 
        ? 'https://your-domain.com' 
        : `http://localhost:${parseInt(process.env.PORT || '8000')}`,
      description: process.env.NODE_ENV === 'production' ? 'Production server' : 'Development server',
    },
  ],
  tags: [
    {
      name: 'Authentication',
      description: 'Authentication related endpoints',
    },
    {
      name: 'Users',
      description: 'User management endpoints',
    },
  ],
});

// Swagger UI
app.get('/docs', swaggerUI({ url: '/openapi.json' }));

// Routes
app.route('/cms/auth', authRoutes);

// Error handling
app.onError((error, c) => {
  console.error('Error:', error);
  return c.json({
    error: error.message || 'Internal server error',
    detail: 'An error occurred while processing your request',
    errorCode: 'SERVER_ERROR',
    requestId: Date.now().toString()
  }, 500);
});

// 404 handler
app.notFound((c) => {
  return c.json({
    error: 'Not found',
    detail: 'The requested resource was not found',
    errorCode: 'NOT_FOUND'
  }, 404);
});

// Initialize database and start server
async function startServer() {
  try {
    await initializeDatabase();
    
    const port = parseInt(process.env.PORT || '8000');
    console.log(`🚀 Server starting on http://localhost:${port}`);
    console.log(`📊 Health check: http://localhost:${port}/health`);
    console.log(`🔐 Auth API: http://localhost:${port}/cms/auth`);
    console.log(`📚 API Documentation: http://localhost:${port}/docs`);
    console.log(`📋 OpenAPI JSON: http://localhost:${port}/openapi.json`);
    
    return {
      port,
      fetch: app.fetch,
    };
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

export default {
  port: parseInt(process.env.PORT || '8000'),
  fetch: app.fetch,
};
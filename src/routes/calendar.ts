import { OpenAPIHono, createRoute } from '@hono/zod-openapi';
import { z } from 'zod';
import { authenticateToken, requireRole, requireCalendarPermission } from '../middleware/auth';
import { CMS_USER_ROLES, EVENT_SCOPE_TYPES } from '../constants/roles';
import {
  CreateEventTypeRequestSchema,
  CreateCalendarEventRequestSchema,
  GetCalendarEventsRequestSchema,
  EventTypeResponseSchema,
  CalendarEventResponseSchema,
  SuccessResponseSchema,
  ErrorResponseSchema,
} from '../schemas/auth';

const calendar = new OpenAPIHono();

// ============= EVENT TYPES =============

// Create event type route
const createEventTypeRoute = createRoute({
  method: 'post',
  path: '/event-types',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    body: {
      content: {
        'application/json': {
          schema: CreateEventTypeRequestSchema,
        },
      },
    },
  },
  responses: {
    201: {
      content: {
        'application/json': {
          schema: EventTypeResponseSchema,
        },
      },
      description: 'Event type created successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Bad request',
    },
  },
  tags: ['Calendar'],
  summary: 'Create a new event type',
  description: 'Create a new calendar event type',
});

calendar.openapi(
  createEventTypeRoute,
  authenticateToken,
  requireRole(CMS_USER_ROLES.PRINCIPAL, CMS_USER_ROLES.COLLEGE_ADMIN),
  async (c) => {
    try {
      const eventTypeData = c.req.valid('json');

      // TODO: Implement event type creation service
      // const eventType = await calendarService.createEventType(eventTypeData);
      
      return c.json({
        id: 'event-type-id',
        name: eventTypeData.name,
        displayName: eventTypeData.displayName,
        color: eventTypeData.color,
        isActive: true,
        createdAt: new Date().toISOString(),
      }, 201);
    } catch (error: any) {
      console.error('Create event type error:', error);
      return c.json({
        error: 'Failed to create event type',
        detail: error.message,
      }, 400);
    }
  }
);

// Get all event types route
const getEventTypesRoute = createRoute({
  method: 'get',
  path: '/event-types',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    query: z.object({
      isActive: z.string().transform(val => val === 'true').optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.array(EventTypeResponseSchema),
        },
      },
      description: 'Event types retrieved successfully',
    },
  },
  tags: ['Calendar'],
  summary: 'Get all event types',
  description: 'Retrieve all calendar event types',
});

calendar.openapi(getEventTypesRoute, authenticateToken, async (c) => {
  try {
    const { isActive } = c.req.valid('query');

    // TODO: Implement event type listing service
    // const eventTypes = await calendarService.getEventTypes({ isActive });
    
    // Return default event types for now
    return c.json([
      {
        id: '1',
        name: 'holiday',
        displayName: 'Holiday',
        color: '#22c55e',
        isActive: true,
        createdAt: new Date().toISOString(),
      },
      {
        id: '2',
        name: 'exam_internal',
        displayName: 'Exams - Internals',
        color: '#f97316',
        isActive: true,
        createdAt: new Date().toISOString(),
      },
      {
        id: '3',
        name: 'event',
        displayName: 'Event',
        color: '#8b5cf6',
        isActive: true,
        createdAt: new Date().toISOString(),
      },
      {
        id: '4',
        name: 'project',
        displayName: 'Major Project Initiation',
        color: '#3b82f6',
        isActive: true,
        createdAt: new Date().toISOString(),
      },
    ]);
  } catch (error: any) {
    console.error('Get event types error:', error);
    return c.json({
      error: 'Failed to retrieve event types',
      detail: error.message,
    }, 500);
  }
});

// ============= CALENDAR EVENTS =============

// Create calendar event route
const createCalendarEventRoute = createRoute({
  method: 'post',
  path: '/events',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    body: {
      content: {
        'application/json': {
          schema: CreateCalendarEventRequestSchema,
        },
      },
    },
  },
  responses: {
    201: {
      content: {
        'application/json': {
          schema: CalendarEventResponseSchema,
        },
      },
      description: 'Calendar event created successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Bad request',
    },
    403: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Insufficient permissions',
    },
  },
  tags: ['Calendar'],
  summary: 'Create a new calendar event',
  description: 'Create a new calendar event with hierarchical scope',
});

calendar.openapi(
  createCalendarEventRoute,
  authenticateToken,
  async (c) => {
    try {
      const user = c.get('user');
      const eventData = c.req.valid('json');

      // Check permissions based on scope type
      const hasPermission = await requireCalendarPermission('create', eventData.scopeType as any);
      
      // TODO: Implement calendar event creation service with scope validation
      // const event = await calendarService.createEvent(user.collegeId, user.userId, eventData);
      
      return c.json({
        id: 'event-id',
        title: eventData.title,
        description: eventData.description || null,
        startDate: eventData.startDate,
        endDate: eventData.endDate,
        scopeType: eventData.scopeType,
        scopeId: eventData.scopeId || null,
        isAllDay: eventData.isAllDay || false,
        isRecurring: eventData.isRecurring || false,
        recurringPattern: eventData.recurringPattern || null,
        eventType: {
          id: eventData.eventTypeId,
          name: 'holiday',
          displayName: 'Holiday',
          color: '#22c55e',
          isActive: true,
          createdAt: new Date().toISOString(),
        },
        createdByUser: null,
        isActive: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }, 201);
    } catch (error: any) {
      console.error('Create calendar event error:', error);
      return c.json({
        error: 'Failed to create calendar event',
        detail: error.message,
      }, 400);
    }
  }
);

// Get calendar events route
const getCalendarEventsRoute = createRoute({
  method: 'get',
  path: '/events',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    query: z.object({
      degreeId: z.string().uuid().optional(),
      batchId: z.string().uuid().optional(),
      branchId: z.string().uuid().optional(),
      startDate: z.string().datetime().optional(),
      endDate: z.string().datetime().optional(),
      eventTypeId: z.string().uuid().optional(),
      scopeType: z.enum(['college', 'department', 'degree', 'branch', 'batch', 'section']).optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.array(CalendarEventResponseSchema),
        },
      },
      description: 'Calendar events retrieved successfully',
    },
  },
  tags: ['Calendar'],
  summary: 'Get calendar events',
  description: 'Retrieve calendar events with hierarchical filtering',
});

calendar.openapi(getCalendarEventsRoute, authenticateToken, async (c) => {
  try {
    const user = c.get('user');
    const filters = c.req.valid('query');

    // TODO: Implement calendar event retrieval with hierarchical inheritance
    // This should show:
    // - College-wide events for all users
    // - Department events for users in that department
    // - Degree/Branch/Batch specific events based on filters
    
    // const events = await calendarService.getEventsForUser(user.collegeId, user.role, user.departmentId, filters);
    
    return c.json([]);
  } catch (error: any) {
    console.error('Get calendar events error:', error);
    return c.json({
      error: 'Failed to retrieve calendar events',
      detail: error.message,
    }, 500);
  }
});

// Get calendar events for specific month route
const getMonthlyEventsRoute = createRoute({
  method: 'get',
  path: '/events/monthly/{year}/{month}',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      year: z.string().transform(val => parseInt(val)),
      month: z.string().transform(val => parseInt(val)),
    }),
    query: z.object({
      degreeId: z.string().uuid().optional(),
      batchId: z.string().uuid().optional(),
      branchId: z.string().uuid().optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.array(CalendarEventResponseSchema),
        },
      },
      description: 'Monthly calendar events retrieved successfully',
    },
  },
  tags: ['Calendar'],
  summary: 'Get monthly calendar events',
  description: 'Retrieve calendar events for a specific month (matching the UI)',
});

calendar.openapi(getMonthlyEventsRoute, authenticateToken, async (c) => {
  try {
    const user = c.get('user');
    const { year, month } = c.req.valid('param');
    const { degreeId, batchId, branchId } = c.req.valid('query');

    // Create start and end dates for the month
    const startDate = new Date(year, month - 1, 1);
    const endDate = new Date(year, month, 0, 23, 59, 59);

    // TODO: Implement monthly calendar event retrieval
    // const events = await calendarService.getMonthlyEvents(user.collegeId, startDate, endDate, {
    //   userId: user.userId,
    //   role: user.role,
    //   departmentId: user.departmentId,
    //   degreeId,
    //   batchId,
    //   branchId
    // });
    
    return c.json([]);
  } catch (error: any) {
    console.error('Get monthly events error:', error);
    return c.json({
      error: 'Failed to retrieve monthly events',
      detail: error.message,
    }, 500);
  }
});

// Update calendar event route
const updateCalendarEventRoute = createRoute({
  method: 'put',
  path: '/events/{eventId}',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      eventId: z.string().uuid(),
    }),
    body: {
      content: {
        'application/json': {
          schema: CreateCalendarEventRequestSchema.partial(),
        },
      },
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: CalendarEventResponseSchema,
        },
      },
      description: 'Calendar event updated successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Bad request',
    },
    403: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Insufficient permissions',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Event not found',
    },
  },
  tags: ['Calendar'],
  summary: 'Update calendar event',
  description: 'Update an existing calendar event',
});

calendar.openapi(
  updateCalendarEventRoute,
  authenticateToken,
  async (c) => {
    try {
      const user = c.get('user');
      const { eventId } = c.req.valid('param');
      const updates = c.req.valid('json');

      // TODO: Implement calendar event update with permission validation
      // Check if user can edit this event based on scope and role
      // const event = await calendarService.updateEvent(eventId, updates, user);
      
      return c.json({
        id: eventId,
        title: updates.title || 'Updated Event',
        description: updates.description || null,
        startDate: updates.startDate || new Date().toISOString(),
        endDate: updates.endDate || new Date().toISOString(),
        scopeType: updates.scopeType || 'college',
        scopeId: updates.scopeId || null,
        isAllDay: updates.isAllDay || false,
        isRecurring: updates.isRecurring || false,
        recurringPattern: updates.recurringPattern || null,
        eventType: {
          id: 'event-type-id',
          name: 'holiday',
          displayName: 'Holiday',
          color: '#22c55e',
          isActive: true,
          createdAt: new Date().toISOString(),
        },
        createdByUser: null,
        isActive: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    } catch (error: any) {
      console.error('Update calendar event error:', error);
      return c.json({
        error: 'Failed to update calendar event',
        detail: error.message,
      }, 400);
    }
  }
);

// Delete calendar event route
const deleteCalendarEventRoute = createRoute({
  method: 'delete',
  path: '/events/{eventId}',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      eventId: z.string().uuid(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: SuccessResponseSchema,
        },
      },
      description: 'Calendar event deleted successfully',
    },
    403: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Insufficient permissions',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Event not found',
    },
  },
  tags: ['Calendar'],
  summary: 'Delete calendar event',
  description: 'Delete an existing calendar event',
});

calendar.openapi(
  deleteCalendarEventRoute,
  authenticateToken,
  async (c) => {
    try {
      const user = c.get('user');
      const { eventId } = c.req.valid('param');

      // TODO: Implement calendar event deletion with permission validation
      // Check if user can delete this event based on scope and role
      // await calendarService.deleteEvent(eventId, user);
      
      return c.json({
        success: true,
        message: 'Calendar event deleted successfully',
      });
    } catch (error: any) {
      console.error('Delete calendar event error:', error);
      return c.json({
        error: 'Failed to delete calendar event',
        detail: error.message,
      }, 400);
    }
  }
);

export default calendar;
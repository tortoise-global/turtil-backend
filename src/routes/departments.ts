import { OpenAPIHono, createRoute } from '@hono/zod-openapi';
import { z } from 'zod';
import { authenticateToken, requireRole, requireDepartmentAccess } from '../middleware/auth';
import { CMS_USER_ROLES } from '../constants/roles';
import {
  CreateDepartmentRequestSchema,
  UpdateDepartmentRequestSchema,
  AssignHODRequestSchema,
  DepartmentResponseSchema,
  SuccessResponseSchema,
  ErrorResponseSchema,
} from '../schemas/auth';

const departments = new OpenAPIHono();

// Create department route
const createDepartmentRoute = createRoute({
  method: 'post',
  path: '/departments',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    body: {
      content: {
        'application/json': {
          schema: CreateDepartmentRequestSchema,
        },
      },
    },
  },
  responses: {
    201: {
      content: {
        'application/json': {
          schema: DepartmentResponseSchema,
        },
      },
      description: 'Department created successfully',
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
  tags: ['Departments'],
  summary: 'Create a new department',
  description: 'Create a new department in the college',
});

departments.openapi(
  createDepartmentRoute,
  authenticateToken,
  requireRole(CMS_USER_ROLES.PRINCIPAL, CMS_USER_ROLES.COLLEGE_ADMIN),
  async (c) => {
    try {
      const user = c.get('user');
      const departmentData = c.req.valid('json');

      // TODO: Implement department creation service
      // const department = await departmentService.createDepartment(user.collegeId, departmentData);
      
      return c.json({
        id: 'dept-id',
        name: departmentData.name,
        code: departmentData.code,
        description: departmentData.description || null,
        type: departmentData.type,
        hod: null,
        staffCount: 0,
        isActive: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }, 201);
    } catch (error: any) {
      console.error('Create department error:', error);
      return c.json({
        error: 'Failed to create department',
        detail: error.message,
      }, 400);
    }
  }
);

// Get all departments route
const getDepartmentsRoute = createRoute({
  method: 'get',
  path: '/departments',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    query: z.object({
      type: z.enum(['academic', 'administrative']).optional(),
      isActive: z.string().transform(val => val === 'true').optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.array(DepartmentResponseSchema),
        },
      },
      description: 'Departments retrieved successfully',
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
  tags: ['Departments'],
  summary: 'Get all departments',
  description: 'Retrieve all departments in the college',
});

departments.openapi(getDepartmentsRoute, authenticateToken, async (c) => {
  try {
    const user = c.get('user');
    const { type, isActive } = c.req.valid('query');

    // TODO: Implement department listing service
    // const departments = await departmentService.getDepartments(user.collegeId, { type, isActive });
    
    return c.json([]);
  } catch (error: any) {
    console.error('Get departments error:', error);
    return c.json({
      error: 'Failed to retrieve departments',
      detail: error.message,
    }, 500);
  }
});

// Get department by ID route
const getDepartmentRoute = createRoute({
  method: 'get',
  path: '/departments/{departmentId}',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      departmentId: z.string().uuid(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: DepartmentResponseSchema,
        },
      },
      description: 'Department retrieved successfully',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Department not found',
    },
  },
  tags: ['Departments'],
  summary: 'Get department by ID',
  description: 'Retrieve a specific department by ID',
});

departments.openapi(
  getDepartmentRoute,
  authenticateToken,
  requireDepartmentAccess(),
  async (c) => {
    try {
      const { departmentId } = c.req.valid('param');

      // TODO: Implement department retrieval service
      // const department = await departmentService.getDepartmentById(departmentId);
      
      return c.json({
        id: departmentId,
        name: 'Computer Science',
        code: 'CSE',
        description: 'Computer Science & Engineering Department',
        type: 'academic',
        hod: null,
        staffCount: 0,
        isActive: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    } catch (error: any) {
      console.error('Get department error:', error);
      return c.json({
        error: 'Department not found',
        detail: error.message,
      }, 404);
    }
  }
);

// Update department route
const updateDepartmentRoute = createRoute({
  method: 'put',
  path: '/departments/{departmentId}',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      departmentId: z.string().uuid(),
    }),
    body: {
      content: {
        'application/json': {
          schema: UpdateDepartmentRequestSchema,
        },
      },
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: DepartmentResponseSchema,
        },
      },
      description: 'Department updated successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Bad request',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Department not found',
    },
  },
  tags: ['Departments'],
  summary: 'Update department',
  description: 'Update department information',
});

departments.openapi(
  updateDepartmentRoute,
  authenticateToken,
  requireRole(CMS_USER_ROLES.PRINCIPAL, CMS_USER_ROLES.COLLEGE_ADMIN),
  async (c) => {
    try {
      const { departmentId } = c.req.valid('param');
      const updates = c.req.valid('json');

      // TODO: Implement department update service
      // const department = await departmentService.updateDepartment(departmentId, updates);
      
      return c.json({
        id: departmentId,
        name: updates.name || 'Computer Science',
        code: updates.code || 'CSE',
        description: updates.description || null,
        type: updates.type || 'academic',
        hod: null,
        staffCount: 0,
        isActive: updates.isActive ?? true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    } catch (error: any) {
      console.error('Update department error:', error);
      return c.json({
        error: 'Failed to update department',
        detail: error.message,
      }, 400);
    }
  }
);

// Assign HOD route
const assignHODRoute = createRoute({
  method: 'post',
  path: '/departments/{departmentId}/assign-hod',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      departmentId: z.string().uuid(),
    }),
    body: {
      content: {
        'application/json': {
          schema: z.object({
            userId: z.string().uuid(),
          }),
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
      description: 'HOD assigned successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Bad request',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Department or user not found',
    },
  },
  tags: ['Departments'],
  summary: 'Assign HOD to department',
  description: 'Assign a user as Head of Department',
});

departments.openapi(
  assignHODRoute,
  authenticateToken,
  requireRole(CMS_USER_ROLES.PRINCIPAL, CMS_USER_ROLES.COLLEGE_ADMIN),
  async (c) => {
    try {
      const { departmentId } = c.req.valid('param');
      const { userId } = c.req.valid('json');

      // TODO: Implement HOD assignment service
      // await departmentService.assignHOD(departmentId, userId);
      
      return c.json({
        success: true,
        message: 'HOD assigned successfully',
      });
    } catch (error: any) {
      console.error('Assign HOD error:', error);
      return c.json({
        error: 'Failed to assign HOD',
        detail: error.message,
      }, 400);
    }
  }
);

// Remove HOD route
const removeHODRoute = createRoute({
  method: 'delete',
  path: '/departments/{departmentId}/remove-hod',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      departmentId: z.string().uuid(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: SuccessResponseSchema,
        },
      },
      description: 'HOD removed successfully',
    },
    404: {
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
      description: 'Department not found',
    },
  },
  tags: ['Departments'],
  summary: 'Remove HOD from department',
  description: 'Remove the current Head of Department',
});

departments.openapi(
  removeHODRoute,
  authenticateToken,
  requireRole(CMS_USER_ROLES.PRINCIPAL, CMS_USER_ROLES.COLLEGE_ADMIN),
  async (c) => {
    try {
      const { departmentId } = c.req.valid('param');

      // TODO: Implement HOD removal service
      // await departmentService.removeHOD(departmentId);
      
      return c.json({
        success: true,
        message: 'HOD removed successfully',
      });
    } catch (error: any) {
      console.error('Remove HOD error:', error);
      return c.json({
        error: 'Failed to remove HOD',
        detail: error.message,
      }, 400);
    }
  }
);

// Get department staff route
const getDepartmentStaffRoute = createRoute({
  method: 'get',
  path: '/departments/{departmentId}/staff',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      departmentId: z.string().uuid(),
    }),
    query: z.object({
      role: z.enum(['hod', 'staff']).optional(),
      isActive: z.string().transform(val => val === 'true').optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.array(z.object({
            id: z.string(),
            email: z.string(),
            fullName: z.string().nullable(),
            role: z.string(),
            staffType: z.string().nullable(),
            jobTitle: z.string().nullable(),
            isActive: z.boolean(),
            createdAt: z.string(),
          })),
        },
      },
      description: 'Department staff retrieved successfully',
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
  tags: ['Departments'],
  summary: 'Get department staff',
  description: 'Retrieve all staff members in a department',
});

departments.openapi(
  getDepartmentStaffRoute,
  authenticateToken,
  requireDepartmentAccess(),
  async (c) => {
    try {
      const { departmentId } = c.req.valid('param');
      const { role, isActive } = c.req.valid('query');

      // TODO: Implement department staff retrieval service
      // const staff = await departmentService.getDepartmentStaff(departmentId, { role, isActive });
      
      return c.json([]);
    } catch (error: any) {
      console.error('Get department staff error:', error);
      return c.json({
        error: 'Failed to retrieve department staff',
        detail: error.message,
      }, 500);
    }
  }
);

export default departments;
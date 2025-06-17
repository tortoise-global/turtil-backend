import { OpenAPIHono, createRoute } from '@hono/zod-openapi';
import { z } from 'zod';
import { authenticateToken, requireRole, requireUserManagementPermission } from '../middleware/auth';
import { CMS_USER_ROLES } from '../constants/roles';
import {
  CreateUserRequestSchema,
  AssignRoleRequestSchema,
  UpdateUserPermissionsRequestSchema,
  UserResponseSchema,
  SuccessResponseSchema,
  ErrorResponseSchema,
} from '../schemas/auth';

const users = new OpenAPIHono();

// Create user route (enhanced for role-based creation)
const createUserRoute = createRoute({
  method: 'post',
  path: '/users',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    body: {
      content: {
        'application/json': {
          schema: CreateUserRequestSchema,
        },
      },
    },
  },
  responses: {
    201: {
      content: {
        'application/json': {
          schema: UserResponseSchema,
        },
      },
      description: 'User created successfully',
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
  tags: ['User Management'],
  summary: 'Create a new user',
  description: 'Create a new user with role assignment and department/HOD associations',
});

users.openapi(
  createUserRoute,
  authenticateToken,
  requireRole(CMS_USER_ROLES.PRINCIPAL, CMS_USER_ROLES.COLLEGE_ADMIN, CMS_USER_ROLES.HOD),
  async (c) => {
    try {
      const currentUser = c.get('user');
      const userData = c.req.valid('json');

      // Role-based validation
      if (currentUser.role === CMS_USER_ROLES.HOD) {
        // HODs can only create staff in their department
        if (userData.role !== CMS_USER_ROLES.STAFF) {
          return c.json({
            error: 'HODs can only create staff members',
          }, 403);
        }
        
        if (userData.departmentId && userData.departmentId !== currentUser.departmentId) {
          return c.json({
            error: 'HODs can only create staff in their own department',
          }, 403);
        }
      }

      // TODO: Implement user creation service with role validation
      // const user = await userService.createUser(currentUser.collegeId, userData);
      
      return c.json({
        id: 'user-id',
        email: userData.email,
        fullName: userData.fullName,
        phone: userData.phone,
        role: userData.role,
        departmentId: userData.departmentId || null,
        department: null,
        hodId: null,
        hod: null,
        collegeId: currentUser.collegeId,
        staffType: userData.staffType || null,
        jobTitle: userData.jobTitle || null,
        profileCompleted: false,
        emailVerified: false,
        isActive: true,
        modulePermissions: [],
        collegeDetails: null,
        affiliatedUniversity: null,
        addressDetails: null,
        logoUrls: null,
        collegeName: null,
        status: 'active',
        parentId: null,
        modelAccess: null,
        resultFormat: null,
        lastLogin: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }, 201);
    } catch (error: any) {
      console.error('Create user error:', error);
      return c.json({
        error: 'Failed to create user',
        detail: error.message,
      }, 400);
    }
  }
);

// Get users route (with role-based filtering)
const getUsersRoute = createRoute({
  method: 'get',
  path: '/users',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    query: z.object({
      role: z.enum(['principal', 'college_admin', 'hod', 'staff']).optional(),
      departmentId: z.string().uuid().optional(),
      staffType: z.enum(['departmental', 'non_departmental']).optional(),
      isActive: z.string().transform(val => val === 'true').optional(),
      limit: z.string().transform(val => parseInt(val)).optional(),
      offset: z.string().transform(val => parseInt(val)).optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.object({
            users: z.array(UserResponseSchema),
            total: z.number(),
            limit: z.number(),
            offset: z.number(),
          }),
        },
      },
      description: 'Users retrieved successfully',
    },
  },
  tags: ['User Management'],
  summary: 'Get all users',
  description: 'Retrieve users with role-based filtering and pagination',
});

users.openapi(getUsersRoute, authenticateToken, async (c) => {
  try {
    const currentUser = c.get('user');
    const { role, departmentId, staffType, isActive, limit = 50, offset = 0 } = c.req.valid('query');

    // Role-based access control
    let accessibleDepartmentId = departmentId;
    
    if (currentUser.role === CMS_USER_ROLES.HOD) {
      // HODs can only see users in their department
      accessibleDepartmentId = currentUser.departmentId;
    }

    // TODO: Implement user listing service with role-based filtering
    // const result = await userService.getUsers(currentUser.collegeId, {
    //   role,
    //   departmentId: accessibleDepartmentId,
    //   staffType,
    //   isActive,
    //   limit,
    //   offset
    // });
    
    return c.json({
      users: [],
      total: 0,
      limit,
      offset,
    });
  } catch (error: any) {
    console.error('Get users error:', error);
    return c.json({
      error: 'Failed to retrieve users',
      detail: error.message,
    }, 500);
  }
});

// Assign role route
const assignRoleRoute = createRoute({
  method: 'post',
  path: '/users/{userId}/assign-role',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      userId: z.string().uuid(),
    }),
    body: {
      content: {
        'application/json': {
          schema: AssignRoleRequestSchema,
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
      description: 'Role assigned successfully',
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
  tags: ['User Management'],
  summary: 'Assign role to user',
  description: 'Assign or change a user\'s role with department/HOD associations',
});

users.openapi(
  assignRoleRoute,
  authenticateToken,
  requireUserManagementPermission(),
  async (c) => {
    try {
      const currentUser = c.get('user');
      const { userId } = c.req.valid('param');
      const roleData = c.req.valid('json');

      // Role-based validation
      if (currentUser.role === CMS_USER_ROLES.HOD) {
        // HODs can only assign staff roles in their department
        if (roleData.role !== CMS_USER_ROLES.STAFF) {
          return c.json({
            error: 'HODs can only assign staff roles',
          }, 403);
        }
        
        if (roleData.departmentId && roleData.departmentId !== currentUser.departmentId) {
          return c.json({
            error: 'HODs can only assign roles in their own department',
          }, 403);
        }
      }

      // TODO: Implement role assignment service with validation
      // const user = await userService.assignRole(userId, roleData);
      
      return c.json({
        id: userId,
        email: 'user@example.com',
        fullName: 'User Name',
        phone: null,
        role: roleData.role,
        departmentId: roleData.departmentId || null,
        department: null,
        hodId: roleData.hodId || null,
        hod: null,
        collegeId: currentUser.collegeId,
        staffType: roleData.staffType || null,
        jobTitle: roleData.jobTitle || null,
        profileCompleted: false,
        emailVerified: false,
        isActive: true,
        modulePermissions: [],
        collegeDetails: null,
        affiliatedUniversity: null,
        addressDetails: null,
        logoUrls: null,
        collegeName: null,
        status: 'active',
        parentId: null,
        modelAccess: null,
        resultFormat: null,
        lastLogin: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    } catch (error: any) {
      console.error('Assign role error:', error);
      return c.json({
        error: 'Failed to assign role',
        detail: error.message,
      }, 400);
    }
  }
);

// Update user permissions route
const updateUserPermissionsRoute = createRoute({
  method: 'put',
  path: '/users/{userId}/permissions',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      userId: z.string().uuid(),
    }),
    body: {
      content: {
        'application/json': {
          schema: UpdateUserPermissionsRequestSchema,
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
      description: 'User permissions updated successfully',
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
  tags: ['User Management'],
  summary: 'Update user module permissions',
  description: 'Update a user\'s module-specific permissions',
});

users.openapi(
  updateUserPermissionsRoute,
  authenticateToken,
  requireUserManagementPermission(),
  async (c) => {
    try {
      const currentUser = c.get('user');
      const { userId } = c.req.valid('param');
      const { permissions } = c.req.valid('json');

      // Role-based validation
      if (currentUser.role === CMS_USER_ROLES.HOD) {
        // HODs can only update permissions for staff in their department
        const targetUser = await getUserById(userId); // TODO: implement service
        if (!targetUser || targetUser.departmentId !== currentUser.departmentId) {
          return c.json({
            error: 'HODs can only update permissions for staff in their department',
          }, 403);
        }
      }

      // TODO: Implement permission update service
      // await userService.updateUserPermissions(userId, permissions);
      
      return c.json({
        success: true,
        message: 'User permissions updated successfully',
      });
    } catch (error: any) {
      console.error('Update user permissions error:', error);
      return c.json({
        error: 'Failed to update user permissions',
        detail: error.message,
      }, 400);
    }
  }
);

// Get department staff (HOD-specific endpoint)
const getDepartmentStaffRoute = createRoute({
  method: 'get',
  path: '/users/department-staff',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    query: z.object({
      departmentId: z.string().uuid().optional(),
      includeHOD: z.string().transform(val => val === 'true').optional(),
      isActive: z.string().transform(val => val === 'true').optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.array(UserResponseSchema),
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
  tags: ['User Management'],
  summary: 'Get department staff',
  description: 'Get all staff members in a department (HOD can see their department only)',
});

users.openapi(getDepartmentStaffRoute, authenticateToken, async (c) => {
  try {
    const currentUser = c.get('user');
    const { departmentId, includeHOD, isActive } = c.req.valid('query');

    // Role-based access control
    let targetDepartmentId = departmentId;
    
    if (currentUser.role === CMS_USER_ROLES.HOD) {
      // HODs can only see staff in their own department
      targetDepartmentId = currentUser.departmentId;
    } else if (currentUser.role === CMS_USER_ROLES.STAFF) {
      return c.json({
        error: 'Staff cannot view department staff lists',
      }, 403);
    }

    // TODO: Implement department staff retrieval service
    // const staff = await userService.getDepartmentStaff(targetDepartmentId, { includeHOD, isActive });
    
    return c.json([]);
  } catch (error: any) {
    console.error('Get department staff error:', error);
    return c.json({
      error: 'Failed to retrieve department staff',
      detail: error.message,
    }, 500);
  }
});

// Activate/Deactivate user route
const toggleUserStatusRoute = createRoute({
  method: 'patch',
  path: '/users/{userId}/toggle-status',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    params: z.object({
      userId: z.string().uuid(),
    }),
    body: {
      content: {
        'application/json': {
          schema: z.object({
            isActive: z.boolean(),
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
      description: 'User status updated successfully',
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
  tags: ['User Management'],
  summary: 'Toggle user active status',
  description: 'Activate or deactivate a user account',
});

users.openapi(
  toggleUserStatusRoute,
  authenticateToken,
  requireUserManagementPermission(),
  async (c) => {
    try {
      const currentUser = c.get('user');
      const { userId } = c.req.valid('param');
      const { isActive } = c.req.valid('json');

      // Role-based validation
      if (currentUser.role === CMS_USER_ROLES.HOD) {
        // HODs can only toggle status for staff in their department
        const targetUser = await getUserById(userId); // TODO: implement service
        if (!targetUser || targetUser.departmentId !== currentUser.departmentId) {
          return c.json({
            error: 'HODs can only toggle status for staff in their department',
          }, 403);
        }
      }

      // TODO: Implement user status toggle service
      // await userService.toggleUserStatus(userId, isActive);
      
      return c.json({
        success: true,
        message: `User ${isActive ? 'activated' : 'deactivated'} successfully`,
      });
    } catch (error: any) {
      console.error('Toggle user status error:', error);
      return c.json({
        error: 'Failed to update user status',
        detail: error.message,
      }, 400);
    }
  }
);

// Get user statistics (for dashboard)
const getUserStatsRoute = createRoute({
  method: 'get',
  path: '/users/stats',
  request: {
    headers: z.object({
      authorization: z.string(),
    }),
    query: z.object({
      departmentId: z.string().uuid().optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.object({
            totalUsers: z.number(),
            activeUsers: z.number(),
            usersByRole: z.object({
              principal: z.number(),
              college_admin: z.number(),
              hod: z.number(),
              staff: z.number(),
            }),
            departmentalStaff: z.number(),
            nonDepartmentalStaff: z.number(),
          }),
        },
      },
      description: 'User statistics retrieved successfully',
    },
  },
  tags: ['User Management'],
  summary: 'Get user statistics',
  description: 'Get user statistics for dashboard (role-based access)',
});

users.openapi(getUserStatsRoute, authenticateToken, async (c) => {
  try {
    const currentUser = c.get('user');
    const { departmentId } = c.req.valid('query');

    // Role-based access control
    let targetDepartmentId = departmentId;
    
    if (currentUser.role === CMS_USER_ROLES.HOD) {
      // HODs can only see stats for their own department
      targetDepartmentId = currentUser.departmentId;
    }

    // TODO: Implement user statistics service
    // const stats = await userService.getUserStats(currentUser.collegeId, targetDepartmentId);
    
    return c.json({
      totalUsers: 0,
      activeUsers: 0,
      usersByRole: {
        principal: 0,
        college_admin: 0,
        hod: 0,
        staff: 0,
      },
      departmentalStaff: 0,
      nonDepartmentalStaff: 0,
    });
  } catch (error: any) {
    console.error('Get user stats error:', error);
    return c.json({
      error: 'Failed to retrieve user statistics',
      detail: error.message,
    }, 500);
  }
});

// Helper function placeholder (TODO: implement in service)
async function getUserById(userId: string) {
  // TODO: Implement actual user retrieval
  return null;
}

export default users;
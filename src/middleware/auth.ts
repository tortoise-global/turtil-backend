import type { Context, Next } from 'hono';
import { authService } from '../services/auth';
import { redisService } from '../services/redis';
import { 
  CMS_USER_ROLES, 
  CMS_MODULES, 
  canManageRole, 
  canManageStaff,
  CALENDAR_PERMISSIONS,
  EVENT_SCOPE_TYPES
} from '../constants/roles';
import type { CMSUserRole, CMSModule, EventScopeType } from '../constants/roles';

export interface AuthUser {
  userId: string;
  email: string;
  role: CMSUserRole;
  departmentId?: string;
  collegeId: string;
  modulePermissions?: Array<{
    module: string;
    canRead: boolean;
    canWrite: boolean;
    scope?: string;
  }>;
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
    
    // Get user with role and permissions
    const user = await authService.getUserById(decoded.userId);
    if (!user) {
      return c.json({ error: 'User not found' }, 404);
    }

    const authUser: AuthUser = {
      userId: user.id,
      email: user.email,
      role: user.role as CMSUserRole,
      departmentId: user.departmentId || undefined,
      collegeId: user.collegeId!,
      modulePermissions: user.modulePermissions as any
    };

    c.set('user', authUser);
    await next();
  } catch (error) {
    return c.json({ error: 'Invalid or expired token' }, 403);
  }
}

// Role-based authorization middleware
export function requireRole(...allowedRoles: CMSUserRole[]) {
  return async (c: Context, next: Next) => {
    const user = c.get('user') as AuthUser;
    
    if (!user) {
      return c.json({ error: 'Authentication required' }, 401);
    }

    if (!allowedRoles.includes(user.role)) {
      return c.json({ error: 'Insufficient permissions' }, 403);
    }

    await next();
  };
}

// Module permission middleware
export function requireModulePermission(module: CMSModule, permission: 'read' | 'write') {
  return async (c: Context, next: Next) => {
    const user = c.get('user') as AuthUser;
    
    if (!user) {
      return c.json({ error: 'Authentication required' }, 401);
    }

    // Principal and College Admin have all permissions
    if (user.role === CMS_USER_ROLES.PRINCIPAL || user.role === CMS_USER_ROLES.COLLEGE_ADMIN) {
      await next();
      return;
    }

    // Check if user has permission for this module
    const modulePermission = user.modulePermissions?.find(p => p.module === module);
    
    if (!modulePermission) {
      return c.json({ error: `No access to ${module} module` }, 403);
    }

    const hasPermission = permission === 'read' ? modulePermission.canRead : modulePermission.canWrite;
    
    if (!hasPermission) {
      return c.json({ error: `Insufficient ${permission} permissions for ${module} module` }, 403);
    }

    await next();
  };
}

// Department-based authorization middleware
export function requireDepartmentAccess(targetDepartmentId?: string) {
  return async (c: Context, next: Next) => {
    const user = c.get('user') as AuthUser;
    
    if (!user) {
      return c.json({ error: 'Authentication required' }, 401);
    }

    // Principal and College Admin have access to all departments
    if (user.role === CMS_USER_ROLES.PRINCIPAL || user.role === CMS_USER_ROLES.COLLEGE_ADMIN) {
      await next();
      return;
    }

    // HODs can only access their own department
    if (user.role === CMS_USER_ROLES.HOD) {
      if (!targetDepartmentId || user.departmentId !== targetDepartmentId) {
        return c.json({ error: 'Access denied to this department' }, 403);
      }
    }

    // Staff access depends on their department assignment and module permissions
    if (user.role === CMS_USER_ROLES.STAFF) {
      if (targetDepartmentId && user.departmentId !== targetDepartmentId) {
        return c.json({ error: 'Access denied to this department' }, 403);
      }
    }

    await next();
  };
}

// User management authorization
export function requireUserManagementPermission() {
  return async (c: Context, next: Next) => {
    const user = c.get('user') as AuthUser;
    const targetUserId = c.req.param('userId');
    
    if (!user) {
      return c.json({ error: 'Authentication required' }, 401);
    }

    // Principal and College Admin can manage all users
    if (user.role === CMS_USER_ROLES.PRINCIPAL || user.role === CMS_USER_ROLES.COLLEGE_ADMIN) {
      await next();
      return;
    }

    // HODs can only manage staff in their department
    if (user.role === CMS_USER_ROLES.HOD && targetUserId) {
      const targetUser = await authService.getUserById(targetUserId);
      if (!targetUser || !canManageStaff(user.role, user.departmentId || null, targetUser.departmentId)) {
        return c.json({ error: 'Cannot manage this user' }, 403);
      }
    }

    // Staff cannot manage other users
    if (user.role === CMS_USER_ROLES.STAFF) {
      return c.json({ error: 'Insufficient permissions' }, 403);
    }

    await next();
  };
}

// Calendar event authorization
export function requireCalendarPermission(action: 'create' | 'edit' | 'delete', scopeType?: EventScopeType) {
  return async (c: Context, next: Next) => {
    const user = c.get('user') as AuthUser;
    
    if (!user) {
      return c.json({ error: 'Authentication required' }, 401);
    }

    const userCalendarPerms = CALENDAR_PERMISSIONS[user.role];
    
    if (!scopeType) {
      // Default to college scope if not specified
      scopeType = EVENT_SCOPE_TYPES.COLLEGE;
    }

    let hasPermission = false;
    
    switch (action) {
      case 'create':
        hasPermission = userCalendarPerms.canCreate.includes(scopeType);
        break;
      case 'edit':
        hasPermission = userCalendarPerms.canEdit.includes(scopeType);
        break;
      case 'delete':
        hasPermission = userCalendarPerms.canDelete.includes(scopeType);
        break;
    }

    // Additional check for HODs - they can only manage events in their department
    if (user.role === CMS_USER_ROLES.HOD && scopeType === EVENT_SCOPE_TYPES.DEPARTMENT) {
      const departmentId = c.req.query('departmentId') || c.req.param('departmentId');
      if (departmentId && departmentId !== user.departmentId) {
        hasPermission = false;
      }
    }

    if (!hasPermission) {
      return c.json({ error: `Insufficient permissions to ${action} ${scopeType} events` }, 403);
    }

    await next();
  };
}

// Helper function to check if user can access specific academic data
export function canAccessAcademicData(user: AuthUser, targetDepartmentId?: string, targetBranchId?: string): boolean {
  // Principal and College Admin have access to all academic data
  if (user.role === CMS_USER_ROLES.PRINCIPAL || user.role === CMS_USER_ROLES.COLLEGE_ADMIN) {
    return true;
  }

  // HODs can access data from their department
  if (user.role === CMS_USER_ROLES.HOD) {
    return !targetDepartmentId || user.departmentId === targetDepartmentId;
  }

  // Staff access depends on their department assignment and module permissions
  if (user.role === CMS_USER_ROLES.STAFF) {
    // Non-departmental staff with Programs & Structure access can view all data
    if (!user.departmentId) {
      const programsPermission = user.modulePermissions?.find(p => p.module === CMS_MODULES.PROGRAMS_STRUCTURE);
      return programsPermission?.canRead || false;
    }
    
    // Departmental staff can access their department's data
    return !targetDepartmentId || user.departmentId === targetDepartmentId;
  }

  return false;
}
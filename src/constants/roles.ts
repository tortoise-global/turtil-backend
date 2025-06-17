// CMS User Roles
export const CMS_USER_ROLES = {
  PRINCIPAL: 'principal',
  COLLEGE_ADMIN: 'college_admin', 
  HOD: 'hod',
  STAFF: 'staff'
} as const;

export type CMSUserRole = typeof CMS_USER_ROLES[keyof typeof CMS_USER_ROLES];

// CMS Modules
export const CMS_MODULES = {
  PROGRAMS_STRUCTURE: 'programs_structure',
  STUDENTS: 'students',
  LISTS: 'lists', 
  ALERTS: 'alerts',
  TIMETABLE: 'timetable',
  ATTENDANCE: 'attendance',
  RESULTS: 'results',
  ASSIGNMENTS: 'assignments',
  ACADEMIC_CALENDAR: 'academic_calendar',
  DOCUMENT_REQUEST: 'document_request',
  EVENTS: 'events',
  PLACEMENTS: 'placements'
} as const;

export type CMSModule = typeof CMS_MODULES[keyof typeof CMS_MODULES];

// Department Types
export const DEPARTMENT_TYPES = {
  ACADEMIC: 'academic',
  ADMINISTRATIVE: 'administrative'
} as const;

export type DepartmentType = typeof DEPARTMENT_TYPES[keyof typeof DEPARTMENT_TYPES];

// Common department codes
export const COMMON_DEPARTMENTS = {
  // Administrative
  ADMIN: { code: 'ADMIN', name: 'Administration', type: DEPARTMENT_TYPES.ADMINISTRATIVE },
  LIBRARY: { code: 'LIB', name: 'Library', type: DEPARTMENT_TYPES.ADMINISTRATIVE },
  ACCOUNTS: { code: 'ACC', name: 'Accounts', type: DEPARTMENT_TYPES.ADMINISTRATIVE },
  HR: { code: 'HR', name: 'Human Resources', type: DEPARTMENT_TYPES.ADMINISTRATIVE },
  
  // Academic - Engineering
  CSE: { code: 'CSE', name: 'Computer Science & Engineering', type: DEPARTMENT_TYPES.ACADEMIC },
  ECE: { code: 'ECE', name: 'Electronics & Communication Engineering', type: DEPARTMENT_TYPES.ACADEMIC },
  MECH: { code: 'MECH', name: 'Mechanical Engineering', type: DEPARTMENT_TYPES.ACADEMIC },
  CIVIL: { code: 'CIVIL', name: 'Civil Engineering', type: DEPARTMENT_TYPES.ACADEMIC },
  EEE: { code: 'EEE', name: 'Electrical & Electronics Engineering', type: DEPARTMENT_TYPES.ACADEMIC },
  
  // Academic - Other
  MBA: { code: 'MBA', name: 'Master of Business Administration', type: DEPARTMENT_TYPES.ACADEMIC },
  MCA: { code: 'MCA', name: 'Master of Computer Applications', type: DEPARTMENT_TYPES.ACADEMIC },
} as const;

// Staff Types for better organization
export const STAFF_TYPES = {
  // Departmental Staff (require department assignment)
  DEPARTMENTAL: 'departmental',
  
  // Non-Departmental Staff (work directly under college administration)
  NON_DEPARTMENTAL: 'non_departmental'
} as const;

export type StaffType = typeof STAFF_TYPES[keyof typeof STAFF_TYPES];

// Common non-departmental staff roles
export const NON_DEPARTMENTAL_ROLES = {
  BANKING: 'Banking Staff',
  SECURITY: 'Security Staff', 
  MAINTENANCE: 'Maintenance Staff',
  TRANSPORT: 'Transport Staff',
  CANTEEN: 'Canteen Staff',
  MEDICAL: 'Medical Staff',
  GUEST_HOUSE: 'Guest House Staff',
  GENERAL: 'General Staff'
} as const;

// Permission scopes
export const PERMISSION_SCOPES = {
  ALL: 'all',         // Full access across college
  DEPARTMENT: 'department', // Limited to user's department
  OWN: 'own'          // Limited to user's own data
} as const;

export type PermissionScope = typeof PERMISSION_SCOPES[keyof typeof PERMISSION_SCOPES];

// Role hierarchy levels (for authorization checks)
export const ROLE_HIERARCHY = {
  [CMS_USER_ROLES.PRINCIPAL]: 4,
  [CMS_USER_ROLES.COLLEGE_ADMIN]: 3,
  [CMS_USER_ROLES.HOD]: 2,
  [CMS_USER_ROLES.STAFF]: 1
} as const;

// Helper functions
export function hasHigherRole(userRole: CMSUserRole, targetRole: CMSUserRole): boolean {
  return ROLE_HIERARCHY[userRole] > ROLE_HIERARCHY[targetRole];
}

export function canManageRole(userRole: CMSUserRole, targetRole: CMSUserRole): boolean {
  return ROLE_HIERARCHY[userRole] > ROLE_HIERARCHY[targetRole];
}

export function isValidRole(role: string): role is CMSUserRole {
  return Object.values(CMS_USER_ROLES).includes(role as CMSUserRole);
}

export function isValidModule(module: string): module is CMSModule {
  return Object.values(CMS_MODULES).includes(module as CMSModule);
}

export function requiresDepartment(role: CMSUserRole): boolean {
  return role === CMS_USER_ROLES.HOD; // Only HODs must have department
}

export function canHaveOptionalDepartment(role: CMSUserRole): boolean {
  return role === CMS_USER_ROLES.STAFF; // Staff can optionally have department
}

export function canManageStaff(userRole: CMSUserRole, userDepartmentId: string | null, targetDepartmentId: string | null): boolean {
  // Principal and College Admin can manage all staff
  if (userRole === CMS_USER_ROLES.PRINCIPAL || userRole === CMS_USER_ROLES.COLLEGE_ADMIN) {
    return true;
  }
  
  // HODs can only manage staff in their department
  if (userRole === CMS_USER_ROLES.HOD) {
    return userDepartmentId !== null && userDepartmentId === targetDepartmentId;
  }
  
  return false;
}

// Academic Hierarchy Constants
export const DEGREE_TYPES = {
  UNDERGRADUATE: 'undergraduate',
  POSTGRADUATE: 'postgraduate',
  DOCTORATE: 'doctorate'
} as const;

export type DegreeType = typeof DEGREE_TYPES[keyof typeof DEGREE_TYPES];

export const SUBJECT_TYPES = {
  CORE: 'core',
  ELECTIVE: 'elective',
  LAB: 'lab'
} as const;

export type SubjectType = typeof SUBJECT_TYPES[keyof typeof SUBJECT_TYPES];

export const STUDENT_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  GRADUATED: 'graduated',
  DROPPED: 'dropped'
} as const;

export type StudentStatus = typeof STUDENT_STATUS[keyof typeof STUDENT_STATUS];

// Timetable Constants
export const TIME_SLOT_TYPES = {
  LECTURE: 'lecture',
  LAB: 'lab',
  BREAK: 'break'
} as const;

export type TimeSlotType = typeof TIME_SLOT_TYPES[keyof typeof TIME_SLOT_TYPES];

export const TIMETABLE_ENTRY_TYPES = {
  LECTURE: 'lecture',
  LAB: 'lab',
  TUTORIAL: 'tutorial'
} as const;

export type TimetableEntryType = typeof TIMETABLE_ENTRY_TYPES[keyof typeof TIMETABLE_ENTRY_TYPES];

export const DAYS_OF_WEEK = {
  MONDAY: 1,
  TUESDAY: 2,
  WEDNESDAY: 3,
  THURSDAY: 4,
  FRIDAY: 5,
  SATURDAY: 6,
  SUNDAY: 7
} as const;

// Attendance Constants
export const ATTENDANCE_STATUS = {
  PRESENT: 'present',
  ABSENT: 'absent',
  LATE: 'late'
} as const;

export type AttendanceStatus = typeof ATTENDANCE_STATUS[keyof typeof ATTENDANCE_STATUS];

// Calendar Event Constants
export const EVENT_TYPES = {
  HOLIDAY: 'holiday',
  EXAM: 'exam',
  EVENT: 'event',
  PROJECT: 'project'
} as const;

export type EventType = typeof EVENT_TYPES[keyof typeof EVENT_TYPES];

export const EVENT_SCOPE_TYPES = {
  COLLEGE: 'college',
  DEPARTMENT: 'department',
  DEGREE: 'degree',
  BRANCH: 'branch',
  BATCH: 'batch',
  SECTION: 'section'
} as const;

export type EventScopeType = typeof EVENT_SCOPE_TYPES[keyof typeof EVENT_SCOPE_TYPES];

// Default Event Types with Colors (matching the UI)
export const DEFAULT_EVENT_TYPES = {
  HOLIDAY: { name: 'holiday', displayName: 'Holiday', color: '#22c55e' }, // green
  EXAM_INTERNAL: { name: 'exam_internal', displayName: 'Exams - Internals', color: '#f97316' }, // orange
  EXAM_EXTERNAL: { name: 'exam_external', displayName: 'Exams - External', color: '#dc2626' }, // red
  EVENT: { name: 'event', displayName: 'Event', color: '#8b5cf6' }, // purple
  PROJECT: { name: 'project', displayName: 'Major Project Initiation', color: '#3b82f6' }, // blue
  SEMINAR: { name: 'seminar', displayName: 'Seminar', color: '#06b6d4' }, // cyan
  WORKSHOP: { name: 'workshop', displayName: 'Workshop', color: '#10b981' }, // emerald
} as const;

// Role-based Calendar Event Management Permissions
export const CALENDAR_PERMISSIONS = {
  [CMS_USER_ROLES.PRINCIPAL]: {
    canCreate: [EVENT_SCOPE_TYPES.COLLEGE, EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION],
    canEdit: [EVENT_SCOPE_TYPES.COLLEGE, EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION],
    canDelete: [EVENT_SCOPE_TYPES.COLLEGE, EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION]
  },
  [CMS_USER_ROLES.COLLEGE_ADMIN]: {
    canCreate: [EVENT_SCOPE_TYPES.COLLEGE, EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION],
    canEdit: [EVENT_SCOPE_TYPES.COLLEGE, EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION],
    canDelete: [EVENT_SCOPE_TYPES.COLLEGE, EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION]
  },
  [CMS_USER_ROLES.HOD]: {
    canCreate: [EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION], // Only for their department
    canEdit: [EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION],
    canDelete: [EVENT_SCOPE_TYPES.DEPARTMENT, EVENT_SCOPE_TYPES.DEGREE, EVENT_SCOPE_TYPES.BRANCH, EVENT_SCOPE_TYPES.BATCH, EVENT_SCOPE_TYPES.SECTION]
  },
  [CMS_USER_ROLES.STAFF]: {
    canCreate: [], // Must be explicitly granted calendar permissions
    canEdit: [],
    canDelete: []
  }
} as const;

// Role-based default permissions
export const DEFAULT_ROLE_PERMISSIONS = {
  [CMS_USER_ROLES.PRINCIPAL]: {
    scope: PERMISSION_SCOPES.ALL,
    modules: Object.values(CMS_MODULES).map(module => ({
      module,
      canRead: true,
      canWrite: true
    }))
  },
  [CMS_USER_ROLES.COLLEGE_ADMIN]: {
    scope: PERMISSION_SCOPES.ALL,
    modules: Object.values(CMS_MODULES).map(module => ({
      module,
      canRead: true,
      canWrite: true
    }))
  },
  [CMS_USER_ROLES.HOD]: {
    scope: PERMISSION_SCOPES.DEPARTMENT,
    modules: Object.values(CMS_MODULES).map(module => ({
      module,
      canRead: true,
      canWrite: true // Can be customized per HOD
    }))
  },
  [CMS_USER_ROLES.STAFF]: {
    scope: PERMISSION_SCOPES.DEPARTMENT,
    modules: [
      // All staff get mandatory read access to Programs & Structure
      {
        module: CMS_MODULES.PROGRAMS_STRUCTURE,
        canRead: true,
        canWrite: false
      }
    ] // Other modules must be explicitly configured
  }
} as const;
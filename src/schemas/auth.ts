import { z } from 'zod';
import { 
  CMS_USER_ROLES, 
  CMS_MODULES, 
  DEPARTMENT_TYPES, 
  PERMISSION_SCOPES,
  DEGREE_TYPES,
  SUBJECT_TYPES,
  STUDENT_STATUS,
  TIME_SLOT_TYPES,
  TIMETABLE_ENTRY_TYPES,
  ATTENDANCE_STATUS,
  EVENT_TYPES,
  EVENT_SCOPE_TYPES
} from '../constants/roles';

// Request schemas
export const SendOTPRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
});

export const VerifyOTPRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  otp: z.string().length(6, 'OTP must be 6 digits'),
});

export const CompleteSignupRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  otp: z.string().length(6, 'OTP must be 6 digits'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const LoginRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  password: z.string().min(1, 'Password is required'),
});

export const UpdateUserRequestSchema = z.object({
  fullName: z.string().optional(),
  phone: z.string().optional(),
  role: z.enum([CMS_USER_ROLES.PRINCIPAL, CMS_USER_ROLES.COLLEGE_ADMIN, CMS_USER_ROLES.HOD, CMS_USER_ROLES.STAFF]).optional(),
  departmentId: z.string().uuid().optional(),
  hodId: z.string().uuid().optional(), // For staff assignments
  staffType: z.enum(['departmental', 'non_departmental']).optional(),
  jobTitle: z.string().optional(),
  isActive: z.boolean().optional(),
});

// Multi-step registration schemas
export const BasicInfoRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  otp: z.string().length(6, 'OTP must be 6 digits'),
  fullName: z.string().min(1, 'Full name is required'),
  phone: z.string().min(10, 'Valid phone number is required'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const CollegeDetailsRequestSchema = z.object({
  userId: z.string().uuid(),
  collegeName: z.string().min(1, 'College name is required'),
  shortName: z.string().optional(),
  collegeId: z.string().optional(),
  type: z.string().min(1, 'College type is required'),
  website: z.string().url().optional(),
  establishedYear: z.number().int().min(1800).max(new Date().getFullYear()).optional(),
  accreditation: z.string().optional(),
});

export const UniversityDetailsRequestSchema = z.object({
  userId: z.string().uuid(),
  universityName: z.string().min(1, 'University name is required'),
  shortName: z.string().optional(),
  universityId: z.string().optional(),
  state: z.string().min(1, 'State is required'),
  country: z.string().min(1, 'Country is required'),
});

export const AddressDetailsRequestSchema = z.object({
  userId: z.string().uuid(),
  street: z.string().min(1, 'Street address is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().min(1, 'State is required'),
  pincode: z.string().min(6, 'Valid pincode is required'),
  country: z.string().min(1, 'Country is required'),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
});

export const LogoUploadRequestSchema = z.object({
  userId: z.string().uuid(),
  collegeLogoUrl: z.string().url().optional(),
  universityLogoUrl: z.string().url().optional(),
});

// Department management schemas
export const CreateDepartmentRequestSchema = z.object({
  name: z.string().min(1, 'Department name is required'),
  code: z.string().min(2, 'Department code is required').max(10),
  description: z.string().optional(),
  type: z.enum([DEPARTMENT_TYPES.ACADEMIC, DEPARTMENT_TYPES.ADMINISTRATIVE]),
  hodId: z.string().uuid().optional(),
});

export const UpdateDepartmentRequestSchema = z.object({
  name: z.string().min(1).optional(),
  code: z.string().min(2).max(10).optional(),
  description: z.string().optional(),
  type: z.enum([DEPARTMENT_TYPES.ACADEMIC, DEPARTMENT_TYPES.ADMINISTRATIVE]).optional(),
  hodId: z.string().uuid().optional(),
  isActive: z.boolean().optional(),
});

export const AssignHODRequestSchema = z.object({
  departmentId: z.string().uuid(),
  userId: z.string().uuid(),
});

// User management schemas
export const CreateUserRequestSchema = z.object({
  email: z.string().email('Invalid email format'),
  fullName: z.string().min(1, 'Full name is required'),
  phone: z.string().min(10, 'Valid phone number is required'),
  role: z.enum([CMS_USER_ROLES.COLLEGE_ADMIN, CMS_USER_ROLES.HOD, CMS_USER_ROLES.STAFF]),
  departmentId: z.string().uuid().optional(), // Required for HOD, optional for Staff
  staffType: z.enum(['departmental', 'non_departmental']).optional(), // For staff classification
  jobTitle: z.string().optional(), // For non-departmental staff roles
  password: z.string().min(8, 'Password must be at least 8 characters'),
})
  .refine((data) => {
    // HODs must have a department
    if (data.role === 'hod' && !data.departmentId) {
      return false;
    }
    return true;
  }, {
    message: "HOD role requires department assignment",
    path: ["departmentId"]
  });

export const AssignRoleRequestSchema = z.object({
  userId: z.string().uuid(),
  role: z.enum([CMS_USER_ROLES.COLLEGE_ADMIN, CMS_USER_ROLES.HOD, CMS_USER_ROLES.STAFF]),
  departmentId: z.string().uuid().optional(),
  hodId: z.string().uuid().optional(),
  staffType: z.enum(['departmental', 'non_departmental']).optional(),
  jobTitle: z.string().optional(),
})
  .refine((data) => {
    // HODs must have a department
    if (data.role === 'hod' && !data.departmentId) {
      return false;
    }
    return true;
  }, {
    message: "HOD role requires department assignment",
    path: ["departmentId"]
  });

// Module permission schemas
export const ModulePermissionSchema = z.object({
  module: z.enum(Object.values(CMS_MODULES) as [string, ...string[]]),
  canRead: z.boolean(),
  canWrite: z.boolean(),
  scope: z.enum([PERMISSION_SCOPES.ALL, PERMISSION_SCOPES.DEPARTMENT, PERMISSION_SCOPES.OWN]).optional(),
});

export const UpdateUserPermissionsRequestSchema = z.object({
  userId: z.string().uuid(),
  permissions: z.array(ModulePermissionSchema),
});

// Response schemas
export const AuthResponseSchema = z.object({
  accessToken: z.string(),
  tokenType: z.string(),
  cmsUserId: z.string(),
  role: z.string().optional(),
  profileCompleted: z.boolean(),
});

export const UserResponseSchema = z.object({
  id: z.string(),
  email: z.string(),
  fullName: z.string().nullable(),
  phone: z.string().nullable(),
  role: z.string().nullable(),
  departmentId: z.string().nullable(),
  department: z.object({
    id: z.string(),
    name: z.string(),
    code: z.string(),
    type: z.string(),
  }).nullable(),
  hodId: z.string().nullable(),
  hod: z.object({
    id: z.string(),
    fullName: z.string(),
    email: z.string(),
  }).nullable(),
  collegeId: z.string().nullable(),
  staffType: z.string().nullable(), // 'departmental' or 'non_departmental'
  jobTitle: z.string().nullable(), // For non-departmental staff
  isActive: z.boolean(),
  modulePermissions: z.array(z.object({
    module: z.string(),
    canRead: z.boolean(),
    canWrite: z.boolean(),
    scope: z.string().optional(),
  })).nullable(),
  lastLogin: z.string().nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const DepartmentResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  code: z.string(),
  description: z.string().nullable(),
  type: z.string(),
  hod: z.object({
    id: z.string(),
    fullName: z.string(),
    email: z.string(),
  }).nullable(),
  staffCount: z.number(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const CollegeResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  shortName: z.string().nullable(),
  collegeId: z.string().nullable(),
  type: z.string().nullable(),
  website: z.string().nullable(),
  establishedYear: z.number().nullable(),
  accreditation: z.string().nullable(),
  logoUrl: z.string().nullable(),
  email: z.string().nullable(),
  phone: z.string().nullable(),
  addressDetails: z.any().nullable(),
  affiliatedUniversity: z.any().nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const SuccessResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

export const ErrorResponseSchema = z.object({
  error: z.string(),
  detail: z.string().optional(),
  errorCode: z.string().optional(),
  requestId: z.string().optional(),
});

// Academic Hierarchy Schemas
export const CreateBatchRequestSchema = z.object({
  name: z.string().min(1, 'Batch name is required'),
  year: z.number().int().min(2000).max(2100),
  startDate: z.string().datetime(),
  endDate: z.string().datetime(),
});

export const CreateDegreeRequestSchema = z.object({
  name: z.string().min(1, 'Degree name is required'),
  shortName: z.string().min(1, 'Short name is required'),
  duration: z.number().int().min(1).max(10),
  type: z.enum([DEGREE_TYPES.UNDERGRADUATE, DEGREE_TYPES.POSTGRADUATE, DEGREE_TYPES.DOCTORATE]),
});

export const CreateBranchRequestSchema = z.object({
  degreeId: z.string().uuid(),
  departmentId: z.string().uuid(),
  name: z.string().min(1, 'Branch name is required'),
  shortName: z.string().min(1, 'Short name is required'),
  code: z.string().min(1, 'Branch code is required'),
});

export const CreateSubjectRequestSchema = z.object({
  branchId: z.string().uuid(),
  name: z.string().min(1, 'Subject name is required'),
  code: z.string().min(1, 'Subject code is required'),
  credits: z.number().int().min(1).max(20),
  semester: z.number().int().min(1).max(10),
  type: z.enum([SUBJECT_TYPES.CORE, SUBJECT_TYPES.ELECTIVE, SUBJECT_TYPES.LAB]),
});

export const CreateSectionRequestSchema = z.object({
  batchId: z.string().uuid(),
  branchId: z.string().uuid(),
  name: z.string().min(1, 'Section name is required'),
  capacity: z.number().int().min(1).max(200),
});

export const CreateStudentRequestSchema = z.object({
  batchId: z.string().uuid(),
  branchId: z.string().uuid(),
  sectionId: z.string().uuid(),
  rollNumber: z.string().min(1, 'Roll number is required'),
  registrationNumber: z.string().optional(),
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  dateOfBirth: z.string().datetime().optional(),
  gender: z.enum(['male', 'female', 'other']).optional(),
  admissionDate: z.string().datetime(),
});

// Timetable Schemas
export const CreateTimeSlotRequestSchema = z.object({
  name: z.string().min(1, 'Time slot name is required'),
  startTime: z.string().regex(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/, 'Invalid time format'),
  endTime: z.string().regex(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/, 'Invalid time format'),
  duration: z.number().int().min(30).max(180), // 30 minutes to 3 hours
  type: z.enum([TIME_SLOT_TYPES.LECTURE, TIME_SLOT_TYPES.LAB, TIME_SLOT_TYPES.BREAK]),
});

export const CreateTimetableRequestSchema = z.object({
  sectionId: z.string().uuid(),
  batchId: z.string().uuid(),
  name: z.string().min(1, 'Timetable name is required'),
  academicYear: z.string().min(1, 'Academic year is required'),
  semester: z.number().int().min(1).max(10),
});

export const CreateTimetableEntryRequestSchema = z.object({
  timetableId: z.string().uuid(),
  subjectId: z.string().uuid(),
  teacherId: z.string().uuid(),
  timeSlotId: z.string().uuid(),
  dayOfWeek: z.number().int().min(1).max(7), // 1=Monday, 7=Sunday
  roomNumber: z.string().optional(),
  type: z.enum([TIMETABLE_ENTRY_TYPES.LECTURE, TIMETABLE_ENTRY_TYPES.LAB, TIMETABLE_ENTRY_TYPES.TUTORIAL]),
});

// Attendance Schemas
export const MarkAttendanceRequestSchema = z.object({
  timetableEntryId: z.string().uuid(),
  attendanceRecords: z.array(z.object({
    studentId: z.string().uuid(),
    status: z.enum([ATTENDANCE_STATUS.PRESENT, ATTENDANCE_STATUS.ABSENT, ATTENDANCE_STATUS.LATE]),
    remarks: z.string().optional(),
  })),
  date: z.string().datetime(),
});

export const GetAttendanceRequestSchema = z.object({
  sectionId: z.string().uuid().optional(),
  subjectId: z.string().uuid().optional(),
  studentId: z.string().uuid().optional(),
  teacherId: z.string().uuid().optional(),
  startDate: z.string().datetime().optional(),
  endDate: z.string().datetime().optional(),
});

// Calendar Event Schemas
export const CreateEventTypeRequestSchema = z.object({
  name: z.string().min(1, 'Event type name is required'),
  displayName: z.string().min(1, 'Display name is required'),
  color: z.string().regex(/^#[0-9A-F]{6}$/i, 'Invalid color format'),
});

export const CreateCalendarEventRequestSchema = z.object({
  eventTypeId: z.string().uuid(),
  title: z.string().min(1, 'Event title is required'),
  description: z.string().optional(),
  startDate: z.string().datetime(),
  endDate: z.string().datetime(),
  scopeType: z.enum([
    EVENT_SCOPE_TYPES.COLLEGE,
    EVENT_SCOPE_TYPES.DEPARTMENT,
    EVENT_SCOPE_TYPES.DEGREE,
    EVENT_SCOPE_TYPES.BRANCH,
    EVENT_SCOPE_TYPES.BATCH,
    EVENT_SCOPE_TYPES.SECTION
  ]),
  scopeId: z.string().uuid().optional(), // Optional for college-wide events
  isAllDay: z.boolean().default(false),
  isRecurring: z.boolean().default(false),
  recurringPattern: z.any().optional(), // JSON object for recurring patterns
});

export const GetCalendarEventsRequestSchema = z.object({
  degreeId: z.string().uuid().optional(),
  batchId: z.string().uuid().optional(),
  branchId: z.string().uuid().optional(),
  startDate: z.string().datetime().optional(),
  endDate: z.string().datetime().optional(),
  eventTypeId: z.string().uuid().optional(),
});

// Response Schemas
export const BatchResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  year: z.number(),
  startDate: z.string(),
  endDate: z.string(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const DegreeResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  shortName: z.string(),
  duration: z.number(),
  type: z.string(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const BranchResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  shortName: z.string(),
  code: z.string(),
  degree: DegreeResponseSchema.nullable(),
  department: DepartmentResponseSchema.nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const SubjectResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  code: z.string(),
  credits: z.number(),
  semester: z.number(),
  type: z.string(),
  branch: BranchResponseSchema.nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const SectionResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  capacity: z.number(),
  currentStrength: z.number(),
  batch: BatchResponseSchema.nullable(),
  branch: BranchResponseSchema.nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const StudentResponseSchema = z.object({
  id: z.string(),
  rollNumber: z.string(),
  registrationNumber: z.string().nullable(),
  firstName: z.string(),
  lastName: z.string(),
  email: z.string().nullable(),
  phone: z.string().nullable(),
  dateOfBirth: z.string().nullable(),
  gender: z.string().nullable(),
  admissionDate: z.string(),
  status: z.string(),
  batch: BatchResponseSchema.nullable(),
  branch: BranchResponseSchema.nullable(),
  section: SectionResponseSchema.nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const TimeSlotResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  startTime: z.string(),
  endTime: z.string(),
  duration: z.number(),
  type: z.string(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const TimetableResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  academicYear: z.string(),
  semester: z.number(),
  section: SectionResponseSchema.nullable(),
  batch: BatchResponseSchema.nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const TimetableEntryResponseSchema = z.object({
  id: z.string(),
  dayOfWeek: z.number(),
  roomNumber: z.string().nullable(),
  type: z.string(),
  timetable: TimetableResponseSchema.nullable(),
  subject: SubjectResponseSchema.nullable(),
  teacher: UserResponseSchema.nullable(),
  timeSlot: TimeSlotResponseSchema.nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const AttendanceRecordResponseSchema = z.object({
  id: z.string(),
  date: z.string(),
  status: z.string(),
  remarks: z.string().nullable(),
  markedAt: z.string(),
  timetableEntry: TimetableEntryResponseSchema.nullable(),
  student: StudentResponseSchema.nullable(),
  teacher: UserResponseSchema.nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const EventTypeResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  displayName: z.string(),
  color: z.string(),
  isActive: z.boolean(),
  createdAt: z.string(),
});

export const CalendarEventResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().nullable(),
  startDate: z.string(),
  endDate: z.string(),
  scopeType: z.string(),
  scopeId: z.string().nullable(),
  isAllDay: z.boolean(),
  isRecurring: z.boolean(),
  recurringPattern: z.any().nullable(),
  eventType: EventTypeResponseSchema,
  createdByUser: UserResponseSchema.nullable(),
  isActive: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

// Type exports
export type SendOTPRequest = z.infer<typeof SendOTPRequestSchema>;
export type VerifyOTPRequest = z.infer<typeof VerifyOTPRequestSchema>;
export type CompleteSignupRequest = z.infer<typeof CompleteSignupRequestSchema>;
export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type UpdateUserRequest = z.infer<typeof UpdateUserRequestSchema>;

// Multi-step registration types
export type BasicInfoRequest = z.infer<typeof BasicInfoRequestSchema>;
export type CollegeDetailsRequest = z.infer<typeof CollegeDetailsRequestSchema>;
export type UniversityDetailsRequest = z.infer<typeof UniversityDetailsRequestSchema>;
export type AddressDetailsRequest = z.infer<typeof AddressDetailsRequestSchema>;
export type LogoUploadRequest = z.infer<typeof LogoUploadRequestSchema>;

// Department management types
export type CreateDepartmentRequest = z.infer<typeof CreateDepartmentRequestSchema>;
export type UpdateDepartmentRequest = z.infer<typeof UpdateDepartmentRequestSchema>;
export type AssignHODRequest = z.infer<typeof AssignHODRequestSchema>;

// User management types
export type CreateUserRequest = z.infer<typeof CreateUserRequestSchema>;
export type AssignRoleRequest = z.infer<typeof AssignRoleRequestSchema>;

// Permission types
export type ModulePermission = z.infer<typeof ModulePermissionSchema>;
export type UpdateUserPermissionsRequest = z.infer<typeof UpdateUserPermissionsRequestSchema>;

// Academic hierarchy types
export type CreateBatchRequest = z.infer<typeof CreateBatchRequestSchema>;
export type CreateDegreeRequest = z.infer<typeof CreateDegreeRequestSchema>;
export type CreateBranchRequest = z.infer<typeof CreateBranchRequestSchema>;
export type CreateSubjectRequest = z.infer<typeof CreateSubjectRequestSchema>;
export type CreateSectionRequest = z.infer<typeof CreateSectionRequestSchema>;
export type CreateStudentRequest = z.infer<typeof CreateStudentRequestSchema>;

// Timetable types
export type CreateTimeSlotRequest = z.infer<typeof CreateTimeSlotRequestSchema>;
export type CreateTimetableRequest = z.infer<typeof CreateTimetableRequestSchema>;
export type CreateTimetableEntryRequest = z.infer<typeof CreateTimetableEntryRequestSchema>;

// Attendance types
export type MarkAttendanceRequest = z.infer<typeof MarkAttendanceRequestSchema>;
export type GetAttendanceRequest = z.infer<typeof GetAttendanceRequestSchema>;

// Calendar types
export type CreateEventTypeRequest = z.infer<typeof CreateEventTypeRequestSchema>;
export type CreateCalendarEventRequest = z.infer<typeof CreateCalendarEventRequestSchema>;
export type GetCalendarEventsRequest = z.infer<typeof GetCalendarEventsRequestSchema>;

// Response types
export type AuthResponse = z.infer<typeof AuthResponseSchema>;
export type UserResponse = z.infer<typeof UserResponseSchema>;
export type DepartmentResponse = z.infer<typeof DepartmentResponseSchema>;
export type CollegeResponse = z.infer<typeof CollegeResponseSchema>;
export type SuccessResponse = z.infer<typeof SuccessResponseSchema>;
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

// Academic hierarchy response types
export type BatchResponse = z.infer<typeof BatchResponseSchema>;
export type DegreeResponse = z.infer<typeof DegreeResponseSchema>;
export type BranchResponse = z.infer<typeof BranchResponseSchema>;
export type SubjectResponse = z.infer<typeof SubjectResponseSchema>;
export type SectionResponse = z.infer<typeof SectionResponseSchema>;
export type StudentResponse = z.infer<typeof StudentResponseSchema>;

// Timetable response types
export type TimeSlotResponse = z.infer<typeof TimeSlotResponseSchema>;
export type TimetableResponse = z.infer<typeof TimetableResponseSchema>;
export type TimetableEntryResponse = z.infer<typeof TimetableEntryResponseSchema>;

// Attendance response types
export type AttendanceRecordResponse = z.infer<typeof AttendanceRecordResponseSchema>;

// Calendar response types
export type EventTypeResponse = z.infer<typeof EventTypeResponseSchema>;
export type CalendarEventResponse = z.infer<typeof CalendarEventResponseSchema>;
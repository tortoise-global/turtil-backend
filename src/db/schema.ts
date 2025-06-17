import { pgTable, text, integer, boolean, jsonb, timestamp, uuid } from 'drizzle-orm/pg-core';
import { sql } from 'drizzle-orm';

export const cmsUsers = pgTable('cms_users', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  email: text('email').unique().notNull(),
  passwordHash: text('password_hash').notNull(),
  fullName: text('full_name'),
  phone: text('phone'),
  role: text('role').notNull(), // 'principal', 'college_admin', 'hod', 'staff'
  
  // Department and hierarchy fields
  departmentId: uuid('department_id').references(() => departments.id), // Required for HOD, optional for Staff
  hodId: uuid('hod_id').references(() => cmsUsers.id), // For departmental staff to reference their HOD
  collegeId: uuid('college_id').references(() => colleges.id),
  
  // Staff classification fields
  staffType: text('staff_type'), // 'departmental', 'non_departmental' - for staff only
  jobTitle: text('job_title'), // For non-departmental staff (Banking Staff, Security, etc.)
  
  // Essential fields only
  isActive: boolean('is_active').default(true),
  
  // Timestamps
  lastLogin: timestamp('last_login'),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Colleges table
export const colleges = pgTable('colleges', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  name: text('name').notNull(),
  shortName: text('short_name'),
  collegeId: text('college_id').unique(),
  type: text('type'), // 'university', 'autonomous', 'affiliated'
  website: text('website'),
  establishedYear: integer('established_year'),
  accreditation: text('accreditation'),
  
  // Logo and branding
  logoUrl: text('logo_url'),
  
  // Contact information
  email: text('email'),
  phone: text('phone'),
  
  // Address
  addressDetails: jsonb('address_details'),
  
  // University affiliation
  affiliatedUniversity: jsonb('affiliated_university'),
  
  // Settings
  settings: jsonb('settings'),
  isActive: boolean('is_active').default(true),
  
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Departments table
export const departments = pgTable('departments', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  name: text('name').notNull(),
  code: text('code').notNull(), // 'CSE', 'ECE', 'MECH', 'ADMIN', etc.
  description: text('description'),
  type: text('type').notNull(), // 'academic', 'administrative'
  
  // HOD assignment - only one HOD per department
  hodId: uuid('hod_id').references(() => cmsUsers.id),
  
  // Department settings
  isActive: boolean('is_active').default(true),
  
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// User module permissions table
export const userModulePermissions = pgTable('user_module_permissions', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  userId: uuid('user_id').references(() => cmsUsers.id).notNull(),
  module: text('module').notNull(), // From CMS_MODULES enum
  canRead: boolean('can_read').default(false),
  canWrite: boolean('can_write').default(false),
  scope: text('scope').default('all'), // 'all', 'department', 'own'
  
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// College modules configuration
export const collegeModules = pgTable('college_modules', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  module: text('module').notNull(), // From CMS_MODULES enum
  isEnabled: boolean('is_enabled').default(true),
  settings: jsonb('settings'),
  
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const otpCodes = pgTable('otp_codes', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  email: text('email').notNull(),
  code: text('code').notNull(),
  expiresAt: timestamp('expires_at').notNull(),
  used: boolean('used').default(false),
  createdAt: timestamp('created_at').defaultNow(),
});

// Academic hierarchy tables
export const batches = pgTable('batches', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  name: text('name').notNull(), // '2023-2024', '2024-2025'
  year: integer('year').notNull(), // 2023, 2024
  startDate: timestamp('start_date').notNull(),
  endDate: timestamp('end_date').notNull(),
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const degrees = pgTable('degrees', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  name: text('name').notNull(), // 'Bachelor of Technology', 'Master of Technology'
  shortName: text('short_name').notNull(), // 'B.Tech', 'M.Tech'
  duration: integer('duration').notNull(), // Duration in years
  type: text('type').notNull(), // 'undergraduate', 'postgraduate'
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const branches = pgTable('branches', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  degreeId: uuid('degree_id').references(() => degrees.id).notNull(),
  departmentId: uuid('department_id').references(() => departments.id).notNull(),
  name: text('name').notNull(), // 'Computer Science & Engineering'
  shortName: text('short_name').notNull(), // 'CSE'
  code: text('code').notNull(), // 'CSE', 'ECE', 'MECH'
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const subjects = pgTable('subjects', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  branchId: uuid('branch_id').references(() => branches.id).notNull(),
  name: text('name').notNull(), // 'Programming Fundamentals'
  code: text('code').notNull(), // 'CS101'
  credits: integer('credits').notNull(),
  semester: integer('semester').notNull(), // 1, 2, 3, etc.
  type: text('type').notNull(), // 'core', 'elective', 'lab'
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const sections = pgTable('sections', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  batchId: uuid('batch_id').references(() => batches.id).notNull(),
  branchId: uuid('branch_id').references(() => branches.id).notNull(),
  name: text('name').notNull(), // 'A', 'B', 'C'
  capacity: integer('capacity').notNull(),
  currentStrength: integer('current_strength').default(0),
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const students = pgTable('students', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  batchId: uuid('batch_id').references(() => batches.id).notNull(),
  branchId: uuid('branch_id').references(() => branches.id).notNull(),
  sectionId: uuid('section_id').references(() => sections.id).notNull(),
  rollNumber: text('roll_number').unique().notNull(),
  registrationNumber: text('registration_number').unique(),
  firstName: text('first_name').notNull(),
  lastName: text('last_name').notNull(),
  email: text('email').unique(),
  phone: text('phone'),
  dateOfBirth: timestamp('date_of_birth'),
  gender: text('gender'), // 'male', 'female', 'other'
  admissionDate: timestamp('admission_date').notNull(),
  status: text('status').default('active'), // 'active', 'inactive', 'graduated', 'dropped'
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Timetable system
export const timeSlots = pgTable('time_slots', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  name: text('name').notNull(), // '9:00 AM - 10:00 AM'
  startTime: text('start_time').notNull(), // '09:00'
  endTime: text('end_time').notNull(), // '10:00'
  duration: integer('duration').notNull(), // Duration in minutes
  type: text('type').notNull(), // 'lecture', 'lab', 'break'
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const timetables = pgTable('timetables', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  sectionId: uuid('section_id').references(() => sections.id).notNull(),
  batchId: uuid('batch_id').references(() => batches.id).notNull(),
  name: text('name').notNull(), // 'CSE A Section Timetable'
  academicYear: text('academic_year').notNull(), // '2023-2024'
  semester: integer('semester').notNull(),
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

export const timetableEntries = pgTable('timetable_entries', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  timetableId: uuid('timetable_id').references(() => timetables.id).notNull(),
  subjectId: uuid('subject_id').references(() => subjects.id).notNull(),
  teacherId: uuid('teacher_id').references(() => cmsUsers.id).notNull(),
  timeSlotId: uuid('time_slot_id').references(() => timeSlots.id).notNull(),
  dayOfWeek: integer('day_of_week').notNull(), // 1=Monday, 2=Tuesday, etc.
  roomNumber: text('room_number'),
  type: text('type').notNull(), // 'lecture', 'lab', 'tutorial'
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Attendance system
export const attendanceRecords = pgTable('attendance_records', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  timetableEntryId: uuid('timetable_entry_id').references(() => timetableEntries.id).notNull(),
  studentId: uuid('student_id').references(() => students.id).notNull(),
  teacherId: uuid('teacher_id').references(() => cmsUsers.id).notNull(),
  date: timestamp('date').notNull(),
  status: text('status').notNull(), // 'present', 'absent', 'late'
  markedAt: timestamp('marked_at').defaultNow(),
  remarks: text('remarks'),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Academic calendar system
export const eventTypes = pgTable('event_types', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  name: text('name').notNull(), // 'holiday', 'exam', 'event', 'project'
  displayName: text('display_name').notNull(), // 'Holiday', 'Exams - Internals'
  color: text('color').notNull(), // '#green', '#orange', '#purple', '#blue'
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
});

export const calendarEvents = pgTable('calendar_events', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  collegeId: uuid('college_id').references(() => colleges.id).notNull(),
  eventTypeId: uuid('event_type_id').references(() => eventTypes.id).notNull(),
  title: text('title').notNull(),
  description: text('description'),
  startDate: timestamp('start_date').notNull(),
  endDate: timestamp('end_date').notNull(),
  
  // Hierarchical scope for event inheritance
  scopeType: text('scope_type').notNull(), // 'college', 'department', 'degree', 'branch', 'batch', 'section'
  scopeId: uuid('scope_id'), // Reference to department, degree, branch, batch, or section
  
  // Creator information
  createdByUserId: uuid('created_by_user_id').references(() => cmsUsers.id).notNull(),
  
  // Event settings
  isAllDay: boolean('is_all_day').default(false),
  isRecurring: boolean('is_recurring').default(false),
  recurringPattern: jsonb('recurring_pattern'), // For future recurring events
  isActive: boolean('is_active').default(true),
  
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Type exports
export type CMSUser = typeof cmsUsers.$inferSelect;
export type NewCMSUser = typeof cmsUsers.$inferInsert;
export type College = typeof colleges.$inferSelect;
export type NewCollege = typeof colleges.$inferInsert;
export type Department = typeof departments.$inferSelect;
export type NewDepartment = typeof departments.$inferInsert;
export type UserModulePermission = typeof userModulePermissions.$inferSelect;
export type NewUserModulePermission = typeof userModulePermissions.$inferInsert;
export type CollegeModule = typeof collegeModules.$inferSelect;
export type NewCollegeModule = typeof collegeModules.$inferInsert;
export type OTPCode = typeof otpCodes.$inferSelect;
export type NewOTPCode = typeof otpCodes.$inferInsert;

// Academic hierarchy types
export type Batch = typeof batches.$inferSelect;
export type NewBatch = typeof batches.$inferInsert;
export type Degree = typeof degrees.$inferSelect;
export type NewDegree = typeof degrees.$inferInsert;
export type Branch = typeof branches.$inferSelect;
export type NewBranch = typeof branches.$inferInsert;
export type Subject = typeof subjects.$inferSelect;
export type NewSubject = typeof subjects.$inferInsert;
export type Section = typeof sections.$inferSelect;
export type NewSection = typeof sections.$inferInsert;
export type Student = typeof students.$inferSelect;
export type NewStudent = typeof students.$inferInsert;

// Timetable types
export type TimeSlot = typeof timeSlots.$inferSelect;
export type NewTimeSlot = typeof timeSlots.$inferInsert;
export type Timetable = typeof timetables.$inferSelect;
export type NewTimetable = typeof timetables.$inferInsert;
export type TimetableEntry = typeof timetableEntries.$inferSelect;
export type NewTimetableEntry = typeof timetableEntries.$inferInsert;

// Attendance types
export type AttendanceRecord = typeof attendanceRecords.$inferSelect;
export type NewAttendanceRecord = typeof attendanceRecords.$inferInsert;

// Calendar types
export type EventType = typeof eventTypes.$inferSelect;
export type NewEventType = typeof eventTypes.$inferInsert;
export type CalendarEvent = typeof calendarEvents.$inferSelect;
export type NewCalendarEvent = typeof calendarEvents.$inferInsert;
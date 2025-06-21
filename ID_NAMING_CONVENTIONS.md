# ID Naming Conventions Documentation

This document explains the ID naming conventions used throughout the Turtil Backend project, covering database fields, JSON responses, and the reasoning behind these design decisions.

## Table of Contents
- [Overview](#overview)
- [Database Field Naming](#database-field-naming)
- [JSON Response Field Naming](#json-response-field-naming)
- [Code Examples](#code-examples)
- [Why This Convention is Better](#why-this-convention-is-better)
- [Industry Standards](#industry-standards)
- [Quick Reference](#quick-reference)

## Overview

The project follows a consistent ID naming pattern that distinguishes between:
- **Primary Keys**: Simple `id` field in each table
- **Foreign Keys**: Descriptive names indicating the referenced table
- **JSON Responses**: camelCase versions of database fields

## Database Field Naming

### Primary Keys
All tables use a simple `id` field as the primary key:

```sql
-- Staff table
staff.id (Primary Key)

-- College table  
college.id (Primary Key)

-- Department table
department.id (Primary Key)
```

**Why not `staff.staff_id`?**
- Redundant: You're already in the staff table context
- Non-standard: ORMs like SQLAlchemy use `id` by default
- Verbose: Adds unnecessary complexity

### Foreign Keys
Foreign keys use descriptive names that indicate what they reference:

```sql
-- Staff table foreign keys
staff.college_id → references college.id
staff.department_id → references department.id
staff.invited_by_staff_id → references staff.id

-- Department table foreign keys  
department.college_id → references college.id
department.hod_cms_staff_id → references staff.id
```

**Pattern**: `{referenced_table}_{context}_id`
- `college_id` - references colleges table
- `hod_cms_staff_id` - references staff table (Head of Department context)

## JSON Response Field Naming

### Conversion Rules
Database snake_case fields are converted to camelCase for JSON responses:

```python
# Database → JSON Response
id → id (unchanged for primary keys in context)
college_id → collegeId
department_id → departmentId
hod_cms_staff_id → hodCmsStaffId
staff.id → staffId (when referencing staff)
```

### Context-Aware Naming
The JSON field name depends on the response context:

```python
# In Staff response context
{
    "staffId": staff.id,           # Primary key becomes staffId
    "collegeId": staff.college_id, # Foreign key becomes collegeId
    "departmentId": staff.department_id
}

# In College response context  
{
    "collegeId": college.id,       # Primary key becomes collegeId
    "name": college.name
}
```

## Code Examples

### Database Model Definitions

```python
# Staff Model
class Staff(BaseModel):
    __tablename__ = "staff"
    
    id = Column(Integer, primary_key=True)           # Primary key
    college_id = Column(Integer, ForeignKey("colleges.id"))     # Foreign key
    department_id = Column(Integer, ForeignKey("departments.id")) # Foreign key
    invited_by_staff_id = Column(Integer, ForeignKey("staff.id")) # Self-reference

# Department Model  
class Department(BaseModel):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True)           # Primary key
    college_id = Column(Integer, ForeignKey("colleges.id"))     # Foreign key
    hod_cms_staff_id = Column(Integer, ForeignKey("staff.id"))  # Foreign key to staff
```

### JSON Response Schemas

```python
# StaffProfileResponse
class StaffProfileResponse(BaseModel):
    staffId: int                    # staff.id
    collegeId: Optional[int]        # staff.college_id  
    departmentId: Optional[int]     # staff.department_id

# DepartmentResponse
class DepartmentResponse(BaseModel):
    id: int                         # department.id (in department context)
    collegeId: int                  # department.college_id
    hodCmsStaffId: Optional[int]    # department.hod_cms_staff_id
```

### Database Queries

```python
# Query by primary key
staff = await db.execute(
    select(Staff).where(Staff.id == staff_id)
)

# Query by foreign key
college_staff = await db.execute(
    select(Staff).where(Staff.college_id == current_staff.college_id)
)

# Join queries using foreign keys
staff_with_department = await db.execute(
    select(Staff, Department)
    .join(Department, Staff.department_id == Department.id)
)
```

## Why This Convention is Better

### ❌ Alternative Approach (Not Recommended)
```python
# Database (Redundant)
staff.staff_id  # Redundant - already in staff table
college.college_id  # Redundant - already in college table

# JSON Response (Non-standard)
staff[StaffId]  # Non-standard array-like syntax
college[CollegeId]  # Confusing syntax
```

### ✅ Current Approach (Recommended)
```python
# Database (Clean)
staff.id        # Clear primary key
staff.college_id  # Clear foreign key reference

# JSON Response (Standard)
staffId         # Standard camelCase
collegeId       # Clear and consistent
```

### Advantages of Current Approach:

1. **No Redundancy**: `staff.id` vs `staff.staff_id`
2. **Industry Standard**: Follows ORM conventions (SQLAlchemy, Django, etc.)
3. **Clear Relationships**: `college_id` clearly references colleges table
4. **REST API Standards**: camelCase JSON fields
5. **Maintainability**: Consistent patterns across the codebase
6. **Database Efficiency**: Standard indexing patterns work optimally

## Industry Standards

### Database Design Standards
- **Primary Keys**: Always use simple `id`
- **Foreign Keys**: Use `{table}_id` pattern
- **Indexes**: Database systems optimize for `id` field names
- **ORM Compatibility**: Works seamlessly with all major ORMs

### API Design Standards
- **REST APIs**: Use camelCase for JSON field names
- **GraphQL**: Follows same camelCase conventions
- **OpenAPI/Swagger**: Standard documentation patterns

### Framework Examples
```python
# SQLAlchemy (Python)
class User(Base):
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'))

# Django (Python)  
class User(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey('Company', on_delete=models.CASCADE)

# Rails (Ruby)
class User < ApplicationRecord
  belongs_to :company  # Creates company_id foreign key
end
```

## Quick Reference

### Database Field Patterns
| Pattern | Example | Purpose |
|---------|---------|----------|
| `id` | `staff.id` | Primary key |
| `{table}_id` | `college_id` | Simple foreign key |
| `{context}_{table}_id` | `hod_cms_staff_id` | Contextual foreign key |

### JSON Response Patterns  
| Database Field | JSON Field | Context |
|----------------|------------|---------|
| `staff.id` | `staffId` | Staff response |
| `college.id` | `collegeId` | College response |  
| `staff.college_id` | `collegeId` | Foreign key reference |
| `department.hod_cms_staff_id` | `hodCmsStaffId` | HOD reference |

### Query Patterns
```python
# Primary key queries
select(Model).where(Model.id == value)

# Foreign key queries  
select(Model).where(Model.other_table_id == value)

# Join queries
select(Model1, Model2).join(Model2, Model1.other_id == Model2.id)
```

## Conclusion

The current ID naming convention in the Turtil Backend follows industry best practices and provides:
- **Clarity**: Clear distinction between primary and foreign keys
- **Consistency**: Uniform patterns across all tables and APIs
- **Maintainability**: Easy to understand and modify
- **Performance**: Optimized for database operations
- **Standards Compliance**: Follows REST API and database design standards

This documentation should be referenced whenever adding new models, APIs, or modifying existing database schemas to ensure consistency across the project.
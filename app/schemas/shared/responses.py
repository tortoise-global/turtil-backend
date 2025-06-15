"""Shared response models for API endpoints.

This module contains common response models used across different API modules.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """Standard message response model."""

    message: str
    success: Optional[bool] = True

    model_config = ConfigDict(populate_by_name=True)


class CreatedResponse(BaseModel):
    """Response model for resource creation."""

    message: str
    id: UUID
    success: bool = True

    model_config = ConfigDict(populate_by_name=True)


class UpdatedResponse(BaseModel):
    """Response model for resource updates."""

    message: str
    success: bool = True

    model_config = ConfigDict(populate_by_name=True)


class DeletedResponse(BaseModel):
    """Response model for resource deletion."""

    message: str
    success: bool = True

    model_config = ConfigDict(populate_by_name=True)


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""

    error: str
    detail: str
    validation_errors: List[dict] = Field(
        default_factory=list, alias="validationErrors"
    )

    model_config = ConfigDict(populate_by_name=True)


class PaginatedResponse(BaseModel):
    """Paginated response model."""

    data: List[dict]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    total_pages: int = Field(..., alias="totalPages")
    has_next: bool = Field(..., alias="hasNext")
    has_previous: bool = Field(..., alias="hasPrevious")

    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: float
    services: Optional[dict] = None

    model_config = ConfigDict(populate_by_name=True)


class UserActionResponse(BaseModel):
    """Response model for user actions."""

    message: str
    user_id: str = Field(..., alias="userId")
    action: str
    timestamp: Optional[int] = None
    success: bool = True

    model_config = ConfigDict(populate_by_name=True)


class RolePermissionResponse(BaseModel):
    """Response model for role permissions."""

    current_user_role: str = Field(..., alias="currentUserRole")
    can_create_roles: List[str] = Field(..., alias="canCreateRoles")
    permissions: Optional[dict] = None

    model_config = ConfigDict(populate_by_name=True)


class UserCreationResponse(BaseModel):
    """Response model for user creation."""

    message: str
    user_id: str = Field(..., alias="userId")
    created_by: str = Field(..., alias="createdBy")
    temporary_password: Optional[str] = Field(None, alias="temporaryPassword")
    success: bool = True

    model_config = ConfigDict(populate_by_name=True)


class ModulePermissionResponse(BaseModel):
    """Response model for module permissions."""

    has_access: bool = Field(..., alias="hasAccess")
    user_role: str = Field(..., alias="userRole")
    module_name: str = Field(..., alias="moduleName")
    permissions: Optional[dict] = None

    model_config = ConfigDict(populate_by_name=True)


class DepartmentAccessResponse(BaseModel):
    """Response model for department access."""

    accessible_department_ids: List[str] = Field(..., alias="accessibleDepartmentIds")
    user_role: str = Field(..., alias="userRole")
    user_department_id: Optional[str] = Field(None, alias="userDepartmentId")

    model_config = ConfigDict(populate_by_name=True)


class BranchAccessResponse(BaseModel):
    """Response model for branch access."""

    accessible_branch_ids: List[str] = Field(..., alias="accessibleBranchIds")
    user_role: str = Field(..., alias="userRole")
    user_branch_id: Optional[str] = Field(None, alias="userBranchId")

    model_config = ConfigDict(populate_by_name=True)


class ModuleInfoResponse(BaseModel):
    """Response model for module information."""

    id: UUID
    name: str
    display_name: str = Field(..., alias="displayName")
    description: Optional[str] = None
    is_core: bool = Field(..., alias="isCore")
    created_at: int = Field(..., alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)

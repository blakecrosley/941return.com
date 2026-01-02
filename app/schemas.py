"""
Pydantic schemas for Return Blog.
Simplified single-locale, single-author validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PostBase(BaseModel):
    """Base fields for post creation/update."""
    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., min_length=1, max_length=200, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    excerpt: Optional[str] = None
    content_md: str = Field(..., min_length=1)
    featured_image: Optional[str] = None
    seo_title: Optional[str] = Field(None, max_length=200)
    seo_description: Optional[str] = Field(None, max_length=500)


class PostCreate(PostBase):
    """Schema for creating a new post."""
    pass


class PostUpdate(BaseModel):
    """Schema for updating a post (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    slug: Optional[str] = Field(None, min_length=1, max_length=200, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    excerpt: Optional[str] = None
    content_md: Optional[str] = Field(None, min_length=1)
    featured_image: Optional[str] = None
    seo_title: Optional[str] = Field(None, max_length=200)
    seo_description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern=r'^(draft|published|archived)$')


class PostResponse(PostBase):
    """Schema for post responses."""
    id: int
    content_html: Optional[str] = None
    status: str
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    file_path: Optional[str] = None

    class Config:
        from_attributes = True

"""
SQLAlchemy models for Return Blog.
Simplified single-locale model (no translations, no author table).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, CheckConstraint, Index
from app.db.database import Base


class Post(Base):
    """
    Blog post with inline content (no translation table).
    Author is always Blake Crosley (hardcoded in templates).
    """
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    excerpt = Column(Text)
    content_md = Column(Text, nullable=False)
    content_html = Column(Text)
    featured_image = Column(String(500))
    seo_title = Column(String(200))
    seo_description = Column(String(500))
    status = Column(String(20), default='draft', nullable=False)
    published_at = Column(DateTime)
    scheduled_at = Column(DateTime)  # If set with status='scheduled', auto-publish at this time
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file_path = Column(String(500))  # For markdown sync
    checksum = Column(String(64))    # For sync detection

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'scheduled', 'archived')",
            name='check_post_status'
        ),
        Index('idx_posts_status', 'status'),
        Index('idx_posts_published_at', 'published_at'),
        Index('idx_posts_scheduled_at', 'scheduled_at'),
    )

    def __repr__(self):
        return f"<Post {self.slug}>"

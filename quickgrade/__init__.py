"""
QuickGrade - GitHub & Taiga Analytics Dashboard
"""

# Load Celery app on Django startup
from quickgrade.celery import app as celery_app

__all__ = ("celery_app",)

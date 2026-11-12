"""Aggregated API v1 router."""
from __future__ import annotations

from fastapi import APIRouter

from .routers import admin, ai, complaints, constitution, departments, documents, feedback, health, library

api_router = APIRouter()
for module_router in (
    health.router,
    constitution.router,
    library.router,
    ai.router,
    complaints.router,
    documents.router,
    departments.router,
    feedback.router,
    admin.router,
):
    api_router.include_router(module_router)

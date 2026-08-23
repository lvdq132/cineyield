from fastapi import APIRouter

from .agents import router as agents_router
from .analytics import router as analytics_router
from .content import router as content_router
from .deals import router as deals_router
from .demo import router as demo_router
from .ingest import router as ingest_router
from .opportunities import router as opportunities_router
from .pipeline import router as pipeline_router
from .scenes import router as scenes_router

router = APIRouter(prefix="/api/v1")
router.include_router(content_router)
router.include_router(scenes_router)
router.include_router(opportunities_router)
router.include_router(deals_router)
router.include_router(ingest_router)
router.include_router(pipeline_router)
router.include_router(analytics_router)
router.include_router(agents_router)
router.include_router(demo_router)

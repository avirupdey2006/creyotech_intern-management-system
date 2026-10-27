from fastapi import APIRouter

from app.api.v1 import admin, auth, candidates, documents, kyc, verify

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(candidates.router)
api_v1_router.include_router(kyc.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(verify.router)
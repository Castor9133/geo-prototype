"""
拓词 API
"""
import json

from fastapi import APIRouter, HTTPException, Request

from app.core.deps import DbSession, OptionalUser
from app.schemas.keyword import KeywordExpandRequest, KeywordExpandResponse, KeywordAiFocusResponse
from app.services.keyword_expansion import expand_keywords_with_status
from app.services.ai_usage import record_ai_usage, release_ai_access, resolve_ai_access
from app.services.runtime_settings import get_keyword_expansion_config

router = APIRouter()


@router.get("/ai-focus", response_model=KeywordAiFocusResponse)
async def get_keyword_ai_focus(_: OptionalUser):
    """目标 AI 平台侧重（来自后台 settings，供拓词页勾选；不含前端标题模板）。"""
    config = await get_keyword_expansion_config()
    items = [
        {
            "platform": row["platform"],
            "generation_focus": row.get("generation_focus") or "",
            "avoid": list(row.get("avoid") or []),
        }
        for row in (config.get("platforms") or [])
    ]
    return {
        "disclaimer": config.get("disclaimer") or "",
        "platforms": [row["platform"] for row in items],
        "items": items,
    }


@router.post("/expand", response_model=KeywordExpandResponse)
async def expand_keyword_pack(payload: KeywordExpandRequest, request: Request, db: DbSession, current_user: OptionalUser):
    access = None
    try:
        access = await resolve_ai_access(
            db=db,
            request=request,
            current_user=current_user,
            module="keywords",
            prompt_text="\n".join(payload.seeds or []),
        )
        result, provider_succeeded = await expand_keywords_with_status(
            payload.seeds,
            provider_override=access.provider_override,
        )
        await record_ai_usage(
            db,
            access,
            output_text=(
                json.dumps(result.get("summary", {}), ensure_ascii=False)
                if provider_succeeded
                else ""
            ),
            status_value="success" if provider_succeeded else "error",
            error_code=None if provider_succeeded else "keyword_platform_fallback",
            metadata={
                "seeds": result.get("seeds", []),
                "fallback_generated": not provider_succeeded,
                "title_hint_count": sum(
                    len(row.get("titles") or [])
                    for row in (result.get("platform_title_hints") or [])
                ),
            },
        )
        await db.commit()
        return result
    except HTTPException:
        if access and access.reservation_id:
            await db.rollback()
            await release_ai_access(db, access, error_code="keyword_request_failed")
            await db.commit()
        raise
    except ValueError as exc:
        if access and access.reservation_id:
            await db.rollback()
            await release_ai_access(db, access, error_code="keyword_validation_failed")
            await db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if access and access.reservation_id:
            await db.rollback()
            await release_ai_access(db, access, error_code="keyword_generation_failed")
            await db.commit()
        if access and access.provider_override is not None:
            raise HTTPException(
                status_code=502,
                detail="自定义 API Key 调用失败，请检查供应商、Base URL、模型和 Key。",
            ) from exc
        raise

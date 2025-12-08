import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional

from app.models.schemas import SavedPlan, SavePlanRequest, LessonPlan
from app.services.supabase import get_supabase_client, SupabaseClient

router = APIRouter()


async def get_current_user_id(
    request: Request,
    client: SupabaseClient = Depends(get_supabase_client)
) -> str:
    """Extract and verify user ID from auth cookie."""
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_response = client.auth.get_user(access_token)
        if user_response and user_response.user:
            return user_response.user.id
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("")
async def list_plans(
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """List all lesson plans for the current user."""
    try:
        response = client.table("lesson_plans").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"plans": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def save_plan(
    request: SavePlanRequest,
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """Save a lesson plan."""
    try:
        plan_id = str(uuid.uuid4())
        data = {
            "id": plan_id,
            "user_id": user_id,
            "theme": request.plan.theme,
            "duration_minutes": request.plan.total_duration_minutes,
            "plan_json": request.plan.model_dump(),
        }
        response = client.table("lesson_plans").insert(data).execute()
        return {"id": plan_id, "message": "Plan saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}")
async def get_plan(
    plan_id: str,
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """Get a specific lesson plan."""
    try:
        response = client.table("lesson_plans").select("*").eq("id", plan_id).eq("user_id", user_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Plan not found")
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{plan_id}")
async def update_plan(
    plan_id: str,
    request: SavePlanRequest,
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """Update an existing lesson plan."""
    try:
        data = {
            "theme": request.plan.theme,
            "duration_minutes": request.plan.total_duration_minutes,
            "plan_json": request.plan.model_dump(),
        }
        response = client.table("lesson_plans").update(data).eq("id", plan_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"id": plan_id, "message": "Plan updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: str,
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """Delete a lesson plan."""
    try:
        response = client.table("lesson_plans").delete().eq("id", plan_id).eq("user_id", user_id).execute()
        return {"message": "Plan deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

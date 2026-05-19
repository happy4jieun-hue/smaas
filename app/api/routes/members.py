"""
app/api/routes/members.py — /api/members CRUD 엔드포인트
"""

from typing import List

from fastapi import APIRouter, HTTPException, Response

from app.models.member import MemberInput, MemberRecord, MemberUpdate
from app.services.member_service import MemberService

router = APIRouter()


@router.get("", response_model=List[MemberRecord])
async def list_members():
    return await MemberService().get_all()


@router.post("", status_code=201, response_model=MemberRecord)
async def create_member(body: MemberInput):
    try:
        return await MemberService().create(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{member_id}", response_model=MemberRecord)
async def update_member(member_id: str, body: MemberUpdate):
    try:
        return await MemberService().update(member_id, body)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{member_id}", status_code=204)
async def delete_member(member_id: str):
    try:
        await MemberService().delete(member_id)
        return Response(status_code=204)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

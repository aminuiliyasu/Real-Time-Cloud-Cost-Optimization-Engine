from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resource import Resource
from app.schemas.resource import ResourceCreate, ResourceOut

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("", response_model=ResourceOut)
def create_resource(payload: ResourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Resource).filter(Resource.resource_id == payload.resource_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="resource_id already exists")

    resource = Resource(**payload.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("", response_model=list[ResourceOut])
def list_resources(db: Session = Depends(get_db)):
    return db.query(Resource).order_by(Resource.id.desc()).all()
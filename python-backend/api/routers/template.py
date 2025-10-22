"""
Template API Router - Template management
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from datetime import datetime
import numpy as np
import cv2

from api.models import (
    TemplateInfo,
    TemplateUploadResponse,
    TemplateLearnRequest,
    Size
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_managers(request: Request):
    """Get managers from app state"""
    return {
        'image_manager': request.app.state.image_manager(),
        'template_manager': request.app.state.template_manager(),
        'config': request.app.state.config
    }


@router.get("/list")
async def list_templates(managers=Depends(get_managers)) -> List[TemplateInfo]:
    """List all templates"""
    try:
        template_manager = managers['template_manager']
        templates = template_manager.list_templates()

        return [
            TemplateInfo(
                id=t['id'],
                name=t['name'],
                description=t.get('description'),
                size=Size(width=t['size']['width'], height=t['size']['height']),
                created_at=datetime.fromisoformat(t['created_at'])
            )
            for t in templates
        ]

    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    managers=Depends(get_managers)
) -> TemplateUploadResponse:
    """Upload new template"""
    try:
        template_manager = managers['template_manager']

        # Read and decode image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Upload template
        template_id = template_manager.upload_template(name, image, description)

        return TemplateUploadResponse(
            success=True,
            template_id=template_id,
            name=name,
            size=Size(width=image.shape[1], height=image.shape[0])
        )

    except Exception as e:
        logger.error(f"Failed to upload template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learn")
async def learn_template(
    request: TemplateLearnRequest,
    managers=Depends(get_managers)
) -> dict:
    """Learn template from image region"""
    try:
        template_manager = managers['template_manager']
        image_manager = managers['image_manager']

        # Get source image
        source_image = image_manager.get(request.image_id)
        if source_image is None:
            raise HTTPException(status_code=404, detail="Image not found")

        # Learn template from ROI
        roi_dict = {
            'x': request.roi.x,
            'y': request.roi.y,
            'width': request.roi.width,
            'height': request.roi.height
        }

        template_id = template_manager.learn_template(
            name=request.name,
            source_image=source_image,
            roi=roi_dict,
            description=request.description
        )

        # Get thumbnail
        thumbnail_base64 = template_manager.create_template_thumbnail(template_id)

        return {
            "success": True,
            "template_id": template_id,
            "thumbnail_base64": thumbnail_base64
        }

    except Exception as e:
        logger.error(f"Failed to learn template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}/image")
async def get_template_image(
    template_id: str,
    managers=Depends(get_managers)
) -> dict:
    """Get template image"""
    try:
        template_manager = managers['template_manager']

        thumbnail = template_manager.create_template_thumbnail(template_id, max_width=200)
        if thumbnail is None:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "success": True,
            "template_id": template_id,
            "image_base64": thumbnail
        }

    except Exception as e:
        logger.error(f"Failed to get template image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    managers=Depends(get_managers)
) -> dict:
    """Delete template"""
    try:
        template_manager = managers['template_manager']

        success = template_manager.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "success": True,
            "message": f"Template {template_id} deleted"
        }

    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
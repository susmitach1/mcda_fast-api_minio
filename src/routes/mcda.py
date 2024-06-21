from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from src.auth.jwthandler import get_current_user
import src.crud.mcda as mcda
from typing import List

router = APIRouter()


@router.post(
    "/api/mcda/upload", tags=["MCDA"], dependencies=[Depends(get_current_user)]
)
async def upload_file(
    dang_shapefile: UploadFile = File(...),
    river_shapefile: UploadFile = File(...),
    road_shapefile: UploadFile = File(...),
    settlement_shapefile: UploadFile = File(...),
    rasterfile: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Endpoint to upload shapefiles and a raster file, perform buffer analysis, rasterization, masking, and upload to Minio.

    Parameters:
    - dang_shapefile: Shapefile of the area of interest.
    - river_shapefile: Shapefile of rivers.
    - road_shapefile: Shapefile of roads.
    - settlement_shapefile: Shapefile of settlements.
    - rasterfile: example raster file for reference to perform rasterization.
    """
    # Save uploaded files to temporary directory
    temp_Dangsh_path = Path("/tmp") / dang_shapefile.filename
    with temp_Dangsh_path.open("wb") as boundary:
        boundary.write(await dang_shapefile.read())

    temp_riversh_path = Path("/tmp") / river_shapefile.filename
    with temp_riversh_path.open("wb") as buffer:
        buffer.write(await river_shapefile.read())

    temp_roadsh_path = Path("/tmp") / road_shapefile.filename
    with temp_roadsh_path.open("wb") as buffer:
        buffer.write(await road_shapefile.read())

    temp_settlementsh_path = Path("/tmp") / settlement_shapefile.filename
    with temp_settlementsh_path.open("wb") as buffer:
        buffer.write(await settlement_shapefile.read())

    temp_rasterfile_path = Path("/tmp") / rasterfile.filename
    with temp_rasterfile_path.open("wb") as buffer:
        buffer.write(await rasterfile.read())

    # Perform buffer analysis on the shapefiles
    try:
        buffered_river = await mcda.perform_buffer_analysis(temp_riversh_path)
        buffered_road = await mcda.perform_buffer_analysis(temp_roadsh_path)
        buffered_settlement = await mcda.perform_buffer_analysis(temp_settlementsh_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Buffer analysis failed: {str(e)}")

    # Rasterize the buffered shapefiles
    try:
        rasterized_river = await mcda.rasterize_vector(
            buffered_river, temp_rasterfile_path
        )
        rasterized_road = await mcda.rasterize_vector(
            buffered_road, temp_rasterfile_path
        )
        rasterized_settlement = await mcda.rasterize_vector(
            buffered_settlement, temp_rasterfile_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rasterization failed: {str(e)}")

    # Mask the rasterized files with the area of interest shapefile
    try:
        masked_river = await mcda.mask_raster(rasterized_river, temp_Dangsh_path)
        masked_road = await mcda.mask_raster(rasterized_road, temp_Dangsh_path)
        masked_settlement = await mcda.mask_raster(
            rasterized_settlement, temp_Dangsh_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Masking failed: {str(e)}")

    # Upload the masked files to Minio and generate presigned URLs
    try:
        river_response = await mcda.upload_to_minio([masked_river])
        road_response = await mcda.upload_to_minio([masked_road])
        settlement_response = await mcda.upload_to_minio([masked_settlement])
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"File upload to Minio failed: {str(e)}"
        )

    return JSONResponse(
        content={
            "river_response": river_response,
            "road_response": road_response,
            "settlement_response": settlement_response,
        }
    )


@router.post(
    "/api/mcda/weighted_overlay",
    tags=["MCDA"],
    dependencies=[Depends(get_current_user)],
)
async def weighted_overlay(
    river_weight: float,
    road_weight: float,
    settlement_weight: float,
    current_user=Depends(get_current_user),
):
    """
    Endpoint to perform weighted overlay analysis on masked raster files and upload the result to Minio.

    Parameters:
    - river_weight: Weight for the river raster.
    - road_weight: Weight for the road raster.
    - settlement_weight: Weight for the settlement raster.
    """
    try:
        river_url = mcda.get_presigned_url(
            "mcda/river_dang_buffered_rasterized_masked.tif"
        )
        road_url = mcda.get_presigned_url(
            "mcda/road_dang_buffered_rasterized_masked.tif"
        )
        settlement_url = mcda.get_presigned_url(
            "mcda/settlement_area_dang_buffered_rasterized_masked.tif"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate presigned URLs: {str(e)}"
        )

    raster_urls = [river_url, road_url, settlement_url]
    weights = [river_weight, road_weight, settlement_weight]

    try:
        overlay_result_path = await mcda.perform_weighted_overlay(raster_urls, weights)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Weighted overlay analysis failed: {str(e)}"
        )

    try:
        response = await mcda.upload_to_minio([overlay_result_path])
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"File upload to Minio failed: {str(e)}"
        )

    return JSONResponse(content=response)

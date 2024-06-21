import fiona
from fastapi import HTTPException
import geopandas as gpd
import io
from minio import Minio
import numpy as np
import os
from pathlib import Path
import rasterio
from rasterio import features, mask
from rasterio.enums import MergeAlg
import requests
from typing import List

"""
Initializing Minio client with environment variables

"""
client = Minio(
    os.getenv("MINIO_HOSTNAME") + ":9000",
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False,
)

bucket_name = "bucket1"
if not client.bucket_exists(bucket_name):
    client.make_bucket(bucket_name)


def get_presigned_url(key: str) -> str:
    """
    Generate a presigned URL for accessing a file stored in Minio.

    Parameters:
    key (str): The key (path) of the file in the Minio bucket.

    Returns:
    str: The presigned URL for the file.
    """
    try:
        presigned_url = client.presigned_get_object(bucket_name, key)
        return presigned_url
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate presigned URL: {str(e)}"
        )


def get_raster_from_presigned_url(url: str):
    """
    Retrieve a raster file from a presigned URL.

    Parameters:
    url (str): The presigned URL.

    Returns:
    BytesIO: The raster file content as a BytesIO object.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve raster from URL: {str(e)}"
        )


async def perform_buffer_analysis(file_path: Path) -> List[Path]:
    """
    Perform buffer analysis on a shapefile.

    Parameters:
    file_path (Path): The path to the shapefile.

    Returns:
    List[Path]: Paths to the buffered shapefile with its other essential files.
    """
    with fiona.Env(SHAPE_RESTORE_SHX="YES"):
        gdf = gpd.read_file(file_path)

        # Set CRS if not present
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)

        # Buffer the geometries
        gdf["geometry"] = gdf["geometry"].buffer(0.0038)

        # Define output file paths
        output_basename = file_path.stem + "_buffered"
        output_dir = file_path.parent
        output_files = [
            output_dir / f"{output_basename}.shp",
            output_dir / f"{output_basename}.shx",
            output_dir / f"{output_basename}.dbf",
            output_dir / f"{output_basename}.cpg",
            output_dir / f"{output_basename}.prj",
        ]

        gdf.to_file(output_dir / f"{output_basename}.shp")

    # Ensure all files are saved
    if not all(file.exists() for file in output_files):
        raise HTTPException(
            status_code=500,
            detail="Failed to save all the buffered shapefile components",
        )

    return output_files


async def rasterize_vector(file_paths: List[Path], raster_file_path: Path) -> Path:
    """
    Rasterize a vector shapefile.

    Parameters:
    file_paths (List[Path]): List of paths to shapefile with its other essential fiels.
    raster_file_path (Path): Path to the example raster file used as reference to perform rasterization.

    Returns:
    Path: Path to the rasterized output file.
    """
    vector_file_path = next(p for p in file_paths if p.suffix == ".shp")

    with fiona.Env(SHAPE_RESTORE_SHX="YES"):
        vector = gpd.read_file(vector_file_path)
        if vector.crs is None:
            vector = vector.set_crs(epsg=4326)

        geom = [shapes for shapes in vector.geometry]

        with rasterio.open(raster_file_path) as raster:
            vector["id"] = range(0, len(vector))
            geom_value = (
                (geom, value) for geom, value in zip(vector.geometry, vector["id"])
            )

            rasterized = features.rasterize(
                geom_value,
                out_shape=raster.shape,
                transform=raster.transform,
                all_touched=True,
                fill=-99999,
                merge_alg=MergeAlg.replace,
                dtype=np.float32,
            )

            output_raster_path = (
                vector_file_path.parent / f"{vector_file_path.stem}_rasterized.tif"
            )

            with rasterio.open(
                output_raster_path,
                "w",
                driver="GTiff",
                crs=raster.crs,
                transform=raster.transform,
                dtype=rasterio.uint8,
                count=1,
                width=raster.width,
                height=raster.height,
            ) as dst:
                dst.write(rasterized, indexes=1)

    return output_raster_path


async def mask_raster(raster_file_path: Path, shapefile_path: Path) -> Path:
    """
    Mask a raster file using a shapefile.

    Parameters:
    raster_file_path (Path): Path to the raster file which is to be masked.
    shapefile_path (Path): Path to the shapefile used as base to perform masking .

    Returns:
    Path: Path to the masked raster output file.
    """
    with fiona.Env(SHAPE_RESTORE_SHX="YES"):
        with fiona.open(shapefile_path) as shapefile:
            shapes = [feature["geometry"] for feature in shapefile]
        with rasterio.open(raster_file_path) as src:
            out_image, out_transform = mask.mask(src, shapes, crop=True, filled=True)
            out_meta = src.meta
            out_meta.update(
                {
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                }
            )

        output_masked_raster_path = (
            raster_file_path.parent / f"{raster_file_path.stem}_masked.tif"
        )
        with rasterio.open(output_masked_raster_path, "w", **out_meta) as dest:
            dest.write(out_image)

    return output_masked_raster_path


async def upload_to_minio(file_paths: List[Path]) -> List[dict]:
    """
    Upload files to Minio and generate presigned URLs.

    Parameters:
    file_paths (List[Path]): List of paths to the files to be uploaded.

    Returns:
    List[dict]: List of responses containing file details and presigned URLs.
    """
    responses = []

    for file_path in file_paths:
        with file_path.open("rb") as file_data:
            file_name = f"mcda/{file_path.name}"

            client.put_object(
                bucket_name,
                file_name,
                data=file_data,
                length=os.path.getsize(file_path),
                content_type="image/tiff",
            )

        presigned_url = client.presigned_get_object(bucket_name, file_name)

        responses.append(
            {
                "bucket_name": bucket_name,
                "file_path": file_name,
                "presigned_url": presigned_url,
            }
        )

    return responses


async def perform_weighted_overlay(
    raster_urls: List[str], weights: List[float]
) -> Path:
    """
    Perform weighted overlay analysis on raster files.

    Parameters:
    raster_urls (List[str]): List of presigned URLs to the raster files.
    weights (List[float]): List of weights corresponding to each raster.

    Returns:
    Path: Path to the output raster file with the weighted overlay.
    """
    # Initialize an empty list to hold the raster data
    rasters = []

    # Iterate over the list of raster URLs
    for url in raster_urls:
        # Retrieve the raster data from the presigned URL
        raster_bytes = get_raster_from_presigned_url(url)
        # Append the retrieved raster data to the rasters list
        rasters.append(raster_bytes)

    # Initialize an empty list to hold the raster arrays (pixel data)
    raster_arrays = []

    # Initialize a variable to store metadata (e.g., dimensions, CRS) for the rasters
    meta = None

    # Iterate over the list of raster data (in BytesIO format)
    for raster_bytes in rasters:
        # Open the raster data using rasterio
        with rasterio.open(raster_bytes) as src:
            # If metadata has not been set yet, set it to the metadata of the current raster
            if meta is None:
                meta = src.meta
            # Read the raster's pixel data and append it to the raster_arrays list
            raster_arrays.append(src.read(1))

    # Perform weighted overlay
    weighted_overlay = sum(
        raster * weight for raster, weight in zip(raster_arrays, weights)
    )

    output_path = Path("/tmp/result_weighted_overlay.tif")
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=weighted_overlay.shape[0],
        width=weighted_overlay.shape[1],
        count=1,
        dtype=weighted_overlay.dtype,
        crs=meta["crs"],
        transform=meta["transform"],
    ) as dst:
        dst.write(weighted_overlay, 1)

    return output_path


async def upload_to_minio(file_paths: List[Path]) -> List[dict]:
    """
    Upload files to Minio and generate presigned URLs.

    Parameters:
    file_paths (List[Path]): List of paths to the files to be uploaded.

    Returns:
    List[dict]: List of responses containing file details and presigned URLs.
    """
    responses = []

    for file_path in file_paths:
        with file_path.open("rb") as file_data:
            file_name = f"mcda/{file_path.name}"

            client.put_object(
                bucket_name,
                file_name,
                data=file_data,
                length=os.path.getsize(file_path),
                content_type="image/tiff",
            )

        presigned_url = client.presigned_get_object(bucket_name, file_name)

        responses.append(
            {
                "bucket_name": bucket_name,
                "file_path": file_name,
                "presigned_url": presigned_url,
            }
        )

    return responses

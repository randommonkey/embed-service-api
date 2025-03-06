from typing import List, Union

import boto3
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from python_hddb.client import HdDB
from loguru import logger
import json

from app.config import config

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/embed", tags=["embed"])


def get_client():
    """
    Creates and returns an HdDB client instance with authentication token from config.

    Returns:
        HdDB: Authenticated HdDB client instance
    """
    client = HdDB(motherduck_token=config.get("MOTHERDUCK_TOKEN"))
    return client


@router.get("/{orgSlug}/{slug}/{table}", response_class=HTMLResponse)
def embed(
    orgSlug: str,
    slug: str,
    table: str,
    request: Request,
    view: str = "table",
    fields: Union[List[str], None] = Query(default=None),
    preview: bool = True,
    order: str = None,
    s: Union[List[str], None] = Query(default=None),
    client=Depends(get_client),
):
    """
    Renders an HTML view of table data with optional filtering and sorting.

    Args:
        orgSlug (str): Organization identifier
        slug (str): Database identifier
        table (str): Table name
        request (Request): FastAPI request object
        view (str, optional): View type to render. Defaults to "table"
        fields (List[str], optional): List of fields to include. Defaults to None (all fields)
        preview (bool, optional): Preview mode flag. Defaults to True
        order (str, optional): Field to sort by. Defaults to None
        s (List[str], optional): Fields to filter by. Defaults to None
        client (HdDB, optional): Database client. Defaults to Depends(get_client)

    Returns:
        HTMLResponse: Rendered template with table data

    Raises:
        HTTPException: 404 if data not found, 400 if sort parameter is invalid
    """
    show_fields = fields
    try:
        response = client.get_data(org=orgSlug, db=slug, tbl=table)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=404, detail="Not found ¯\_(ツ)_/¯")

    data, fields = response["data"], response["fields"]
    field_mapping = {field["id"]: field["label"] for field in fields}

    # Crear DataFrame
    df = pd.DataFrame(data).drop("rcd___id", axis=1, errors="ignore")

    if show_fields:
        df = df[show_fields]

    if order:
        try:
            df = df.sort_values(by=order)
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=400, detail="Error in sort parameter")

    if s:
        filtered_df = df[s]
    else:
        filtered_df = df

    # Renombrar columnas usando el field_mapping
    filtered_df.rename(columns=field_mapping, inplace=True)

    image_columns = [field["label"] for field in fields if field.get("type") == "Img"]
    headers = [
        str(h).lower() for h in filtered_df.columns
    ]  # Convertir todos los headers a string y minúsculas

    # Convertir columnas a minúsculas para consistencia
    filtered_df.columns = filtered_df.columns.str.lower()

    # Convertir DataFrame a formato apropiado según la vista
    rows = (
        filtered_df.to_dict("records")
        if view == "table"
        else filtered_df.values.tolist()
    )

    capitalized = [word.title() for word in slug.split("-")]
    title = " ".join(capitalized)

    ctx = {
        "request": request,
        "title": title,
        "headers": headers,
        "rows": rows,
        "image_columns": image_columns,
    }

    return templates.TemplateResponse(
        "{}.html".format(view),
        ctx,
    )


@router.get("/{org}/{db}", response_class=HTMLResponse)
def embed_gallery(
    org: str,
    db: str,
    request: Request,
    t: Union[str, None] = None,
):
    client = get_client()

    tables = client.get_tables(org=org, db=db)
    print(tables)
    """ metadata = client.get_metadata(org=org, db=db, tbl='hoja_1')
    print(metadata) """
    
    client.close()

    tables_data = []
    for table in tables:
        new_client = get_client()
        metadata = new_client.get_metadata(org=org, db=db, tbl=table)
        client.close()
        print(metadata)
        tables_data.append((table, metadata.get("formats"), metadata.get("nrow"), metadata.get("ncol")))
    """
    Renders a gallery view of database tables and their metadata.

    Args:
        org (str): Organization identifier
        db (str): Database identifier
        request (Request): FastAPI request object
        t (str, optional): Custom title. Defaults to None

    Returns:
        HTMLResponse: Rendered gallery template

    Raises:
        HTTPException: 404 if database metadata not found
    """
    """ s3 = boto3.resource(
        "s3",
        aws_access_key_id=config.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=config.get("AWS_SECRET_ACCESS_KEY"),
    )
    key = "{}/{}/{}.base.json".format(org, db, db)
    obj = s3.Object(bucket_name="uploads.dskt.ch", key=key)

    try:
        response = obj.get()
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=404, detail="Not found ¯\_(ツ)_/¯")

    data = response["Body"].read()
    json_data = json.loads(data)

    meta = json_data.get("hdtables_meta")
    tables = []

    for k, v in meta.items():
        tables.append((k, v.get("formats"), v.get("nrow"), v.get("ncol")))
"""
    ctx = {
        "request": request,
        "title": db,
        "org": org,
        "db": db,
        "tables": tables_data,
    } 
    return templates.TemplateResponse("gallery.html", ctx)

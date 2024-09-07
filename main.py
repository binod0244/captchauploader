import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import FastAPI, HTTPException, UploadFile, status, Form
import uvicorn
import magic
from uuid import uuid4
from dotenv import load_dotenv
import os
import requests

load_dotenv()

SOLVED_URL = os.getenv("SOLVED_URL")
UNSOLVED_URL = os.getenv("UNSOLVED_URL")

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("BUCKET_NAME")
SOLVED_FOLDER_NAME = os.getenv("SOLVED_FOLDER_NAME")
UNSOLVED_FOLDER_NAME = os.getenv("UNSOLVED_FOLDER_NAME")

app = FastAPI()

SUPPORTED_FILE_TYPES = {
    'image/png': 'png',
    'image/jpeg': 'jpg'
}

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

@app.get("/")
async def root():
    return {"message": "Hello World"}


async def doUpload(file: UploadFile, folder_name: str):
    contents = await file.read()
    file_type = magic.from_buffer(buffer=contents, mime=True)
    if file_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported file type: {file_type}. Supported types are {SUPPORTED_FILE_TYPES}'
        )
    file_name = f'{folder_name}/{uuid4()}.{SUPPORTED_FILE_TYPES[file_type]}'
    s3_client.put_object(Body=contents, Bucket=BUCKET_NAME, Key=file_name)
    file_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
    return file_url


@app.post("/upload")
async def upload(file: UploadFile = Form(...), solvedValue: int = Form(...)):
    try:
        file_url = await doUpload(file, SOLVED_FOLDER_NAME)
    except NoCredentialsError:
        raise HTTPException(status_code=403, detail="Error occurred while saving to S3. AWS credentials not available")
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail="Error occurred while saving to S3. "+e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred while saving to S3.File upload failed: {str(e)}")
    try:
        response = requests.post(SOLVED_URL, {
            "url": file_url,
            "solvedValue": solvedValue
        })
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.HTTPError as http_err:
        # Handle HTTP errors (like 404, 500, etc.)
        raise HTTPException(status_code=response.status_code, detail=f"HTTP error occurred while saving to database: {str(http_err)}")

    except requests.exceptions.ConnectionError as conn_err:
        # Handle connection errors
        raise HTTPException(status_code=503, detail=f"Connection error occurred while saving to database: {str(conn_err)}")

    except requests.exceptions.Timeout as timeout_err:
        # Handle request timeout
        raise HTTPException(status_code=504, detail=f"Timeout error occurred while saving to database: {str(timeout_err)}")

    except requests.exceptions.RequestException as req_err:
        # Handle any other type of request-related error
        raise HTTPException(status_code=500, detail=f"An error occurred while saving to database: {str(req_err)}")

@app.post("/unsolved/upload")
async def upload(file: UploadFile = Form(...), unsolvedValue: int = Form(...)):
    try:
        file_url = await doUpload(file, UNSOLVED_FOLDER_NAME)
    except NoCredentialsError:
        raise HTTPException(status_code=403, detail="Error occurred while saving to S3. AWS credentials not available")
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail="Error occurred while saving to S3. "+e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred while saving to S3.File upload failed: {str(e)}")
    try:
        response = requests.post(UNSOLVED_URL, {
            "url": file_url,
            "unsolvedValue": unsolvedValue
        })
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.HTTPError as http_err:
        # Handle HTTP errors (like 404, 500, etc.)
        raise HTTPException(status_code=response.status_code, detail=f"HTTP error occurred while saving to database: {str(http_err)}")

    except requests.exceptions.ConnectionError as conn_err:
        # Handle connection errors
        raise HTTPException(status_code=503, detail=f"Connection error occurred while saving to database: {str(conn_err)}")

    except requests.exceptions.Timeout as timeout_err:
        # Handle request timeout
        raise HTTPException(status_code=504, detail=f"Timeout error occurred while saving to database: {str(timeout_err)}")

    except requests.exceptions.RequestException as req_err:
        # Handle any other type of request-related error
        raise HTTPException(status_code=500, detail=f"An error occurred while saving to database: {str(req_err)}")



if __name__ == '__main__':
    uvicorn.run(app='main:app', reload=True)

""" entry point to BA API to handle requests to openapi as well as pre-rendering """
from openai import OpenAI
from fastapi import FastAPI, Depends, Request, HTTPException
from pydantic import BaseModel
import requests
import subprocess
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import auth, credentials

if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

from secretsmanager import get_secret
from bucket import s3_client
from logger import logger

origins = [
    "http://localhost:4200",
    ]

OPENAPI_KEY_SECRET_ID = "OPENAI_API_KEY"

REGION = "eu-central-1"
BUCKET_NAME = "page-builder"

# Create OpenAPI client
openapi_client = OpenAI(api_key=get_secret(OPENAPI_KEY_SECRET_ID))

# Create an instance of the FastAPI application
app = FastAPI(title="Content-Generator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow requests from specified origins
    allow_credentials=True,  # Allow cookies to be included in cross-origin requests
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

class InputData(BaseModel):
    """
    Define the schema for the expected input using Pydantic
    """
    instructions: str
    input: str


async def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer"):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split("Bearer ")[1]
    try: 
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    

# Define a POST endpoint that accepts the JSON object
@app.post("/generate-content", tags=["Data Submission"])
def submit_data(data: InputData, user=Depends(verify_token)):
    response = client.responses.create(
        model="gpt-5",
        instructions=data.instructions,
        input=data.input,
    )
    return response.output_text


@app.post("/publish-website/{uid}")
def publish_website(uid: str, user=Depends(verify_token)) -> str:
    """
    Publish users website to HA's self-hosted S3 bucket
    """
    def get_website_url(uid: str) -> str:
        """ generate the website url given an uid """
        return f"https://s3.z1storage.com/page-builder/{uid}.html"

    logger.info("Publishing website for uid %s", uid)
    ssr_project_dir = "/ssr"
    build_command = f"PRERENDER_UID={uid} npx ng build"
    try:
        logger.info("Starting static site generation.")
        result = subprocess.run(
            build_command,
            cwd=ssr_project_dir,  # working directory
            check=True,
            shell=True,           # needed to run env var inline
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info("Build output: %s", result.stdout.decode())
    except subprocess.CalledProcessError as e:
        logger.error("Build failed: %s", e.stderr.decode())
        return

    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET_NAME, "Key": uid+".html", "ContentType": "text/html"},
        ExpiresIn=60
    )

    file_path = f"../ssr/dist/template-system/browser/builder/{uid}/index.html"
    with open(file_path, "rb") as f:
        content = f.read()
    logger.info("Uploading html file for uid %s to bucket %s", uid, BUCKET_NAME)
    response = requests.put(
        url=presigned_url,
        data=content,
        headers={"Content-Type": "text/html"},
        timeout=(5, 30))

    if response.status_code != 200:
        logger.error("Loading website to bucket failed, error message: %s", response.text)
        return

    s3_client.put_object_acl(
        Bucket='page-builder',
        Key=uid+".html",
        ACL='public-read'
    )

    website_url = get_website_url(uid)
    logger.info("Loading website to bucket succeeded, URL: %s", website_url)

    return website_url

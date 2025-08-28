""" entry point to BA API to handle requests to openapi as well as pre-rendering """
from openai import OpenAI
from pydantic import BaseModel
import requests
import subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import boto3
from google.cloud import secretmanager

from logger import logger

origins = [
    "http://localhost:4200",
    ]

PROJECT_ID = "378193426299"
OPENAPI_KEY_SECRET_ID = "OPENAI_API_KEY"
S3_URL_SECRET_ID = "S3_URL"
S3_ACCESS_KEY_SECRET_ID = "S3_ACCESS_KEY"
S3_SECRET_KEY_SECRET_ID = "S3_SECRET_KEY"
SECRET_VERSION = "latest"
REGION = "eu-central-1"
BUCKET_NAME = "page-builder"

# Create GCP Secrets Manager client
secrets_manager_client = secretmanager.SecretManagerServiceClient()

def get_secret(secrets_id: str) -> str:
    """
    Holt das Secret aus GCP Secret Manager.
    """
    name = f"projects/{PROJECT_ID}/secrets/{secrets_id}/versions/{SECRET_VERSION}"
    logger.info("Getting %s from Secrets Manager", secrets_id)
    response = secrets_manager_client.access_secret_version(request={"name": name})
    secret_value = response.payload.data.decode("UTF-8")
    return secret_value

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
    input: str

@app.post("/generate-content", tags=["Data Submission"])
def submit_data(data: InputData):
    """
    Define a POST endpoint that accepts the JSON object
    """
    response = openapi_client.responses.create(
        model="gpt-5",
        instructions='Use the input as a description for a website with one hero section and one feature section containing three features. Generate a title and a subtitle for the hero section and a title for the feature section. Also, generate titles and descriptions for each of the three features. Return the response in the following JSON format where null should be replaced by your generated content: "{\"hero\":{\"title\":null,\"subtitle\":null},\"features\":{\"title\":null,\"feature1\":{\"title\":null,\"description\":null},\"feature2\":{\"title\":null,\"description\":null},\"feature3\":{\"title\":null,\"description\":null}}}"',
        input=data.input,
    )
    return response.output_text

@app.post("/publish-website/{uid}")
def publish_website(uid: str):
    """
    Publish users website to HA's self-hosted S3 bucket
    """
    def get_website_url(uid: str):
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

    # Creating S3 boto client
    s3_client = boto3.client(
        's3',
        endpoint_url=get_secret(S3_URL_SECRET_ID),
        aws_access_key_id=get_secret(S3_ACCESS_KEY_SECRET_ID),
        aws_secret_access_key=get_secret(S3_SECRET_KEY_SECRET_ID),
        region_name='default',)

    url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET_NAME, "Key": uid+".html", "ContentType": "text/html"},
        ExpiresIn=60
    )

    file_path = f"../ssr/dist/template-system/browser/builder/{uid}/index.html"
    with open(file_path, "rb") as f:
        content = f.read()
    logger.info("Uploading html file for uid %s to bucket %s", uid, BUCKET_NAME)
    response = requests.put(
        url,
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

    url = get_website_url(uid)
    logger.info("Loading website to bucket succeeded, URL: %s", url)

    return url

""" module for the bucket client """
import boto3
from secretsmanager import get_secret

S3_URL_SECRET_ID = "S3_URL"
S3_ACCESS_KEY_SECRET_ID = "S3_ACCESS_KEY"
S3_SECRET_KEY_SECRET_ID = "S3_SECRET_KEY"

# Creating S3 boto client
s3_client = boto3.client(
    's3',
    endpoint_url=get_secret(S3_URL_SECRET_ID),
    aws_access_key_id=get_secret(S3_ACCESS_KEY_SECRET_ID),
    aws_secret_access_key=get_secret(S3_SECRET_KEY_SECRET_ID),
    region_name='default',)

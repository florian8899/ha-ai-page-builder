""" module for GCP's secrets manager """
from google.cloud import secretmanager
from logger import logger

PROJECT_ID = "378193426299"
SECRET_VERSION = "latest"

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

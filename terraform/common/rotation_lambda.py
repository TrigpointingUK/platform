import json
import logging
import os
import string

import boto3
import pymysql
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Lambda function to rotate RDS admin password
    """
    secret_arn = os.environ["SECRET_ARN"]

    # Create AWS clients
    secrets_client = boto3.client("secretsmanager")

    try:
        # Get current secret
        current_secret = secrets_client.get_secret_value(SecretId=secret_arn)
        current_credentials = json.loads(current_secret["SecretString"])

        # Generate a new password
        try:
            response = secrets_client.get_random_password(
                ExcludeCharacters='@/"\\', ExcludePunctuation=True
            )
            new_password = response["RandomPassword"]
        except ClientError as e:
            logger.error(f"Error generating random password: {e}")
            raise e

        # Get RDS endpoint from the secret ARN context or hardcode for now
        # In a real implementation, you'd get this from the secret or environment
        rds_endpoint = "your-rds-endpoint"  # This should be dynamically retrieved

        # Test new password by creating a temporary connection
        test_connection(rds_endpoint, current_credentials["username"], new_password)

        # Update the secret with new password
        secrets_client.put_secret_value(
            SecretId=secret_arn,
            SecretString=json.dumps(
                {"username": current_credentials["username"], "password": new_password}
            ),
        )

        # Set the new version as current
        secrets_client.update_secret_version_stage(
            SecretId=secret_arn,
            VersionStage="AWSCURRENT",
            MoveToVersionId=current_secret["VersionId"],
        )

        logger.info(
            f"Successfully rotated password for {current_credentials['username']}"
        )
        return {
            "statusCode": 200,
            "body": json.dumps("Password rotation completed successfully"),
        }

    except Exception as e:
        logger.error(f"Error rotating password: {str(e)}")
        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}


def generate_password():
    """Generate a secure random password"""
    import secrets  # Use secrets module for cryptographic randomness

    length = 32
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(characters) for _ in range(length))


def test_connection(host, username, password):
    """Test database connection with new credentials"""
    try:
        connection = pymysql.connect(
            host=host,
            user=username,
            password=password,
            database="mysql",
            ssl_disabled=False,
        )
        connection.close()
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        raise e

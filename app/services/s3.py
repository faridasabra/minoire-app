import boto3
import uuid
from app.config import settings

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
    endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
)

def upload_image(file_bytes: bytes, content_type: str, folder: str = "raw") -> str:
    key = f"{folder}/{uuid.uuid4()}.jpg"
    s3_client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{settings.S3_BUCKET_NAME}/{key}"

def delete_image(image_url: str) -> None:
    key = "/".join(image_url.split("/")[-2:])
    s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
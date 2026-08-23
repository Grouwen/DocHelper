import json

from minio import Minio

from app.config.minio_config import minio_config


def init_minio_client() -> Minio:
    minio_client = Minio(
        endpoint=minio_config.endpoint,
        access_key=minio_config.access_key,
        secret_key=minio_config.secret_key,
        secure=minio_config.secure,
    )

    _ensure_bucket(minio_client, minio_config.bucket_name)

    return minio_client


def _ensure_bucket(minio_client: Minio, bucket_name: str):
    if not minio_client.bucket_exists(bucket_name):
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AnonymousReadOnly",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}/*"
                    ]
                },
                {
                    "Sid": "AppFullAccess",
                    "Effect": "Allow",
                    "Principal": {
                        f"AWS": f"arn:aws:iam:::user/{minio_config.access_key}"
                    },
                    "Action": [
                        "s3:*"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}/*"
                    ]
                }
            ]
        }
        minio_client.make_bucket(bucket_name)
        minio_client.set_bucket_policy(bucket_name, json.dumps(bucket_policy))

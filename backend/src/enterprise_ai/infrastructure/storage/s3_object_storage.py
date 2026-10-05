"""S3-compatible object storage adapter."""

from collections.abc import AsyncIterator
from pathlib import Path
from tempfile import NamedTemporaryFile

import aioboto3

from enterprise_ai.domain.repositories.object_storage import ObjectStorage


class S3ObjectStorage(ObjectStorage):
    """Store document bytes in Amazon S3 or an S3-compatible service."""

    def __init__(
        self,
        bucket: str,
        *,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )
        self._endpoint_url = endpoint_url

    async def put(self, key: str, content: AsyncIterator[bytes], *, content_type: str) -> int:
        total_size = 0
        with NamedTemporaryFile(prefix="enterprise-ai-", suffix=".upload", delete=False) as handle:
            temp_path = Path(handle.name)
            async for chunk in content:
                total_size += len(chunk)
                handle.write(chunk)
        try:
            async with self._session.client("s3", endpoint_url=self._endpoint_url) as client:
                with temp_path.open("rb") as handle:
                    await client.upload_fileobj(
                        handle,
                        self._bucket,
                        key,
                        ExtraArgs={
                            "ContentType": content_type,
                            "ServerSideEncryption": "AES256",
                        },
                    )
        finally:
            temp_path.unlink(missing_ok=True)
        return total_size

    async def open(self, key: str) -> AsyncIterator[bytes]:
        async with self._session.client("s3", endpoint_url=self._endpoint_url) as client:
            response = await client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            try:
                while chunk := await body.read(1024 * 1024):
                    yield chunk
            finally:
                body.close()

    async def delete(self, key: str) -> None:
        async with self._session.client("s3", endpoint_url=self._endpoint_url) as client:
            await client.delete_object(Bucket=self._bucket, Key=key)
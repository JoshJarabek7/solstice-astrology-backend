from datetime import UTC, datetime, timedelta

from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from app.shared.settings import settings_model

account_name = str(settings_model.azure.storage.name)
account_key = str(settings_model.azure.storage.account_key)

async def create_sas(container_name: str, blob_name: str, expiry: datetime = datetime.now(UTC) + timedelta(hours=4), read: bool = True, write: bool = False) -> str:
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=read, write=write),
        expiry=expiry,
    )
    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
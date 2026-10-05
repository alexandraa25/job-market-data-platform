"""Upload a run's raw artifact to a private Azure Data Lake container."""

import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def upload_raw(path, run_id):
    enabled = os.getenv("AZURE_UPLOAD_ENABLED", "false").lower()
    if enabled not in ("true", "false"):
        raise ValueError("AZURE_UPLOAD_ENABLED must be true or false")
    if enabled == "false":
        return {}
    names = (
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_CONTAINER",
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
    )
    config = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in config.items() if not value]
    if missing:
        raise ValueError("Missing Azure configuration: " + ", ".join(missing))
    from azure.identity import ClientSecretCredential
    from azure.storage.filedatalake import DataLakeServiceClient

    # Never interpolate raw run IDs into remote paths; retries replace one artifact.
    remote_path = "jobs/" + hashlib.sha256(run_id.encode()).hexdigest() + "/raw.json"
    payload = Path(path).read_bytes()
    logging.getLogger("azure").setLevel(logging.WARNING)
    try:
        with ClientSecretCredential(
            config["AZURE_TENANT_ID"],
            config["AZURE_CLIENT_ID"],
            config["AZURE_CLIENT_SECRET"],
        ) as credential:
            with DataLakeServiceClient(
                account_url=f"https://{config['AZURE_STORAGE_ACCOUNT_NAME']}.dfs.core.windows.net",
                credential=credential,
                retry_total=2,
                connection_timeout=15,
                read_timeout=60,
            ) as service:
                file = service.get_file_client(
                    config["AZURE_STORAGE_CONTAINER"], remote_path
                )
                file.upload_data(
                    payload,
                    overwrite=True,
                    metadata={"sha256": hashlib.sha256(payload).hexdigest()},
                )
                props = file.get_file_properties()
                if props.size != len(payload):
                    raise ValueError("Uploaded size mismatch")
    except Exception as error:
        # SDK exception text may contain request details: report only type/status.
        raise RuntimeError(
            f"Azure raw upload failed ({type(error).__name__}, status={getattr(error, 'status_code', None)})"
        ) from None
    logger.info(
        "Azure raw uploaded | container=%s | path=%s | bytes=%s",
        config["AZURE_STORAGE_CONTAINER"],
        remote_path,
        len(payload),
    )
    return {
        "azure_raw_path": remote_path,
        "azure_raw_bytes": len(payload),
        "azure_raw_sha256": hashlib.sha256(payload).hexdigest(),
    }

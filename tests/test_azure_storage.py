import hashlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from src.azure_storage import upload_raw


def test_disabled_upload_needs_no_credentials(monkeypatch):
    monkeypatch.setenv("AZURE_UPLOAD_ENABLED", "false")
    assert upload_raw("missing.json", "run") == {}


def test_enabled_requires_configuration(monkeypatch):
    monkeypatch.setenv("AZURE_UPLOAD_ENABLED", "true")
    for key in (
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_CONTAINER",
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="Missing Azure configuration"):
        upload_raw("missing", "run")


def test_upload_path_retry_and_safe_error(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_UPLOAD_ENABLED", "true")
    for key in (
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_CONTAINER",
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
    ):
        monkeypatch.setenv(key, "test-secret-value")
    credential = MagicMock()
    service_factory = MagicMock()
    service = service_factory.return_value.__enter__.return_value
    file = service.get_file_client.return_value
    file.get_file_properties.return_value.size = 2
    monkeypatch.setitem(
        sys.modules,
        "azure.identity",
        SimpleNamespace(ClientSecretCredential=credential),
    )
    monkeypatch.setitem(
        sys.modules,
        "azure.storage.filedatalake",
        SimpleNamespace(DataLakeServiceClient=service_factory),
    )
    raw = tmp_path / "raw.json"
    raw.write_bytes(b"{}")
    first = upload_raw(raw, "../untrusted:run")
    second = upload_raw(raw, "../untrusted:run")
    assert first == second
    assert (
        first["azure_raw_path"]
        == "jobs/" + hashlib.sha256(b"../untrusted:run").hexdigest() + "/raw.json"
    )
    assert file.upload_data.call_args.kwargs["overwrite"] is True
    file.upload_data.side_effect = Exception("test-secret-value")
    with pytest.raises(RuntimeError) as error:
        upload_raw(raw, "run")
    assert "test-secret-value" not in str(error.value)


def test_extract_keeps_audit_metrics_compatible(monkeypatch, tmp_path):
    import json
    from src import stages

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(stages, "extract_jobs", lambda **kwargs: {"jobs": []})
    monkeypatch.setattr(stages, "save_raw_data", lambda data: None)
    monkeypatch.setattr(
        stages, "upload_raw", lambda path, run: {"azure_raw_path": "jobs/test/raw.json"}
    )
    assert stages.run_stage("extract", "azure-audit-test") == {"extracted": 0}
    manifest = stages.run_directory("azure-audit-test") / "azure_upload.json"
    assert json.loads(manifest.read_text())["azure_raw_path"] == "jobs/test/raw.json"

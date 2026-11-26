from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "infra" / "compose.yaml"


def load_yaml(path: Path) -> dict:
    class ComposeLoader(yaml.SafeLoader):
        pass

    ComposeLoader.add_constructor(
        "!override", lambda loader, node: loader.construct_sequence(node, deep=True)
    )
    ComposeLoader.add_constructor(
        "!reset", lambda loader, node: loader.construct_sequence(node, deep=True)
    )
    return yaml.load(path.read_text(encoding="utf-8"), Loader=ComposeLoader)


def test_base_topology_is_ephemeral_and_persistent() -> None:
    model = load_yaml(BASE)
    services = model["services"]
    assert {"postgres", "minio", "hive-metastore", "spark-history", "airflow-scheduler", "trino"} <= services.keys()
    assert "spark-master" not in services
    assert "spark-worker" not in services
    assert services["airflow-scheduler"]["environment"]["AIRFLOW__CORE__EXECUTOR"] == "LocalExecutor"
    assert {"postgres-data", "minio-data", "spark-events"} <= model["volumes"].keys()


def test_only_scheduler_gets_docker_socket() -> None:
    services = load_yaml(BASE)["services"]
    owners = []
    for name, service in services.items():
        if any("/var/run/docker.sock" in str(volume) for volume in service.get("volumes", [])):
            owners.append(name)
    assert owners == ["airflow-scheduler"]


def test_images_are_version_pinned() -> None:
    env = dict(
        line.split("=", 1)
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    for compose_path in (ROOT / "infra").glob("compose*.yaml"):
        for service in load_yaml(compose_path).get("services", {}).values():
            image = service.get("image")
            if image:
                match = re.fullmatch(r"\$\{([A-Z0-9_]+)\}", image)
                if match:
                    image = env[match.group(1)]
                assert ":latest" not in image
                assert ":" in image


def test_trino_and_minio_are_read_only_by_default() -> None:
    catalog = (ROOT / "infra/trino/catalog/lakehouse.properties").read_text(encoding="utf-8")
    assert "delta.security=READ_ONLY" in catalog
    assert "delta.register-table-procedure.enabled=false" in catalog
    policy = json.loads((ROOT / "infra/minio/policies/trino-reader.json").read_text(encoding="utf-8"))
    actions = {action for statement in policy["Statement"] for action in statement["Action"]}
    assert "s3:GetObject" in actions
    assert not {"s3:PutObject", "s3:DeleteObject"} & actions


def test_security_overlay_enables_system_ranger_and_tls() -> None:
    security = load_yaml(ROOT / "infra/compose.security.yaml")["services"]["trino"]
    mounts = "\n".join(str(value) for value in security["volumes"])
    assert "lakehouse-security.properties" in mounts
    assert "access-control.properties" in mounts
    config = (ROOT / "infra/trino/config/security/config.properties").read_text(encoding="utf-8")
    assert "http-server.https.enabled=true" in config
    assert "http-server.http.port=8080" in config
    assert security["ports"] == ["${HOST_BIND:-127.0.0.1}:${TRINO_HTTPS_PORT:-8443}:8443"]
    assert "http-server.authentication.type=PASSWORD" in config
    access = (ROOT / "infra/trino/config/security/access-control.properties").read_text(encoding="utf-8")
    assert "access-control.name=ranger" in access


def test_ranger_bootstrap_has_mask_filter_and_required_policies() -> None:
    source = (ROOT / "infra/ranger/bootstrap/bootstrap_ranger.py").read_text(encoding="utf-8")
    for marker in (
        "all - queryid",
        "all - trinouser",
        "MASK_SHOW_LAST_4",
        "customer_type = 'INDIVIDUAL'",
        "external_user",
    ):
        assert marker in source


def test_docker_operator_is_bounded_and_auto_removed() -> None:
    source = (ROOT / "infra/airflow/plugins/spark_docker_operator.py").read_text(encoding="utf-8")
    assert 'auto_remove="force"' in source
    assert 'mount_tmp_dir=False' in source
    assert 'Mount(source=os.environ["SPARK_JOBS_VOLUME"]' in source
    assert 'Mount(source=os.environ["SPARK_EVENTS_VOLUME"]' in source
    assert "shell=True" not in source
    assert "SPARK_S3_SECRET_KEY" in source


def test_all_compose_variants_render() -> None:
    if not shutil.which("docker"):
        return
    variants = [
        [],
        ["-f", "infra/compose.security.yaml"],
        ["-f", "infra/compose.security.yaml", "-f", "infra/compose.audit.yaml"],
        ["-f", "infra/compose.distributed.yaml"],
        ["-f", "infra/compose.sources.yaml"],
    ]
    for extra in variants:
        result = subprocess.run(
            [
                "docker", "compose", "--env-file", ".env.example",
                "-f", "infra/compose.yaml", *extra, "config", "--quiet",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr

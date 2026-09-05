"""GCP synthetic service tables and identifier formats."""

from decimal import Decimal
from .types import ProviderProfile, ServiceSpec
from ..values import _hexid

_SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec(
        "Compute Engine",
        "Compute",
        "Virtual Machines",
        "Compute Instance",
        ("compute.googleapis.com", "instances"),
        "Compute",
        "Hours",
        "e2-standard-4 running",
        Decimal("0.134"),
        Decimal("1"),
        Decimal("1"),
        "instance-",
        "hourly",
        True,
        True,
        {
            "InstanceType": "e2-standard-4",
            "InstanceSeries": "E2",
            "CoreCount": 4,
            "MemorySize": 16,
            "OperatingSystem": "Linux",
            "x_Preemptible": "false",
        },
    ),
    ServiceSpec(
        "Cloud Storage",
        "Storage",
        "Object Storage",
        "Storage Bucket",
        ("storage.googleapis.com", "buckets"),
        "Storage",
        "GB-Months",
        "Standard storage",
        Decimal("0.020"),
        Decimal("50"),
        Decimal("8000"),
        "bucket-",
        "monthly",
        False,
        False,
        {"StorageClass": "Standard"},
    ),
    ServiceSpec(
        "Cloud SQL",
        "Databases",
        "Relational Databases",
        "Cloud SQL Instance",
        ("sqladmin.googleapis.com", "instances"),
        "Database",
        "Hours",
        "Cloud SQL custom 4 vCPU",
        Decimal("0.200"),
        Decimal("1"),
        Decimal("1"),
        "sql-",
        "hourly",
        False,
        False,
        {
            "InstanceType": "db-custom-4-16384",
            "CoreCount": 4,
            "MemorySize": 16,
            "x_Engine": "PostgreSQL",
        },
    ),
    ServiceSpec(
        "Cloud Functions",
        "Compute",
        "Serverless Compute",
        "Cloud Function",
        ("cloudfunctions.googleapis.com", "functions"),
        "Compute",
        "GB-Seconds",
        "Function execution duration",
        Decimal("0.0000025"),
        Decimal("100000"),
        Decimal("8000000"),
        "fn-",
        "hourly",
        False,
        False,
        {"x_Runtime": "python312", "x_Generation": "gen2"},
    ),
    ServiceSpec(
        "Google Kubernetes Engine",
        "Compute",
        "Containers",
        "GKE Cluster",
        ("container.googleapis.com", "clusters"),
        "Compute",
        "Hours",
        "GKE node pool hours",
        Decimal("0.134"),
        Decimal("1"),
        Decimal("1"),
        "gke-",
        "hourly",
        False,
        False,
        {
            "InstanceType": "e2-standard-4",
            "CoreCount": 4,
            "MemorySize": 16,
            "x_NodePool": "default",
        },
    ),
    ServiceSpec(
        "Cloud Monitoring",
        "Management and Governance",
        "Observability",
        "Monitoring Workspace",
        ("monitoring.googleapis.com", "metricsScopes"),
        "Monitoring",
        "MiB",
        "Monitoring data ingested",
        Decimal("0.2580"),
        Decimal("1"),
        Decimal("300"),
        "mon-",
        "daily",
        False,
        False,
        {"x_DataType": "Metrics"},
    ),
    ServiceSpec(
        "BigQuery",
        "Databases",
        "Data Warehouses",
        "BigQuery Dataset",
        ("bigquery.googleapis.com", "datasets"),
        "Analysis",
        "TiB",
        "On-demand query analysis",
        Decimal("6.250"),
        Decimal("0.01"),
        Decimal("50"),
        "ds_",
        "daily",
        False,
        False,
        {"x_Edition": "OnDemand"},
    ),
    ServiceSpec(
        "Cloud Run",
        "Compute",
        "Serverless Compute",
        "Cloud Run Service",
        ("run.googleapis.com", "services"),
        "Compute",
        "Core-Seconds",
        "Cloud Run vCPU allocation",
        Decimal("0.000024"),
        Decimal("100000"),
        Decimal("5000000"),
        "svc-",
        "hourly",
        False,
        False,
        {"x_Generation": "gen2"},
    ),
)

_REGIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("us-central1", "Iowa", ("us-central1-a", "us-central1-b", "us-central1-c")),
    ("europe-west1", "Belgium", ("europe-west1-b", "europe-west1-c")),
    ("us-east1", "South Carolina", ("us-east1-b", "us-east1-c")),
    ("asia-southeast1", "Singapore", ("asia-southeast1-a", "asia-southeast1-b")),
)

_BILLING_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("01A2B3-C4D5E6-F70819", "ExampleCorp Billing - Primary"),
    ("11C2D3-E4F506-A7B8C9", "ExampleCorp Billing - Secondary"),
)

_SUB_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("examplecorp-prod-481627", "prod-platform"),
    ("examplecorp-staging-552831", "staging-platform"),
    ("examplecorp-data-739104", "data-analytics"),
    ("examplecorp-sandbox-160942", "sandbox-dev"),
)


def resource_id(rng, spec, region, ctx, name):
    return f"//{spec.id_parts[0]}/projects/{ctx['sub_id']}/{spec.id_parts[1]}/{name}"


def invoice_id(billing_id):
    return f"INV-2026-05-{billing_id.replace('-', '')[-6:]}"


def commitment_id(rng, region, ctx, kind, spend_based):
    return f"//compute.googleapis.com/projects/{ctx['sub_id']}/regions/{region}/commitments/cud-{_hexid(rng, 10)}"


def allocation_id(rng, region, ctx, workload):
    return f"//container.googleapis.com/projects/{ctx['sub_id']}/clusters/gke-{_hexid(rng, 6)}/workloads/{workload}"


PROFILE = ProviderProfile(
    key="gcp",
    provider_name="Google Cloud",
    publisher_name="Google",
    invoice_issuer="Google Cloud",
    services=_SERVICES,
    regions=_REGIONS,
    billing_accounts=_BILLING_ACCOUNTS,
    sub_accounts=_SUB_ACCOUNTS,
    resource_id=resource_id,
    invoice_id=invoice_id,
    commitment_id=commitment_id,
    allocation_id=allocation_id,
    label="GCP",
    billing_type="Billing Account",
    sub_type="Project",
    tag_keys=("environment", "cost-center", "owner"),
    resource_width=8,
    committed_width=6,
    commitment_kinds=("cud", "cud"),
    commitment_types=("Committed Use Discount", "Committed Use Discount"),
    commitment_names=("SpendBasedCUD-1yr", "ResourceBasedCUD-1yr-Compute"),
    commitment_name_width=10,
    commitment_details='{"x_Plan":"TWELVE_MONTH","x_Type":"COMPUTE_OPTIMIZED"}',
    allocation_description="Shared Compute Engine host cost allocated to workload",
)

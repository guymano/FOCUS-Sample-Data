"""AWS synthetic service tables and identifier formats."""

from decimal import Decimal
from .types import ProviderProfile, ServiceSpec
from ..values import _hexid

_SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec(
        "AmazonEC2",
        "Compute",
        "Virtual Machines",
        "EC2 Instance",
        ("instance",),
        "Compute",
        "Hours",
        "Linux on-demand m6i.large",
        Decimal("0.096"),
        Decimal("1"),
        Decimal("1"),
        "i-",
        "hourly",
        True,
        True,
        {
            "InstanceType": "m6i.large",
            "InstanceSeries": "M6i",
            "CoreCount": 2,
            "MemorySize": 8,
            "OperatingSystem": "Linux",
            "x_Tenancy": "Shared",
        },
    ),
    ServiceSpec(
        "AmazonS3",
        "Storage",
        "Object Storage",
        "S3 Bucket",
        ("bucket",),
        "Storage",
        "GB-Months",
        "S3 Standard storage",
        Decimal("0.023"),
        Decimal("50"),
        Decimal("8000"),
        "bucket-",
        "monthly",
        False,
        False,
        {"StorageClass": "Standard", "Redundancy": "Zonal"},
    ),
    ServiceSpec(
        "AmazonRDS",
        "Databases",
        "Relational Databases",
        "RDS Instance",
        ("db",),
        "Database",
        "Hours",
        "RDS PostgreSQL db.r6g.large",
        Decimal("0.240"),
        Decimal("1"),
        Decimal("1"),
        "db-",
        "hourly",
        False,
        False,
        {
            "InstanceType": "db.r6g.large",
            "InstanceSeries": "R6g",
            "CoreCount": 2,
            "MemorySize": 16,
            "x_Engine": "PostgreSQL",
        },
    ),
    ServiceSpec(
        "AWSLambda",
        "Compute",
        "Serverless Compute",
        "Lambda Function",
        ("function",),
        "Compute",
        "GB-Seconds",
        "Lambda function duration",
        Decimal("0.0000166667"),
        Decimal("100000"),
        Decimal("5000000"),
        "fn-",
        "hourly",
        False,
        False,
        {"x_Runtime": "python3.12", "x_Architecture": "arm64"},
    ),
    ServiceSpec(
        "AmazonVPC",
        "Networking",
        "Network Connectivity",
        "NAT Gateway",
        ("natgateway",),
        "Data Transfer",
        "GB",
        "NAT gateway data processed",
        Decimal("0.045"),
        Decimal("1"),
        Decimal("500"),
        "nat-",
        "daily",
        False,
        False,
        {"x_TransferType": "InterAZ"},
    ),
    ServiceSpec(
        "AmazonCloudWatch",
        "Management and Governance",
        "Observability",
        "Metric",
        ("metric",),
        "Monitoring",
        "Metrics",
        "Custom metrics",
        Decimal("0.300"),
        Decimal("1"),
        Decimal("200"),
        "metric-",
        "daily",
        False,
        False,
        {"x_MetricType": "Custom"},
    ),
    ServiceSpec(
        "AmazonDynamoDB",
        "Databases",
        "NoSQL Databases",
        "DynamoDB Table",
        ("table",),
        "Database",
        "Requests",
        "DynamoDB on-demand write requests",
        Decimal("0.00000125"),
        Decimal("100000"),
        Decimal("5000000"),
        "table-",
        "daily",
        False,
        False,
        {"x_CapacityMode": "On-Demand"},
    ),
    ServiceSpec(
        "AWSGlue",
        "Analytics",
        "Data Processing",
        "Glue Job",
        ("job",),
        "Data Processing",
        "DPU-Hours",
        "Glue ETL job run",
        Decimal("0.440"),
        Decimal("1"),
        Decimal("200"),
        "job-",
        "daily",
        False,
        False,
        {"x_WorkerType": "G.1X"},
    ),
)

_REGIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("us-east-1", "US East (N. Virginia)", ("us-east-1a", "us-east-1b", "us-east-1c")),
    ("us-west-2", "US West (Oregon)", ("us-west-2a", "us-west-2b")),
    ("eu-west-1", "EU (Ireland)", ("eu-west-1a", "eu-west-1b")),
    (
        "ap-southeast-1",
        "Asia Pacific (Singapore)",
        ("ap-southeast-1a", "ap-southeast-1b"),
    ),
)

_BILLING_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("100000000001", "ExampleCorp Master Payer"),
    ("100000000002", "ExampleCorp Secondary Payer"),
)

_SUB_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("200000000011", "prod-platform"),
    ("200000000012", "staging-platform"),
    ("200000000013", "data-analytics"),
    ("200000000014", "sandbox-dev"),
)


def resource_id(rng, spec, region, ctx, name):
    svc = {
        "AmazonEC2": "ec2",
        "AmazonS3": "s3",
        "AmazonRDS": "rds",
        "AWSLambda": "lambda",
        "AmazonVPC": "ec2",
        "AmazonCloudWatch": "cloudwatch",
        "AmazonDynamoDB": "dynamodb",
        "AWSGlue": "glue",
    }[spec.name]
    return f"arn:aws:{svc}:{region}:{ctx['sub_id']}:{spec.id_parts[0]}/{name}"


def invoice_id(billing_id):
    return f"INV-2026-05-{billing_id[-4:]}"


def commitment_id(rng, region, ctx, kind, spend_based):
    return f"arn:aws:{'savingsplans' if spend_based else 'ec2'}:{region}::{kind}/{_hexid(rng, 16)}"


def allocation_id(rng, region, ctx, workload):
    return f"arn:aws:eks:{region}:{ctx['sub_id']}:workload/{workload}-{_hexid(rng, 6)}"


PROFILE = ProviderProfile(
    key="aws",
    provider_name="AWS",
    publisher_name="AWS",
    invoice_issuer="AWS",
    services=_SERVICES,
    regions=_REGIONS,
    billing_accounts=_BILLING_ACCOUNTS,
    sub_accounts=_SUB_ACCOUNTS,
    resource_id=resource_id,
    invoice_id=invoice_id,
    commitment_id=commitment_id,
    allocation_id=allocation_id,
    label="AWS",
    billing_type="Payer Account",
    sub_type="Linked Account",
    tag_keys=("Environment", "CostCenter", "Owner"),
    resource_width=12,
    committed_width=8,
    commitment_kinds=("savingsplan", "reservation"),
    commitment_types=("Savings Plan", "Reserved Instance"),
    commitment_names=(
        "ComputeSavingsPlan-1yr-NoUpfront",
        "EC2ReservedInstance-1yr-NoUpfront",
    ),
    commitment_name_width=12,
    commitment_details='{"x_PurchaseTerm":"1yr","x_PaymentOption":"NoUpfront"}',
    allocation_description="Shared EC2 host cost allocated to workload",
)

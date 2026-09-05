"""AZURE synthetic service tables and identifier formats."""

from decimal import Decimal
from .types import ProviderProfile, ServiceSpec
from ..values import _hexid

_SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec(
        "Virtual Machines",
        "Compute",
        "Virtual Machines",
        "Virtual Machine",
        ("Microsoft.Compute/virtualMachines",),
        "Compute",
        "Hours",
        "Standard_D4s_v5 instance",
        Decimal("0.192"),
        Decimal("1"),
        Decimal("1"),
        "vm-",
        "hourly",
        True,
        True,
        {
            "InstanceType": "Standard_D4s_v5",
            "InstanceSeries": "Ddsv5",
            "CoreCount": 4,
            "MemorySize": 16,
            "OperatingSystem": "Linux",
            "x_Tenancy": "Shared",
        },
    ),
    ServiceSpec(
        "Azure Blob Storage",
        "Storage",
        "Object Storage",
        "Storage Account",
        ("Microsoft.Storage/storageAccounts",),
        "Storage",
        "GB-Months",
        "Hot LRS data stored",
        Decimal("0.0184"),
        Decimal("50"),
        Decimal("8000"),
        "stor",
        "monthly",
        False,
        False,
        {"StorageClass": "Hot", "Redundancy": "Local"},
    ),
    ServiceSpec(
        "Azure SQL Database",
        "Databases",
        "Relational Databases",
        "SQL Database",
        ("Microsoft.Sql/servers/databases",),
        "Database",
        "Hours",
        "General Purpose 4 vCore",
        Decimal("0.504"),
        Decimal("1"),
        Decimal("1"),
        "sqldb-",
        "hourly",
        False,
        False,
        {
            "InstanceType": "GP_Gen5_4",
            "CoreCount": 4,
            "MemorySize": 20,
            "x_Engine": "SQLServer",
        },
    ),
    ServiceSpec(
        "Azure Functions",
        "Compute",
        "Serverless Compute",
        "Function App",
        ("Microsoft.Web/sites",),
        "Compute",
        "GB-Seconds",
        "Function execution duration",
        Decimal("0.000016"),
        Decimal("100000"),
        Decimal("4000000"),
        "func-",
        "hourly",
        False,
        False,
        {"x_Plan": "Consumption", "x_Runtime": "dotnet8"},
    ),
    ServiceSpec(
        "Azure Kubernetes Service",
        "Compute",
        "Containers",
        "Managed Cluster",
        ("Microsoft.ContainerService/managedClusters",),
        "Compute",
        "Hours",
        "AKS node pool hours",
        Decimal("0.192"),
        Decimal("1"),
        Decimal("1"),
        "aks-",
        "hourly",
        False,
        False,
        {
            "InstanceType": "Standard_D4s_v5",
            "CoreCount": 4,
            "MemorySize": 16,
            "x_NodePool": "system",
        },
    ),
    ServiceSpec(
        "Azure Monitor",
        "Management and Governance",
        "Observability",
        "Log Analytics Workspace",
        ("Microsoft.OperationalInsights/workspaces",),
        "Monitoring",
        "GB",
        "Log data ingested",
        Decimal("2.30"),
        Decimal("1"),
        Decimal("500"),
        "law-",
        "daily",
        False,
        False,
        {"x_DataType": "Logs"},
    ),
    ServiceSpec(
        "Azure Cosmos DB",
        "Databases",
        "NoSQL Databases",
        "Cosmos DB Account",
        ("Microsoft.DocumentDB/databaseAccounts",),
        "Database",
        "Hours",
        "Provisioned throughput",
        Decimal("0.008"),
        Decimal("1"),
        Decimal("1"),
        "cosmos-",
        "hourly",
        False,
        False,
        {"x_CapacityMode": "Provisioned"},
    ),
    ServiceSpec(
        "Virtual Network",
        "Networking",
        "Network Connectivity",
        "Virtual Network",
        ("Microsoft.Network/virtualNetworks",),
        "Data Transfer",
        "GB",
        "VNet peering data transfer",
        Decimal("0.010"),
        Decimal("1"),
        Decimal("5000"),
        "vnet-",
        "daily",
        False,
        False,
        {"x_TransferType": "Peering"},
    ),
)

_REGIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("eastus", "East US", ("eastus-1", "eastus-2", "eastus-3")),
    ("westeurope", "West Europe", ("westeurope-1", "westeurope-2")),
    ("westus2", "West US 2", ("westus2-1", "westus2-2")),
    ("southeastasia", "Southeast Asia", ("southeastasia-1", "southeastasia-2")),
)

_BILLING_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("8a1b2c3d-0000-4a00-9000-000000000001", "ExampleCorp MCA - Primary"),
    ("8a1b2c3d-0000-4a00-9000-000000000002", "ExampleCorp MCA - Secondary"),
)

_SUB_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("11111111-1111-4111-8111-111111111111", "prod-platform"),
    ("22222222-2222-4222-8222-222222222222", "staging-platform"),
    ("33333333-3333-4333-8333-333333333333", "data-analytics"),
    ("44444444-4444-4444-8444-444444444444", "sandbox-dev"),
)


def resource_id(rng, spec, region, ctx, name):
    return f"/subscriptions/{ctx['sub_id']}/resourceGroups/rg-{ctx['sub_name']}/providers/{spec.id_parts[0]}/{name}"


def invoice_id(billing_id):
    return f"INV-2026-05-{billing_id[-6:]}"


def commitment_id(rng, region, ctx, kind, spend_based):
    return f"/subscriptions/{ctx['sub_id']}/providers/Microsoft.BillingBenefits/{kind}/{_hexid(rng, 12)}"


def allocation_id(rng, region, ctx, workload):
    return f"/subscriptions/{ctx['sub_id']}/resourceGroups/rg-{ctx['sub_name']}/providers/Microsoft.ContainerService/managedClusters/aks-{_hexid(rng, 6)}/workloads/{workload}"


PROFILE = ProviderProfile(
    key="azure",
    provider_name="Microsoft Azure",
    publisher_name="Microsoft",
    invoice_issuer="Microsoft Azure",
    services=_SERVICES,
    regions=_REGIONS,
    billing_accounts=_BILLING_ACCOUNTS,
    sub_accounts=_SUB_ACCOUNTS,
    resource_id=resource_id,
    invoice_id=invoice_id,
    commitment_id=commitment_id,
    allocation_id=allocation_id,
    label="Azure",
    billing_type="Microsoft Customer Agreement",
    sub_type="Subscription",
    tag_keys=("Environment", "CostCenter", "Owner"),
    resource_width=8,
    committed_width=6,
    commitment_kinds=("savingsPlans", "reservations"),
    commitment_types=("Savings Plan", "Reservation"),
    commitment_names=(
        "AzureSavingsPlan-1yr-NoUpfront",
        "AzureReservation-1yr-NoUpfront",
    ),
    commitment_name_width=10,
    commitment_details='{"x_Term":"P1Y","x_PaymentOption":"NoUpfront"}',
    allocation_description="Shared VM host cost allocated to workload",
)

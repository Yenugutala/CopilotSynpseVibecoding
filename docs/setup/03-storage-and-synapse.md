# 3. Storage (ADLS Gen2) + Synapse workspace

Time: about 20 minutes. Everything goes in `rg-copilot-demo`.

## 3.1 Storage account
**Storage accounts** → **+ Create**:

| Field | Value |
|---|---|
| Name | `stcopilotdemokk1` (globally unique, lowercase) |
| Performance / Redundancy | Standard / **LRS** |
| **Advanced → Enable hierarchical namespace** | ✅ **Required**. Without it, Synapse can't use the account. |

Check **Overview → Data Lake Storage → Hierarchical namespace: Enabled**.
- If it says Disabled, delete the account and create it again with the box ticked. That's faster than the in-place upgrade, which can take hours and fails while container soft delete is on.

## 3.2 Containers
**Data storage → Containers → + Add container** (Private) for each of:

| Container | Purpose |
|---|---|
| `landing` | You upload the source CSVs here |
| `raw` | The pipeline copies files here by ingest date |
| `curated` | The pipeline writes silver Parquet here |

## 3.3 Synapse workspace
**Azure Synapse Analytics** → **+ Create**:

| Tab | Field | Value |
|---|---|---|
| Basics | Workspace name | `syn-copilot-demo-kk` |
| Basics | Region | One that accepts SQL provisioning. East US was blocked for us, so we used **Central US**. |
| Basics | Data Lake Storage Gen2 | Account `stcopilotdemokk1`, file system `raw` |
| Basics | Assign myself Storage Blob Data Contributor | ✅ |
| Security | Authentication | Local + Microsoft Entra ID. SQL admin `sqladminuser` (password in your password manager). |
| Networking | Managed virtual network | **Disable** (cost) |
| Networking | Allow connections from all IP addresses | ✅ (demo only) |

**Don't create a Dedicated SQL pool or an Apache Spark pool.** The built-in serverless pool is all we use.

Update `config/environment.yaml` (`synapse.workspace`, `synapse.serverless_endpoint`) if your names differ.

## Troubleshooting
| Error | Fix |
|---|---|
| `SqlServerRegionDoesNotAllowProvisioning` | Pick another region (Central US, West US 2, West US 3). If every region fails, open a free support request: **Service and subscription limits (quotas)** → SQL Database. |
| Storage account not listed in the Synapse form | Hierarchical namespace isn't enabled (see 3.1) |

Next: [04-synapse-git-and-permissions.md](04-synapse-git-and-permissions.md)

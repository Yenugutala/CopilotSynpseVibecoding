# 4. Synapse permissions + Git integration

These steps let the pipeline read and write storage and run SQL, and let Synapse Studio read this repo.
Do them **once per workspace**. Create the GitHub repo first: [05-github-repo.md](05-github-repo.md).

## 4.1 Storage access for the workspace managed identity
1. Open the storage account `stcopilotdemokk1` → **Access control (IAM)** → **+ Add role assignment**.
2. Role: **Storage Blob Data Contributor** → **Next**.
3. Members: **Managed identity** → **Synapse workspace** → `syn-copilot-demo-kk` → **Select** → **Review + assign**.
4. Check that **your own user** also has this role. You need it to query gold views and to upload to `landing`.

Allow 5–10 minutes for the role to take effect.

## 4.2 Serverless SQL login for the workspace identity
Pipeline Script activities connect to serverless SQL as the workspace identity.
1. Open Synapse Studio → **Develop** → **+ SQL script**.
2. Set **Connect to: Built-in** and **database: master**.
3. Run the following (use your workspace name):
```sql
CREATE LOGIN [syn-copilot-demo-kk] FROM EXTERNAL PROVIDER;
ALTER SERVER ROLE sysadmin ADD MEMBER [syn-copilot-demo-kk];
```
An "already exists" error on the first statement is fine.

`sysadmin` keeps the demo simple. For production, grant only what's needed: `dbcreator`, plus `db_owner` in `demo_lakehouse`.

## 4.3 Connect Synapse Studio to GitHub
1. Synapse Studio → **Manage** (toolbox icon) → **Source control → Git configuration** → **Configure**.
2. Fill in:

| Field | Value |
|---|---|
| Repository type | **GitHub** |
| GitHub account | your GitHub user or organization. Click **Authorize** the first time; this installs the "Azure Synapse" GitHub app. |
| Repository name | the repo from step 5 |
| Collaboration branch | `main` |
| Publish branch | `workspace_publish` |
| **Root folder** | `/synapse` |
| Import existing resources to repository | **Unticked** |

3. Click **Apply**. At the top of Studio, set the working branch to **main**.
4. **Integrate → Pipelines** should now show **copilot-generated → pl_customer_orders** once the generated code is merged.

## How Git mode works
- Studio reads the artifacts from the selected branch. **Publish** (only allowed from `main`) deploys them live and writes the deployment template to `workspace_publish`.
- **Trigger now** runs the **published** version. After every merge, click **Publish** before you trigger.
- If someone edits a pipeline in Studio, the change is committed to the branch. Regenerate from SQL (`tools/build_synapse.py build`) before merging, or CI will fail.

Next: [06-run-the-pipeline.md](06-run-the-pipeline.md)

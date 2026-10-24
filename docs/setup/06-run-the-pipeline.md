# 6. Generate, run and query

## 6.1 Generate the code (VS Code)
1. Copilot Chat → **Agent** mode → your Foundry model.
2. Type `/generate-pipeline` (accept the default `customers orders` / `customer_order_summary`).
3. Review the plan → approve → review the staged files → approve. Copilot opens the PR.
4. Wait for CI to go green → review → **Merge**.

## 6.2 Upload the source files
In the portal: storage account → **Containers → landing → Upload**. Upload `data/sample/customers.csv` and `data/sample/orders.csv`, keeping the file names exactly as they are.

## 6.3 Publish and run (Synapse Studio)
1. Set the branch dropdown to **main** → click **Publish** → **OK**.
2. **Integrate → copilot-generated → pl_customer_orders** → **Add trigger → Trigger now** → **OK**.
3. **Monitor → Pipeline runs**: wait for **Succeeded** (about 2–4 minutes).
   - If it fails, click the failed activity's error icon and give the exact message to Copilot ("the pipeline failed with …").

## 6.4 Query the result
Synapse Studio → **Develop → + SQL script** → **Connect to: Built-in**, **Database: demo_lakehouse**:
```sql
SELECT * FROM gold.customer_order_summary ORDER BY total_revenue DESC;

-- what was rejected and why
SELECT customer_id, email, signup_date_raw, _dq_failures FROM silver.customers_rejects;
SELECT order_id, quantity, unit_price, status, _dq_failures FROM silver.orders_rejects;
```

The sample files contain deliberate bad rows: a bad email, a missing id, invalid dates, a negative price, zero quantity and an unknown status. You should see them in the rejects tables.

## 6.5 Load new data
Upload new files with the same names to `landing/` → **Trigger now**. Raw keeps a history by ingest date. Silver rebuilds into a new `run_id` folder, keeping the latest row per business key.

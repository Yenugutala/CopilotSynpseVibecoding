# 1. Azure foundation (subscription, budget, providers, resource group)

Time: about 10 minutes. You need **Owner** or **Contributor** on the subscription.

## 1.1 Subscription is active
Go to **portal.azure.com** → **Subscriptions** → your subscription → **Overview**. Status must be **Active**.
- If it's a Free Trial that has ended, click **Upgrade** to switch to Pay-As-You-Go.
- After upgrading, sign out and back in. It can take a few minutes before tools such as ai.azure.com see the change.

## 1.2 Budget alert
**Budgets** → **+ Add** → name `demo-budget`, Monthly, `$10`, alerts at 50% and 90% (Actual) sent to your email.

## 1.3 Register resource providers
**Subscription** → **Settings** → **Resource providers**. For each of these, select it and click **Register**:
- `Microsoft.CognitiveServices`
- `Microsoft.MachineLearningServices`
- `Microsoft.Synapse`
- `Microsoft.Storage`

Click **Refresh** until all four show **Registered**.

## 1.4 Resource group
**Resource groups** → **+ Create** → `rg-copilot-demo`.

Next: [02-azure-ai-foundry-and-copilot.md](02-azure-ai-foundry-and-copilot.md)

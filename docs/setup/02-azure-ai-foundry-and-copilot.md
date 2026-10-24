# 2. Azure AI Foundry model + GitHub Copilot in VS Code

Time: about 20 minutes.

## 2.1 Create the Foundry project
1. Go to **https://ai.azure.com** → **Create project**.
2. Expand **Advanced options** and check the **Region** and **Resource group** fields. The form fills them in automatically.
3. Leave **"Set up recommended resources"** OFF. It adds App Insights, which costs money.
4. Click **Create**.

Our environment: project `kyenugutala-9617`, resource `kyenugutala-9617-resource`, region West US 3.

## 2.2 Deploy a low-cost model
1. **Explore models** → search `gpt-4.1-mini` (or a newer `gpt-*-mini`) → open it.
2. **Custom deploy ⌄** → Deployment type **Global Standard**, Tokens per minute **20K** → **Deploy**.
3. On the **Deployments** tab, note the deployment name. Ours is `gpt-4.1-mini-1`.
4. **Open in playground** → send `hello` and check that it replies.

## 2.3 Get the connection details
On the Foundry **Home** page, copy:
- **Azure OpenAI endpoint**: `https://<resource>.openai.azure.com/…`. Do **not** use the "Project endpoint" (`services.ai.azure.com`).
- **API key**. Keep it in a password manager, never in the repo or in chat.

## 2.4 Connect Copilot
1. Open VS Code from **Applications**. If updates fail with "read-only volume", quit VS Code and run:
   ```bash
   xattr -dr com.apple.quarantine "/Applications/Visual Studio Code.app"
   ```
2. Sign in to GitHub Copilot (the Copilot icon in the status bar). Copilot Free is enough.
3. Press **Cmd+Shift+P** → **GitHub Copilot: Manage Models…**, or open the **Language Models** page → **Add Models** → **Azure**.
4. Enter:
   - URL: `https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2025-01-01-preview`
   - API key: your key
   - Model ID: `<deployment>`
   - Tool calling: **Yes**
5. In Chat, set the mode to **Agent**, open the model picker → **Azure** tab → select your deployment.

## 2.5 Verify that it's really Foundry
- In Foundry → your deployment → **Monitor**, requests should appear within about 5 minutes of chatting.
- Or run **Developer: Show Chat Debug View** in VS Code. The request URL should contain `openai.azure.com`.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Subscription is disabled" when creating the project | Upgrade the subscription (step 1.1) |
| "Language model unavailable" | Copilot premium requests are used up. Select your Azure model. |
| Only Copilot or OpenRouter models in the picker | Add the Azure model (2.4). OpenRouter is billed separately. |
| "Unrecognized Azure deployment URL" | You used the `services.ai.azure.com` endpoint. Use `openai.azure.com`. |
| "Model only supports 128 tools" warning | Harmless. Click **Configure Tools** and untick tool groups you don't need. |
| 401 / 404 | Wrong key, resource name or deployment name in the URL |

Next: [03-storage-and-synapse.md](03-storage-and-synapse.md)

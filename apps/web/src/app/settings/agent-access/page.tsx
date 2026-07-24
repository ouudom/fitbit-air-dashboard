import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

type Capabilities = {
  agentAccessEnabled: boolean;
};

export default async function AgentAccessPage() {
  const apiOrigin = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
  let agentAccessEnabled = false;

  try {
    const response = await fetch(`${apiOrigin}/api/v1/capabilities`, {
      cache: "no-store",
    });
    if (response.ok) {
      const capabilities = (await response.json()) as Capabilities;
      agentAccessEnabled = capabilities.agentAccessEnabled;
    }
  } catch {
    // Fail closed when backend capabilities are unavailable.
  }

  redirect(agentAccessEnabled ? "/settings#agent-access" : "/settings");
}

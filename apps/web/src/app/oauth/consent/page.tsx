import { Suspense } from "react";
import { OAuthConsent } from "@/modules/agent-access/OAuthConsent";

export default function OAuthConsentPage() {
  return (
    <Suspense
      fallback={
        <main className="center">
          <div className="loader" role="status">
            Loading authorization…
          </div>
        </main>
      }
    >
      <OAuthConsent />
    </Suspense>
  );
}

import type { components } from "./openapi";

export type Session = components["schemas"]["SessionResponse"];
export type Dashboard = components["schemas"]["DashboardResponse"];
export type AgentScope = components["schemas"]["AgentScope"];
export type AgentOAuthGrant = components["schemas"]["AgentOAuthGrantResponse"];
export type OAuthAuthorizationPreview =
  components["schemas"]["OAuthAuthorizationPreviewResponse"];
export type OAuthAuthorizationDecision =
  components["schemas"]["OAuthAuthorizationDecisionRequest"];
export type OAuthAuthorizationResult =
  components["schemas"]["OAuthAuthorizationDecisionResponse"];

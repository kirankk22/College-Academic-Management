import { env } from "../config/env";

export async function getHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${env.apiBaseUrl}/health`);

  if (!response.ok) {
    throw new Error(`Backend health check failed: ${response.status}`);
  }

  return response.json();
}

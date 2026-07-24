import {parseApiResponse} from './api-error';

const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export type GeoflowStatus = {
  enabled: boolean;
  configured: boolean;
  public_base_url: string;
  public_cta_label: string;
  suite_path: string;
  mode: 'live' | 'preview' | string;
};

export type GeoflowHandoffRequest = {
  source?: 'manual' | 'solutions' | 'keywords' | 'plans' | 'diagnostic';
  conversation_id?: string;
  task_name?: string;
  brief?: string;
  keywords?: string[];
  force_preview?: boolean;
};

export type GeoflowHandoffResult = {
  mode: 'live' | 'preview' | string;
  status: string;
  message: string;
  task_name?: string;
  task_id?: number | string;
  keywords?: string[];
  titles?: Array<{title: string; keyword: string}>;
  geoflow_admin_url?: string;
  suite_path?: string;
  next_steps?: string[];
  brief_preview?: string;
};

export async function getGeoflowStatus(): Promise<GeoflowStatus> {
  const response = await fetch(`${API_BASE}/api/integrations/geoflow/status`, {
    headers: {Accept: 'application/json'},
    cache: 'no-store'
  });
  return parseApiResponse<GeoflowStatus>(response);
}

export async function handoffToGeoflow(payload: GeoflowHandoffRequest): Promise<GeoflowHandoffResult> {
  const response = await fetch(`${API_BASE}/api/integrations/geoflow/handoff`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return parseApiResponse<GeoflowHandoffResult>(response);
}

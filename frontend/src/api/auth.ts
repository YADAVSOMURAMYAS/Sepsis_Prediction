import { apiFetch } from './client'

export interface TokenResponse {
  access_token:  string
  token_type:    string
  hospital_id:   string
  hospital_name: string
}

export interface HospitalInfo {
  id:          string
  name:        string
  city:        string
  address:     string
  admin_email: string
  accent_color: string
  units:       string[]
  beds_total:  number
  established: string
}

export interface HospitalListItem {
  id:          string
  name:        string
  city:        string
  accent_color: string
  admin_email: string
}

export const authApi = {
  login: (admin_email: string, password: string) =>
    apiFetch<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ admin_email, password }),
    }),

  register: (payload: {
    id: string; name: string; city: string; address: string
    admin_email: string; password: string; accent_color?: string
    units?: string[]; beds_total?: number; established?: string
  }) =>
    apiFetch<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  me: () => apiFetch<HospitalInfo>('/auth/me'),

  listHospitals: () => apiFetch<HospitalListItem[]>('/hospitals'),
}

// Typed API client for the FastAPI backend. One axios instance with a bearer
// interceptor; every call maps 1:1 to an endpoint in app/api/routers.
import axios, { AxiosInstance } from "axios";
import type {
  ContractSummary, Deployment, JobOut, LibraryItem,
  QueueAction, QueueItem, Report, TokenResponse, User,
} from "../types";

const TOKEN_KEY = "cv_token";

export function getToken(): string | null { return localStorage.getItem(TOKEN_KEY); }
export function setToken(t: string | null): void {
  if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY);
}

export function createClient(baseURL = "/"): AxiosInstance {
  const http = axios.create({ baseURL });
  http.interceptors.request.use((cfg) => {
    const t = getToken();
    if (t) cfg.headers.Authorization = `Bearer ${t}`;
    return cfg;
  });
  return http;
}

const http = createClient();

export const api = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const { data } = await http.post<TokenResponse>("/api/auth/login", { username, password });
    setToken(data.access_token);
    return data;
  },
  logout(): void { setToken(null); },
  async me(): Promise<User> {
    return (await http.get<User>("/api/auth/me")).data;
  },
  async uploadContract(form: FormData, contractType?: string): Promise<JobOut> {
    const q = contractType ? `?contract_type=${encodeURIComponent(contractType)}` : "";
    return (await http.post<JobOut>(`/api/contracts${q}`, form)).data;
  },
  async getJob(jobId: string): Promise<JobOut> {
    return (await http.get<JobOut>(`/api/contracts/jobs/${jobId}`)).data;
  },
  async getReport(contractId: string): Promise<Report> {
    return (await http.get<Report>(`/api/contracts/${contractId}/report`)).data;
  },
  async listQueue(): Promise<QueueItem[]> {
    return (await http.get<QueueItem[]>("/api/queue")).data;
  },
  async actOnQueueItem(queueId: string, action: QueueAction, comment?: string): Promise<QueueItem> {
    return (await http.post<QueueItem>(`/api/queue/${queueId}/action`, { action, comment })).data;
  },
  async deployment(): Promise<Deployment> {
    return (await http.get<Deployment>("/api/deployment")).data;
  },
  async listContracts(): Promise<ContractSummary[]> {
    return (await http.get<ContractSummary[]>("/api/contracts")).data;
  },
  async uploadLibraryFiles(layer: "playbook" | "standard-terms", files: FileList | File[]): Promise<JobOut> {
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    return (await http.post<JobOut>(`/api/library/${layer}`, form)).data;
  },
  async listLibrary(layer: "playbook" | "standard-terms"): Promise<LibraryItem[]> {
    return (await http.get<LibraryItem[]>(`/api/library/${layer}`)).data;
  },
};

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { clientLogger, captureClientAlert } from "@/lib/logger";

const API_BASE_URL = "/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 20000,
});

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string }>) => {
    const originalRequest = error.config as RetryConfig | undefined;
    const status = error.response?.status;
    const url = originalRequest?.url || "";

    if (
      status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !url.includes("/auth/login") &&
      !url.includes("/auth/register") &&
      !url.includes("/auth/refresh") &&
      !url.includes("/auth/me")
    ) {
      originalRequest._retry = true;
      try {
        await axios.post(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true });
        return apiClient(originalRequest);
      } catch {
        clientLogger.warn({ url }, "Session refresh token expired");
      }
    }

    if (status && status >= 500) {
      captureClientAlert("Backend API 5xx error encountered", {
        url,
        status,
        detail: error.response?.data?.detail,
      });
    }

    return Promise.reject(error);
  }
);

export function extractErrorMessage(err: unknown, fallback = "An unexpected error occurred."): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
    }
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
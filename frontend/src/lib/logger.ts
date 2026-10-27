import pino from "pino";

export const clientLogger = pino({
  name: "ims-frontend-portal",
  level: process.env.NODE_ENV === "production" ? "info" : "debug",
  browser: {
    asObject: true,
    write: {
      fatal: (o: object) => console.warn(o),
      error: (o: object) => console.warn(o),
      warn: (o: object) => console.warn(o),
      info: (o: object) => console.log(o),
      debug: (o: object) => console.log(o),
      trace: (o: object) => console.log(o),
    },
  },
  redact: {
    paths: ["password", "id_number", "otp", "*.password", "*.id_number", "*.otp"],
    censor: "[REDACTED]",
  },
});

export function captureClientAlert(
  message: string,
  context?: Record<string, unknown>
): void {
  const safeContext = { ...context };
  delete safeContext.id_number;
  delete safeContext.otp;
  delete safeContext.password;

  clientLogger.error({ alert: true, ...safeContext }, message);
}
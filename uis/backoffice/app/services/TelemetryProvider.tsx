"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { initTelemetry, track, getDeviceType } from "./telemetry";

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const previousPathnameRef = useRef<string | null>(null);

  useEffect(() => {
    initTelemetry();

    // Global uncaught error handler
    const handleError = (event: ErrorEvent) => {
      track("api_request_failed", {
        api_route: window.location.pathname,
        method: "GET",
        status_code: 500,
        error_family: "frontend_uncaught_error",
        error_message_sanitized: (event.message || "Uncaught frontend error").slice(0, 200),
        retryable: false,
        request_source: "web_backoffice",
      });
    };

    // Unhandled promise rejections
    const handleRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const message =
        reason instanceof Error
          ? reason.message
          : typeof reason === "string"
          ? reason
          : "Unhandled promise rejection";

      track("api_request_failed", {
        api_route: window.location.pathname,
        method: "GET",
        status_code: 500,
        error_family: "frontend_unhandled_rejection",
        error_message_sanitized: message.slice(0, 200),
        retryable: false,
        request_source: "web_backoffice",
      });
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);

    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, []);

  // Track navigation changes
  useEffect(() => {
    if (!pathname) return;

    if (previousPathnameRef.current !== null && previousPathnameRef.current !== pathname) {
      const isMobile = typeof window !== "undefined" ? window.innerWidth < 768 : false;
      const deviceType = getDeviceType();
      track("backoffice_navigation_clicked", {
        from_path: previousPathnameRef.current,
        to_path: pathname,
        nav_surface: isMobile || deviceType === "mobile" ? "mobile" : "desktop",
        is_mobile: isMobile || deviceType === "mobile",
      });
    }

    previousPathnameRef.current = pathname;
  }, [pathname]);

  return <>{children}</>;
}

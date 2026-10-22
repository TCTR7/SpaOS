"use client";

import * as React from "react";
import { registerSpaServiceWorker } from "@/lib/web-push";
import { captureInstallPrompt, clearInstallPrompt } from "@/lib/pwa-install";

export function PwaRegister(): null {
  React.useEffect(() => {
    void registerSpaServiceWorker();
    window.addEventListener("beforeinstallprompt",captureInstallPrompt);
    window.addEventListener("appinstalled",clearInstallPrompt);
    return ()=>{window.removeEventListener("beforeinstallprompt",captureInstallPrompt);window.removeEventListener("appinstalled",clearInstallPrompt);};
  }, []);

  return null;
}

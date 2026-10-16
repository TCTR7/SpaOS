"use client";

import * as React from "react";
import { registerSpaServiceWorker } from "@/lib/web-push";

export function PwaRegister(): null {
  React.useEffect(() => {
    void registerSpaServiceWorker();
  }, []);

  return null;
}

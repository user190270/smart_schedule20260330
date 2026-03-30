import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.smartschedule.app",
  appName: "Smart Schedule",
  webDir: "dist",
  server: {
    cleartext: true
  }
};

export default config;

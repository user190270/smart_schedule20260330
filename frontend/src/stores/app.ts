import { defineStore } from "pinia";
import { getApiBaseUrl } from "@/services/runtime-config";

export const useAppStore = defineStore("app", {
  state: () => ({
    apiBaseUrl: getApiBaseUrl(),
    activeTab: "home"
  }),
  actions: {
    setActiveTab(tab: string) {
      this.activeTab = tab;
    }
  }
});


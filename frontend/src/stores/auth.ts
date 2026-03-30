import { defineStore } from "pinia";

import { fetchMe, login, logout, register, type LoginPayload, type RegisterPayload, type UserProfile } from "@/api/auth";
import { getStringValue } from "@/services/local-store";
import { useLocalScheduleStore } from "@/stores/local-schedules";

const ACCESS_TOKEN_KEY = "auth:access_token";

type AuthState = {
  user: UserProfile | null;
  initialized: boolean;
};

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    initialized: false
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user)
  },
  actions: {
    async syncLocalScheduleAccount(user: UserProfile | null) {
      const localScheduleStore = useLocalScheduleStore();
      await localScheduleStore.setCurrentAccount(user?.id ?? null);
    },
    async hydrate() {
      if (this.initialized) {
        return;
      }
      const token = await getStringValue(ACCESS_TOKEN_KEY);
      if (!token) {
        this.user = null;
        await this.syncLocalScheduleAccount(null);
        this.initialized = true;
        return;
      }
      try {
        this.user = await fetchMe();
      } catch {
        await logout();
        this.user = null;
      } finally {
        await this.syncLocalScheduleAccount(this.user);
        this.initialized = true;
      }
    },
    async login(payload: LoginPayload) {
      const result = await login(payload);
      this.user = result.user;
      await this.syncLocalScheduleAccount(this.user);
      this.initialized = true;
      return result.user;
    },
    async register(payload: RegisterPayload) {
      const result = await register(payload);
      this.user = result.user;
      await this.syncLocalScheduleAccount(this.user);
      this.initialized = true;
      return result.user;
    },
    async refreshProfile() {
      this.user = await fetchMe();
       await this.syncLocalScheduleAccount(this.user);
      this.initialized = true;
      return this.user;
    },
    async logout() {
      await logout();
      this.user = null;
      await this.syncLocalScheduleAccount(null);
      this.initialized = true;
    }
  }
});

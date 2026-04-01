import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import { pinia } from "@/stores/pinia";
import AdminView from "@/views/AdminView.vue";
import HomeView from "@/views/HomeView.vue";
import ParseView from "@/views/ParseView.vue";
import PublicShareView from "@/views/PublicShareView.vue";
import RagView from "@/views/RagView.vue";
import ScheduleView from "@/views/ScheduleView.vue";
import ShareView from "@/views/ShareView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView
    },
    {
      path: "/schedules",
      name: "schedules",
      component: ScheduleView
    },
    {
      path: "/parse",
      name: "parse",
      component: ParseView,
      meta: { requiresAuth: true }
    },
    {
      path: "/rag",
      name: "rag",
      component: RagView,
      meta: { requiresAuth: true }
    },
    {
      path: "/share",
      name: "share",
      component: ShareView,
      meta: { requiresAuth: true }
    },
    {
      path: "/share/public/:shareUuid",
      name: "share-public",
      component: PublicShareView,
      meta: { hideChrome: true }
    },
    {
      path: "/admin",
      name: "admin",
      component: AdminView,
      meta: { requiresAuth: true, requiresAdmin: true, hideChrome: true }
    }
  ]
});

router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth && !to.meta.requiresAdmin) {
    return true;
  }

  const authStore = useAuthStore(pinia);
  await authStore.hydrate();

  if (!authStore.isAuthenticated) {
    return { name: "home" };
  }

  if (to.meta.requiresAdmin && authStore.user?.role !== "admin") {
    return { name: "home" };
  }

  return true;
});

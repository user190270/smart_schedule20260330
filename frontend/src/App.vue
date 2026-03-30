<template>
  <div class="app-shell" :class="{ 'app-shell-plain': hideChrome }">
    <template v-if="!hideChrome">
      <header class="app-header">
        <h1>Smart Schedule</h1>
        <p>本地仓优先，云端同步与知识库链路显式可控。</p>
      </header>

      <main class="app-main">
        <RouterView v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </main>

      <footer class="app-footer">
        <van-tabbar v-model="active" @change="onTabChange">
          <van-tabbar-item name="home" icon="home-o">首页</van-tabbar-item>
          <van-tabbar-item name="schedules" icon="calendar-o">日程</van-tabbar-item>
          <van-tabbar-item name="parse" icon="notes-o">解析</van-tabbar-item>
          <van-tabbar-item name="rag" icon="chat-o">知识库</van-tabbar-item>
          <van-tabbar-item name="share" icon="share-o">分享</van-tabbar-item>
        </van-tabbar>
      </footer>
    </template>

    <template v-else>
      <RouterView />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";

import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";
import { useCloudSyncStore } from "@/stores/cloud-sync";
import { useLocalScheduleStore } from "@/stores/local-schedules";

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const authStore = useAuthStore();
const cloudSyncStore = useCloudSyncStore();
const localScheduleStore = useLocalScheduleStore();

const hideChrome = computed(() => route.meta.hideChrome === true);

const active = computed({
  get: () => appStore.activeTab,
  set: (value: string) => appStore.setActiveTab(value)
});

const routeByTab: Record<string, string> = {
  home: "/",
  schedules: "/schedules",
  parse: "/parse",
  rag: "/rag",
  share: "/share"
};

const tabByRoute: Record<string, string> = {
  "/": "home",
  "/schedules": "schedules",
  "/parse": "parse",
  "/rag": "rag",
  "/share": "share"
};

appStore.setActiveTab(tabByRoute[route.path] ?? "home");

watch(
  () => route.path,
  (path) => {
    appStore.setActiveTab(tabByRoute[path] ?? "home");
  }
);

watch(
  () => authStore.isAuthenticated,
  async (isAuthenticated) => {
    if (isAuthenticated) {
      await cloudSyncStore.refreshStatus().catch(() => undefined);
      return;
    }
    cloudSyncStore.clearCloudStatus();
  }
);

onMounted(async () => {
  await authStore.hydrate();
  await localScheduleStore.initialize();
  await cloudSyncStore.initialize();
});

function onTabChange(tabName: string) {
  const path = routeByTab[tabName];
  if (path && route.path !== path) {
    void router.push(path);
  }
}
</script>

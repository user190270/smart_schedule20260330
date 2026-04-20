<template>
  <div class="quota-page">
    <!-- Sleek Header -->
    <header class="quota-header">
      <div class="header-left">
        <van-button class="back-btn" plain round icon="arrow-left" size="small" @click="goBack">返回</van-button>
      </div>
      <div class="header-content">
        <h1 class="quota-title">配额与层级管理</h1>
        <p class="quota-subtitle">演示型层级入口，只模拟层级切换与每日 token 上限。</p>
      </div>
    </header>

    <main class="quota-main" v-if="user">
      <!-- High-end Account Status Card -->
      <section class="status-card">
        <div class="status-card-header">
          <div class="tier-badge">
            <van-icon name="vip-crown-o" />
            <span>{{ currentTier.label }}</span>
          </div>
          <span class="reset-note">按 Asia/Shanghai 自然日重置</span>
        </div>

        <div class="usage-overview">
          <div class="usage-stats">
            <div class="stat-item">
              <span class="stat-label">今日已用 (Tokens)</span>
              <div class="stat-value" :class="{ 'text-danger': isExceeded }">
                {{ formatNumber(user.daily_token_usage) }}
              </div>
            </div>
            <div class="stat-divider">/</div>
            <div class="stat-item">
              <span class="stat-label">每日上限</span>
              <div class="stat-value limit-value">
                {{ formatNumber(user.daily_token_limit) }}
              </div>
            </div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-info">
            <span class="progress-text" v-if="!isExceeded">配额使用良好</span>
            <span class="progress-text text-danger" v-else>
              <van-icon name="warning-o" /> 配额已超限
            </span>
            <span class="progress-percent">{{ usagePercent }}%</span>
          </div>
          <div class="progress-track">
            <div 
              class="progress-fill" 
              :class="{ 'fill-danger': isExceeded }"
              :style="{ width: `${usagePercent}%` }"
            ></div>
          </div>
          <p class="usage-scope">使用范围: Parse, RAG answer, query embedding, rebuild embedding</p>
        </div>
      </section>

      <!-- Professional Tier Selection -->
      <section class="tiers-section">
        <h2 class="section-title">层级与权益</h2>
        <div class="tier-grid">
          <div
            v-for="tier in tierCards"
            :key="tier.id"
            class="tier-panel"
            :class="{ 'is-active': user?.subscription_tier === tier.id }"
          >
            <div class="tier-panel-header">
              <h3 class="tier-name">{{ tier.label }}</h3>
              <div v-if="user?.subscription_tier === tier.id" class="current-badge">当前层级</div>
            </div>
            <div class="tier-limit">{{ tier.limitLabel }}</div>
            <p class="tier-desc">{{ tier.description }}</p>
            <div class="tier-note">{{ tier.note }}</div>
          </div>
        </div>

        <div class="upgrade-action">
          <van-button
            class="upgrade-btn"
            type="primary"
            round
            size="large"
            :loading="upgrading"
            :disabled="!nextTierId"
            @click="runDemoUpgrade"
          >
            {{ upgradeButtonLabel }}
          </van-button>
          <p class="demo-disclaimer">
            <van-icon name="info-o" />
            此操作仅演示“升级后配额立即提高”的支撑路径，不会产生真实订单或支付。
          </p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { showNotify } from "vant";

import type { SubscriptionTier } from "@/api/auth";
import { extractApiErrorMessage } from "@/services/api-errors";
import { useAuthStore } from "@/stores/auth";

type TierCard = {
  id: SubscriptionTier;
  label: string;
  limitLabel: string;
  note: string;
  description: string;
};

const tierCards: TierCard[] = [
  {
    id: "free",
    label: "Free",
    limitLabel: "5,000 token / 日",
    note: "基础演示层级",
    description: "适合轻量体验，演示每日 token 配额约束。"
  },
  {
    id: "plus",
    label: "Plus",
    limitLabel: "20,000 token / 日",
    note: "中阶演示层级",
    description: "通过演示升级即可获得更高的云端 token 预算。"
  },
  {
    id: "pro",
    label: "Pro",
    limitLabel: "50,000 token / 日",
    note: "高阶演示层级",
    description: "继续提高每日上限，用于展示分层 token 配额的差异。"
  }
];

const nextTierByCurrent: Record<SubscriptionTier, SubscriptionTier | null> = {
  free: "plus",
  plus: "pro",
  pro: null
};

const router = useRouter();
const authStore = useAuthStore();
const upgrading = ref(false);

const user = computed(() => authStore.user);
const currentTier = computed(() => tierCards.find((tier) => tier.id === user.value?.subscription_tier) ?? tierCards[0]);
const nextTierId = computed(() => (user.value ? nextTierByCurrent[user.value.subscription_tier] : null));

const usagePercent = computed(() => {
  if (!user.value || user.value.daily_token_limit <= 0) {
    return 0;
  }
  return Math.min(100, Math.round((user.value.daily_token_usage / user.value.daily_token_limit) * 100));
});

const isExceeded = computed(() => {
  if (!user.value) return false;
  return user.value.daily_token_usage >= user.value.daily_token_limit;
});

const upgradeButtonLabel = computed(() => {
  if (!nextTierId.value) {
    return "已处于最高演示层级";
  }
  const nextTier = tierCards.find((tier) => tier.id === nextTierId.value);
  return `演示升级到 ${nextTier?.label ?? nextTierId.value}`;
});

onMounted(async () => {
  await authStore.hydrate();
  if (authStore.isAuthenticated) {
    await authStore.refreshProfile().catch(() => undefined);
  }
});

async function runDemoUpgrade() {
  if (!nextTierId.value) {
    showNotify({ type: "warning", message: "当前已经是最高演示层级。" });
    return;
  }

  upgrading.value = true;
  try {
    const updated = await authStore.demoUpgrade(nextTierId.value);
    const tier = tierCards.find((item) => item.id === updated.subscription_tier);
    showNotify({
      type: "success",
      message: `演示升级成功，当前层级为 ${tier?.label ?? updated.subscription_tier}，每日 token 上限已更新。`
    });
  } catch (error) {
    showNotify({ type: "danger", message: extractApiErrorMessage(error, "演示升级失败，请稍后重试。") });
  } finally {
    upgrading.value = false;
  }
}

function goBack() {
  if (window.history.length > 1) {
    void router.back();
    return;
  }
  void router.push("/");
}

function formatNumber(value: number): string {
  return value.toLocaleString("zh-CN");
}
</script>

<style scoped>
.quota-page {
  min-height: 100vh;
  background-color: #f8f9fa;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #333;
}

.quota-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.back-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: #666;
  font-weight: 500;
  cursor: pointer;
}

.back-btn:hover {
  color: #1a73e8;
}

.quota-title {
  font-size: 28px;
  font-weight: 700;
  color: #111;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.quota-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

.quota-main {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* Status Card */
.status-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  border: 1px solid #eaeaea;
}

.status-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.tier-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f0f7ff;
  color: #1a73e8;
  padding: 6px 14px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
}

.reset-note {
  font-size: 13px;
  color: #888;
}

.usage-overview {
  margin-bottom: 32px;
}

.usage-stats {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 42px;
  font-weight: 700;
  color: #111;
  line-height: 1;
}

.limit-value {
  color: #888;
  font-size: 28px;
}

.stat-divider {
  font-size: 28px;
  color: #eaeaea;
  font-weight: 300;
  padding: 0 8px;
}

.text-danger {
  color: #d32f2f !important;
}

.progress-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 500;
}

.progress-text {
  color: #333;
}

.progress-percent {
  color: #666;
  font-variant-numeric: tabular-nums;
}

.progress-track {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1a73e8;
  border-radius: 4px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fill-danger {
  background: #d32f2f;
}

.usage-scope {
  margin: 4px 0 0;
  font-size: 12px;
  color: #999;
}

/* Tiers Section */
.tiers-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #111;
  margin: 0;
}

.tier-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.tier-panel {
  background: #fff;
  border: 1px solid #eaeaea;
  border-radius: 12px;
  padding: 24px;
  transition: all 0.2s ease;
  position: relative;
}

.tier-panel:hover {
  border-color: #d0d0d0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.tier-panel.is-active {
  border-color: #1a73e8;
  box-shadow: 0 0 0 1px #1a73e8, 0 4px 12px rgba(26, 115, 232, 0.08);
}

.tier-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.tier-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111;
}

.current-badge {
  font-size: 11px;
  background: #1a73e8;
  color: #fff;
  padding: 4px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.tier-limit {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  margin-bottom: 12px;
}

.tier-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin: 0 0 16px 0;
}

.tier-note {
  font-size: 12px;
  color: #888;
  background: #f8f9fa;
  padding: 8px 10px;
  border-radius: 6px;
}

/* Upgrade Action */
.upgrade-action {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upgrade-btn {
  width: 100%;
  max-width: 320px;
  height: 48px;
  font-weight: 600;
  font-size: 16px;
  box-shadow: 0 4px 12px rgba(26, 115, 232, 0.2);
}

.demo-disclaimer {
  font-size: 13px;
  color: #888;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Responsive */
@media (max-width: 768px) {
  .quota-page {
    padding: 16px;
  }

  .quota-title {
    font-size: 24px;
  }

  .status-card {
    padding: 20px;
  }

  .stat-value {
    font-size: 32px;
  }

  .limit-value, .stat-divider {
    font-size: 22px;
  }

  .tier-grid {
    grid-template-columns: 1fr;
  }
}
</style>

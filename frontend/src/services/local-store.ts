export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export type StoreKind = "capacitor" | "web";

type StoreAdapter = {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
  kind: StoreKind;
};

const WEB_PREFIX = "smart-schedule:";
const WEB_DB_NAME = "smart-schedule-web-store";
const WEB_DB_VERSION = 1;
const WEB_STORE_NAME = "kv";

const webAdapter: StoreAdapter = {
  kind: "web",
  async get(key: string) {
    return webStoreGet(`${WEB_PREFIX}${key}`);
  },
  async set(key: string, value: string) {
    await webStoreSet(`${WEB_PREFIX}${key}`, value);
  },
  async remove(key: string) {
    await webStoreDelete(`${WEB_PREFIX}${key}`);
  }
};

let adapterPromise: Promise<StoreAdapter> | null = null;
let indexedDbPromise: Promise<IDBDatabase> | null = null;

function getIndexedDb(): Promise<IDBDatabase> {
  if (indexedDbPromise) {
    return indexedDbPromise;
  }
  indexedDbPromise = new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !("indexedDB" in window)) {
      reject(new Error("IndexedDB is not available in this runtime."));
      return;
    }

    const request = window.indexedDB.open(WEB_DB_NAME, WEB_DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(WEB_STORE_NAME)) {
        db.createObjectStore(WEB_STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Failed to open IndexedDB."));
  });
  return indexedDbPromise;
}

async function withStore<T>(mode: IDBTransactionMode, fn: (store: IDBObjectStore) => Promise<T>): Promise<T> {
  const db = await getIndexedDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(WEB_STORE_NAME, mode);
    const store = tx.objectStore(WEB_STORE_NAME);
    fn(store)
      .then(resolve)
      .catch(reject);
    tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed."));
  });
}

function requestToPromise<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error("IndexedDB request failed."));
  });
}

async function webStoreGet(key: string): Promise<string | null> {
  try {
    return await withStore("readonly", async (store) => {
      const value = await requestToPromise(store.get(key));
      if (typeof value === "string") {
        return value;
      }
      return null;
    });
  } catch {
    return window.localStorage.getItem(key);
  }
}

async function webStoreSet(key: string, value: string): Promise<void> {
  try {
    await withStore("readwrite", async (store) => {
      await requestToPromise(store.put(value, key));
    });
  } catch {
    window.localStorage.setItem(key, value);
  }
}

async function webStoreDelete(key: string): Promise<void> {
  try {
    await withStore("readwrite", async (store) => {
      await requestToPromise(store.delete(key));
    });
  } catch {
    window.localStorage.removeItem(key);
  }
}

async function resolveAdapter(): Promise<StoreAdapter> {
  if (adapterPromise) {
    return adapterPromise;
  }

  adapterPromise = (async () => {
    try {
      const { Capacitor } = await import("@capacitor/core");
      if (!Capacitor.isNativePlatform()) {
        return webAdapter;
      }
      const { Preferences } = await import("@capacitor/preferences");
      return {
        kind: "capacitor",
        async get(key: string) {
          const data = await Preferences.get({ key });
          return data.value;
        },
        async set(key: string, value: string) {
          await Preferences.set({ key, value });
        },
        async remove(key: string) {
          await Preferences.remove({ key });
        }
      };
    } catch {
      return webAdapter;
    }
  })();

  return adapterPromise;
}

export async function setJsonValue(key: string, value: JsonValue): Promise<"capacitor" | "web"> {
  const adapter = await resolveAdapter();
  await adapter.set(key, JSON.stringify(value));
  return adapter.kind;
}

export async function getJsonValue<T extends JsonValue>(key: string): Promise<T | null> {
  const adapter = await resolveAdapter();
  const raw = await adapter.get(key);
  if (!raw) {
    return null;
  }
  return JSON.parse(raw) as T;
}

export async function removeValue(key: string): Promise<void> {
  const adapter = await resolveAdapter();
  await adapter.remove(key);
}

export async function setStringValue(key: string, value: string): Promise<"capacitor" | "web"> {
  const adapter = await resolveAdapter();
  await adapter.set(key, value);
  return adapter.kind;
}

export async function getStringValue(key: string): Promise<string | null> {
  const adapter = await resolveAdapter();
  return adapter.get(key);
}

export async function getStorageBackendKind(): Promise<StoreKind> {
  const adapter = await resolveAdapter();
  return adapter.kind;
}

# Mobile LAN Setup

## Current Scope

- Cloud backend remains the existing FastAPI + PostgreSQL + pgvector stack.
- Mobile shell is Capacitor + Android.
- Native local storage is still transitional in this round:
  - Web: IndexedDB
  - Native: Capacitor Preferences
- Native SQLite is not delivered in this round.

## Host Backend Startup

1. Start the backend stack on the host computer:
   - `docker compose up --build -d`
2. Confirm the host API responds on:
   - `http://localhost:8000/api/health`
3. Find the host computer's LAN IP, for example:
   - `192.168.1.101`

## Frontend API Configuration

- Host-browser development example:
  - `frontend/.env.example`
- LAN mobile debug example:
  - `frontend/.env.mobile.example`
- The mobile build should use the host LAN IP, for example:
  - `VITE_API_BASE_URL=http://192.168.1.101:8000/api`

## Android Shell Workflow

From `frontend/`:

1. Install dependencies:
   - `npm install`
2. Build and sync the Capacitor project:
   - `npm run android:sync`
3. Build the debug APK:
   - `npm run android:build`
4. Open Android Studio if needed:
   - `npm run android:open`

## Network Notes

- The phone/emulator and host computer must be on the same reachable network.
- Android cleartext HTTP is enabled in this repo through:
  - `frontend/capacitor.config.ts`
  - `frontend/android/app/src/main/AndroidManifest.xml`
  - `frontend/android/app/src/main/res/xml/network_security_config.xml`
- If the phone cannot reach the backend, verify:
  - Windows firewall allows inbound access to port `8000`
  - Docker is publishing port `8000`
  - the host LAN IP is still correct

## Current Machine Requirement

- Android SDK must be installed locally for `gradlew assembleDebug` to succeed.
- If Gradle reports missing `sdk.dir`, create or refresh:
  - `frontend/android/local.properties`
- Example:
  - `sdk.dir=C:\\Users\\<your-user>\\AppData\\Local\\Android\\Sdk`

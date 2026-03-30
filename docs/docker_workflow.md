# Docker Workflow

## Start

```powershell
docker compose up --build -d
```

## Check Status

```powershell
docker compose ps
docker compose logs api --tail 120
docker compose logs frontend --tail 120
```

## Stop

```powershell
docker compose down
```

## Notes

- API runs on `http://localhost:8000`
- Frontend runs on `http://localhost:5173`
- SQLite data is persisted in Docker volume `smart_schedule_data`


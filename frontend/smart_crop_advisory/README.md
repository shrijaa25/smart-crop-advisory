# Smart Crop Advisory frontend

This repository's frontend is a Flutter/Dart application (not React). It signs farmers in against the existing FastAPI API and supports authenticated farm setup, crop registration, crop-stage lookup, and daily-task generation.

## Run locally

Start the FastAPI backend from `D:\smartcropad\Smart_Crop_Daily_Task_Engine_Step1\smart_crop_task_engine_step1`:

```powershell
uvicorn app.main:app --reload
```

From this Flutter project directory, install packages and launch the web app:

```powershell
flutter pub get
flutter run -d chrome --web-port 5173 --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Open the frontend at <http://localhost:5173> and the backend API documentation at <http://127.0.0.1:8000/docs>.

`API_BASE_URL` is a Dart compile-time configuration value. For another local backend address, pass that address with the same `--dart-define` option. Do not put JWT signing secrets or database credentials in frontend configuration.

## Connected features and current limits

- Registration uses `POST /api/v1/auth/register` and sign-in uses the URL-encoded `POST /api/v1/auth/login` contract.
- The app verifies the farmer profile through `GET /api/v1/auth/me` and restores saved sessions through that endpoint.
- Farm details use `POST/GET /api/v1/farms`; the backend sets ownership from the JWT farmer identity.
- Crop cycles use `POST /api/v1/farms/{farm_id}/crops` and `GET /api/v1/crop-cycles`. The backend checks that the selected farm belongs to the authenticated farmer.
- Crop age and stage use the protected `GET /api/v1/tasks/crop-stage` endpoint. Stage names appear only for a unique verified crop-stage rule.
- Daily tasks use protected `GET /api/v1/tasks?task_date=...` and `POST /api/v1/tasks/generate?target_date=...` endpoints. Generation is user-triggered and only verified active rules qualify.
- Sign-out clears the stored token. Backend ownership checks remain responsible for protecting farmer data.
- Weather, crop recommendations, and task completion are not connected because the current backend does not expose those endpoints. The UI displays empty states instead of sample recommendations or fabricated farmer data. If no verified active rules match, generating zero tasks is expected.

Bearer tokens are stored through `flutter_secure_storage`. On Flutter Web, browser storage cannot provide the same protection as an HttpOnly cookie. The current backend returns bearer tokens, so this app follows that contract; production web deployment should consider a backend-supported HttpOnly, Secure, SameSite cookie flow with CSRF protection.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import router
from app.auth import router as auth_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="dota_sensei",
    description="Analyse past Dota 2 matches and point out mistakes.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Signed cookie session. "lax" is required rather than "strict": the Steam
# callback arrives as a top-level cross-site redirect, and a strict cookie
# wouldn't be sent on the navigation that follows it.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=settings.session_https_only,
)

app.include_router(auth_router, prefix="/api")
app.include_router(router)


def main() -> None:
    """`python -m app.main` — dev server on 8273."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()

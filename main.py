from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.routers import auth, generate, plans, spotify


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    print(f"Starting Cycle Planner in {settings.app_env} mode")
    yield
    # Shutdown
    print("Shutting down Cycle Planner")


app = FastAPI(
    title="Cycle Planner",
    description="AI-powered cycle class lesson plan generator",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
settings = get_settings()
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(plans.router, prefix="/api/plans", tags=["plans"])
app.include_router(spotify.router, prefix="/api/spotify", tags=["spotify"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Page routes
from fastapi import Request


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("generator.html", {"request": request})


@app.get("/plans")
async def plans_page(request: Request):
    return templates.TemplateResponse("plans.html", {"request": request})


@app.get("/plan/new")
async def new_plan_page(request: Request):
    return templates.TemplateResponse("plan_edit.html", {"request": request})


@app.get("/plan/{plan_id}")
async def view_plan_page(request: Request, plan_id: str):
    return templates.TemplateResponse("plan_view.html", {"request": request, "plan_id": plan_id})


@app.get("/plan/{plan_id}/edit")
async def edit_plan_page(request: Request, plan_id: str):
    return templates.TemplateResponse("plan_edit.html", {"request": request, "plan_id": plan_id})


@app.get("/spotify-connected")
async def spotify_connected_page(request: Request):
    return templates.TemplateResponse("spotify_connected.html", {"request": request})


@app.get("/play/{plan_id}")
async def play_plan_page(request: Request, plan_id: str):
    return templates.TemplateResponse("player.html", {"request": request, "plan_id": plan_id})


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

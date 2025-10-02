from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from loguru import logger
from typing import Optional
logger.add("app.log", rotation="10 MB", retention="7 days")
from app.providers.container import Container
from app.providers.config import Configs
from app.providers.context_storage import ContextStorage
from app.utils.database import SessionLocal, Base, engine

import app.services.provider as provider_svc
import app.repository.connector as repo

# Routers
from app.api.v1.main_router import MainRouter
from app.api.v1.connector import router as ConnectorRouter
from app.api.v1.llmchat import chat_router
from app.api.v1.provider import router as ProviderRouter
from app.api.v1.provider import vectordb as vectordb
from app.api.v1.connector import cap_router as capabilityrouter
from app.api.v1.connector import inference_router as inference_router
from app.api.v1.connector import actions as actions
from app.api.v1.provider import sample as sample_sql
from app.api.v1.auth import login as login


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI startup and shutdown lifecycle"""
    logger.info(">>> Starting FastAPI lifespan")

    # -------------------------------
    # Startup logic
    # -------------------------------
    logger.info("creating application container")
    container = Container()

    logger.info("loading necessary configurations")
    json_config = Configs().model_dump(mode="json")
    container.config.from_dict(json_config)
    container.config.from_dict(app.config)

    app.config["models"] = []
    logger.level("SB", no=27, color="<yellow>")

    if container.config.logging_enabled():
        logger.add(
            "trace.log",
            level="SB",
            colorize=False,
            backtrace=True,
            diagnose=True
        )

    logger.info("creating database tables")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    logger.info("initializing plugin providers")
    err = provider_svc.initialize_plugin_providers(session)
    if err:
        logger.critical(err)

    logger.info("initializing vector store")
    err = provider_svc.initialize_vectordb_provider(session)
    if err:
        logger.critical(err)

    logger.info("initializing embeddings")
    err = provider_svc.initialize_embeddings(session)
    if err:
        logger.critical(err)

    logger.info("setting all configuration status to 1")
    repo.default_configuration_status(session)

    logger.info("creating local context storage")
    context_storage = ContextStorage(session)

    # store objects in app state
    app.container = container
    app.context_storage = context_storage
    app.db_session = session

    # hand control back to FastAPI
    yield

    # -------------------------------
    # Shutdown logic
    # -------------------------------
    logger.info(">>> Shutting down FastAPI lifespan")

    # close DB session
    try:
        if hasattr(app, "db_session"):
            app.db_session.close()
            logger.info("DB session closed")
    except Exception as e:
        logger.error(f"Error closing DB session: {e}")

    # cleanup container or other resources
    try:
        if hasattr(app, "container"):
            app.container.shutdown_resources()
            logger.info("Container resources released")
    except Exception as e:
        logger.error(f"Error shutting down container: {e}")


def create_app(config):
    logger.info("Creating FastAPI app")

    app = FastAPI(lifespan=lifespan)

    # Attach config before lifespan runs
    app.config = config

    # -------------------------------
    # Static mounts
    # -------------------------------
    app.mount("/assets", StaticFiles(directory="./assets"), name="assets")
    app.mount(
        "/ui/assets",
        StaticFiles(directory="./ui/dist/assets", html=True),
        name="ui"
    )
    app.mount(
        "/ui/dist-library",
        StaticFiles(directory="./ui/dist-library", html=True),
        name="embedbot"
    )

    templates = Jinja2Templates(directory="./ui/dist")

    @app.get("/ui", response_class=HTMLResponse)
    @app.get("/ui/{full_path:path}", response_class=HTMLResponse)
    def serve_home(request: Request, full_path: Optional[str] = ""):
        if request:
            return templates.TemplateResponse("index.html", context={"request": request})
        else:
            return templates.TemplateResponse("index.html")

    # -------------------------------
    # CORS middleware
    # -------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["OPTIONS", "GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    # -------------------------------
    # Routers
    # -------------------------------
    app.include_router(MainRouter, prefix="/api/v1/query")
    app.include_router(ConnectorRouter, prefix="/api/v1/connector")
    app.include_router(chat_router, prefix="/api/v1/chat")
    app.include_router(ProviderRouter, prefix="/api/v1/provider")
    app.include_router(capabilityrouter, prefix="/api/v1/capability")
    app.include_router(inference_router, prefix="/api/v1/inference")
    app.include_router(actions, prefix="/api/v1/actions")
    app.include_router(sample_sql, prefix="/api/v1/sql")
    app.include_router(login, prefix="/api/v1/auth")
    app.include_router(vectordb, prefix="/api/v1/vectordb")

    # -------------------------------
    # OpenAPI schema info
    # -------------------------------
    curr_schema = app.openapi()
    curr_schema["info"]["title"] = "Rag genie Chat API"
    curr_schema["info"]["description"] = "API for raggenie cloud chatbot"

    return app

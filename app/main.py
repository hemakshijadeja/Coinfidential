from fastapi import FastAPI

from app.api import transfers, wallets
from app.errors import add_error_handlers

app = FastAPI(title="Coinfidential", version="0.1.0")
add_error_handlers(app)
app.include_router(wallets.router)
app.include_router(transfers.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import users
from app.routes import groups
from app.routes import group_members
from app.routes.expenses import router as expenses_router
from app.routes.expense_participants import router as expense_participants_router

app = FastAPI(title="Shared Expenses API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(groups.router)
app.include_router(group_members.router)
app.include_router(expenses_router)
app.include_router(expense_participants_router)

@app.get("/")
def root():
    return {"message": "Shared Expenses API is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}

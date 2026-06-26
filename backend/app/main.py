"""FastAPI application - MVP with in-memory storage + real Flux generation."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from app.config import get_settings

# === In-Memory Storage ===
users_db: dict[str, dict] = {}
tasks_db: dict[str, dict] = {}
settings = get_settings()

security_scheme = HTTPBearer()


# === Auth helpers ===
def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, tenant_id: str) -> str:
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user = users_db.get(payload["sub"])
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# === LLM Prompt Optimization (Tokenpony / OpenAI-compatible) ===
async def optimize_prompt(user_input: str) -> str:
    """Use LLM to translate Chinese→English and optimize for image generation."""
    api_key = settings.llm_api_key
    api_base = settings.llm_api_base
    if not api_key or api_key == "your-llm-api-key-here":
        # Fallback: basic template
        return (
            f"A professional e-commerce product photograph: {user_input}. "
            "Commercial photography style, clean composition, soft natural lighting, "
            "8k resolution, high quality product shot, professional color grading."
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": settings.llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert prompt engineer for AI image generation (Flux/Stable Diffusion). "
                            "The user describes a product photo they want. "
                            "1. If the input is in Chinese, translate it to English first. "
                            "2. Expand the description into a professional image generation prompt. "
                            "3. Include details: product placement, lighting, composition, camera angle, background, mood. "
                            "4. Add quality keywords: 'commercial photography, 8k, professional product shot, studio lighting'. "
                            "5. Output ONLY the English prompt, 50-150 words, no explanations, no markdown."
                        ),
                    },
                    {"role": "user", "content": user_input},
                ],
                "temperature": 0.7,
                "max_tokens": 300,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            prompt = data["choices"][0]["message"]["content"].strip()
            return prompt
        else:
            # Fallback
            error_detail = resp.text if hasattr(resp, 'text') else str(resp.status_code)
            return (
                f"A professional e-commerce product photograph: {user_input}. "
                "Commercial photography style, clean composition, soft natural lighting, "
                "8k resolution, high quality product shot, professional color grading."
            )


# === Image Generation (Free Pollinations.ai + Replicate fallback) ===
async def generate_image_free(prompt: str) -> tuple[list[str], str | None]:
    """Try free Pollinations.ai first, fall back to Replicate."""
    # 1. Pollinations.ai (free, no key needed)
    try:
        import urllib.parse
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 5000:
                import base64
                data_url = f"data:image/jpeg;base64,{base64.b64encode(resp.content).decode()}"
                return [data_url], None
    except Exception:
        pass

    # 2. Try Replicate if configured
    api_key = settings.replicate_api_key
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://api.replicate.com/v1/predictions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "version": "black-forest-labs/flux-schnell",
                        "input": {"prompt": prompt, "width": 1024, "height": 1024, "num_outputs": 1, "output_format": "png"},
                    },
                )
                if resp.status_code == 201:
                    prediction = resp.json()
                    poll_url = prediction["urls"]["get"]
                    for _ in range(30):
                        import asyncio
                        await asyncio.sleep(1)
                        resp = await client.get(poll_url, headers={"Authorization": f"Bearer {api_key}"})
                        prediction = resp.json()
                        if prediction.get("status") == "succeeded":
                            output = prediction.get("output", [])
                            urls = [output] if isinstance(output, str) else (output or [])
                            return urls, None
                        elif prediction.get("status") in ("failed", "canceled"):
                            break
        except Exception:
            pass

    return [], "All generation methods failed. Try again or check API configuration."


# === App ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="E-Commerce AI Studio", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# === Schemas ===
class LoginReq(BaseModel):
    email: str
    password: str

class RegisterReq(BaseModel):
    email: str
    password: str
    name: str = ""
    tenant_name: str = "Default"

class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    email: str
    name: str

class GenerateReq(BaseModel):
    requirement: str
    model_name: str | None = None

class TaskResp(BaseModel):
    task_id: str
    status: str
    estimated_time_sec: int = 30

class TaskStatusResp(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    result_urls: list[str] = []
    error_message: str | None = None


# === Auth Endpoints ===
@app.post("/api/v1/auth/login", response_model=TokenResp)
async def login(req: LoginReq):
    user = users_db.get(req.email)
    if not user or not verify_pw(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], user["tenant_id"])
    return TokenResp(access_token=token, user_id=user["id"], tenant_id=user["tenant_id"], email=user["email"], name=user.get("name", ""))

@app.post("/api/v1/auth/register", response_model=TokenResp, status_code=201)
async def register(req: RegisterReq):
    if req.email in users_db:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = req.email
    tenant_id = f"tenant-{req.tenant_name.lower().replace(' ', '-')}"
    user = {
        "id": user_id, "tenant_id": tenant_id, "email": req.email,
        "password_hash": hash_pw(req.password), "name": req.name, "role": "admin",
    }
    users_db[req.email] = user
    token = create_token(user_id, tenant_id)
    return TokenResp(access_token=token, user_id=user_id, tenant_id=tenant_id, email=req.email, name=req.name)

@app.get("/api/v1/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"], "name": user.get("name"), "role": user["role"], "tenant_id": user["tenant_id"]}


# === Generation Endpoints ===
import uuid
import asyncio

# Build a prompt that describes an e-commerce product scene
def build_product_prompt(requirement: str) -> str:
    return (
        f"A professional e-commerce product photograph: {requirement}. "
        "Commercial photography style, clean composition, soft natural lighting, "
        "8k resolution, high quality product shot, professional color grading."
    )

@app.post("/api/v1/generate/image", response_model=TaskResp)
async def generate_image(req: GenerateReq, user: dict = Depends(get_current_user)):
    """Submit an image generation task. Uses Flux Schnell via Replicate."""
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {
        "task_id": task_id, "status": "running",
        "requirement": req.requirement, "result_urls": [],
        "progress": 0.0, "tenant_id": user["tenant_id"],
    }

    async def run_generation():
        # Step 1: LLM translation + optimization
        optimized = await optimize_prompt(req.requirement)
        # Step 2: Generate image
        urls, error = await generate_image_free(optimized)
        tasks_db[task_id] = {
            **tasks_db[task_id],
            "status": "completed" if urls else "failed",
            "progress": 1.0,
            "result_urls": urls,
            "error_message": error,
            "original_prompt": req.requirement,
            "optimized_prompt": optimized,
        }

    asyncio.create_task(run_generation())
    return TaskResp(task_id=task_id, status="queued", estimated_time_sec=15)

@app.get("/api/v1/generate/tasks/{task_id}", response_model=TaskStatusResp)
async def get_task_status(task_id: str, user: dict = Depends(get_current_user)):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return TaskStatusResp(
        task_id=task_id, status=task["status"], progress=task["progress"],
        result_urls=task["result_urls"], error_message=task.get("error_message"),
    )


# === Models Endpoint ===
@app.get("/api/v1/models")
async def list_models():
    return [
        {"name": "flux-schnell", "provider_type": "image", "provider": "black-forest-labs", "cost_per_image": 0.003, "is_enabled": True},
        {"name": "flux-pro", "provider_type": "image", "provider": "black-forest-labs", "cost_per_image": 0.05, "is_enabled": True},
        {"name": "dall-e-3", "provider_type": "image", "provider": "openai", "cost_per_image": 0.04, "is_enabled": True},
        {"name": "runway-gen3", "provider_type": "video", "provider": "runway", "cost_per_second": 0.25, "is_enabled": True},
        {"name": "kling", "provider_type": "video", "provider": "kuaishou", "cost_per_second": 0.10, "is_enabled": True},
    ]


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0", "flux_configured": bool(settings.replicate_api_key)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)

"""
FastAPI Server pour la Plateforme d'Analyse de Tendances Spark
Expose les fonctionnalités d'analyse de tendances via une API REST
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
import os
import uuid
from threading import Thread
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# ============================================
# CONFIGURATION LOGGING GLOBALE
# ============================================

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/spark_trend_logs/app.log')
    ]
)

# Créer le dossier s'il n'existe pas
from pathlib import Path as PathlibPath
PathlibPath('/tmp/spark_trend_logs').mkdir(exist_ok=True, parents=True)

from ..agents import analyze_trend
from ..models.config import Config
from ..utils.logger import setup_logger
from ..utils.serializers import make_json_serializable
from ..services.db_service import DatabaseService

# ============================================
# CONFIGURATION LOGGING
# ============================================

logger = setup_logger(__name__)

# ============================================
# DATABASE SERVICE
# ============================================

db_service = DatabaseService()

# ============================================
# JOB STORAGE (EN-MÉMOIRE)
# ============================================

jobs_storage: Dict[str, Dict[str, Any]] = {}


class JobManager:
    """Gestionnaire de jobs"""
    
    @staticmethod
    def create_job(prompt: str, spark_config: Dict, auto_recovery: bool) -> str:
        """Créer un nouveau job"""
        job_id = str(uuid.uuid4())
        jobs_storage[job_id] = {
            "job_id": job_id,
            "prompt": prompt,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
            "spark_config": spark_config,
            "auto_recovery": auto_recovery
        }
        return job_id
    
    @staticmethod
    def get_job(job_id: str) -> Optional[Dict]:
        """Récupérer un job"""
        return jobs_storage.get(job_id)
    
    @staticmethod
    def get_jobs(limit: int = 20) -> List[Dict]:
        """Récupérer les derniers jobs"""
        jobs_list = list(jobs_storage.values())
        jobs_list.sort(key=lambda x: x["created_at"], reverse=True)
        return jobs_list[:limit]
    
    @staticmethod
    def update_job(job_id: str, **kwargs):
        """Mettre à jour un job"""
        if job_id in jobs_storage:
            jobs_storage[job_id].update(kwargs)
    
    @staticmethod
    def execute_analysis_async(job_id: str, prompt: str, spark_config: Dict[str, Any] = None):
        """Exécuter l'analyse en arrière-plan"""
        try:
            JobManager.update_job(job_id, status="processing")
            db_service.save_job(job_id, "processing", prompt=prompt)
            logger.info(f"🚀 Analyse en cours pour job {job_id}")
            logger.info(f"📝 Prompt reçu: {prompt}")
            if spark_config:
                logger.info(f"⚙️  Config Spark: {spark_config}")
            
            try:
                result = analyze_trend(prompt, spark_config=spark_config or {})
                logger.info(f"✓ Résultat reçu: {type(result)}")
                logger.info(f"  Success: {result.get('success')}")
                logger.info(f"  Keys: {list(result.keys())}")
            except Exception as analyze_error:
                logger.error(f"❌ Erreur lors de l'analyse: {str(analyze_error)}", exc_info=True)
                JobManager.update_job(job_id, status="erreur", error=f"Analyze error: {str(analyze_error)}")
                db_service.save_job(job_id, "erreur", result={"error": str(analyze_error)})
                return
            
            if result.get("success"):
                logger.info(f"✅ Analyse succès pour job {job_id}")
                # Rendre le résultat sérialisable avant de le stocker
                from src.utils.serializers import make_json_serializable
                serializable_result = make_json_serializable(result)
                JobManager.update_job(
                    job_id,
                    status="succès",
                    result=serializable_result
                )
                db_service.save_job(job_id, "succès", result=serializable_result)
                logger.info(f"💾 Analyse terminée et sauvegardée pour job {job_id}")
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ Analyse échouée pour job {job_id}: {error_msg}")
                # Rendre le résultat sérialisable avant de le stocker
                from src.utils.serializers import make_json_serializable
                serializable_result = make_json_serializable(result)
                JobManager.update_job(
                    job_id,
                    status="erreur",
                    error=error_msg,
                    result=serializable_result
                )
                db_service.save_job(job_id, "erreur", result=serializable_result)
        except Exception as e:
            logger.error(f"❌ Erreur exception lors de l'analyse du job {job_id}: {str(e)}", exc_info=True)
            JobManager.update_job(job_id, status="erreur", error=str(e))
            db_service.save_job(job_id, "erreur", result={"error": str(e)})


# ============================================
# CRÉATION DE L'APP FASTAPI
# ============================================

app = FastAPI(
    title="Spark Trend Analyzer API",
    description="API pour l'analyse de tendances Spark avec LangChain et OpenAI GPT-4o",
    version="1.0.0"
)

# ============================================
# MIDDLEWARE CORS
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# CONFIGURATION DES FICHIERS STATIQUES
# ============================================

# Servir les fichiers statiques du dossier frontend/static
frontend_static_path = Path(__file__).parent.parent.parent / "frontend" / "static"
if frontend_static_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_static_path)), name="static")

# ============================================
# MODÈLES PYDANTIC
# ============================================

class TrendAnalysisRequest(BaseModel):
    """Requête d'analyse de tendance"""
    prompt: str
    description: Optional[str] = None


class TrendAnalysisV1Request(BaseModel):
    """Requête d'analyse de tendance (API v1)"""
    prompt: str
    auto_recovery: bool = True
    spark_config: Dict[str, Any] = {}


class TrendAnalysisResponse(BaseModel):
    """Réponse d'analyse de tendance"""
    success: bool
    timestamp: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ConfigResponse(BaseModel):
    """Configuration actuelle"""
    knox_host: str
    driver_memory: str
    driver_cores: int
    executor_memory: str
    executor_cores: int
    num_executors: int
    queue: str
    llm_model: str


class JobResponse(BaseModel):
    """Réponse de job"""
    job_id: str
    status: str
    prompt: str
    created_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RecoveryExecuteRequest(BaseModel):
    """Requête d'exécution de rattrapage"""
    action_index: int
    spark_config: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Réponse de santé"""
    status: str
    timestamp: str
    api_version: str
    config_status: str


# ============================================
# ENDPOINTS
# ============================================

@app.get("/api", tags=["Health"])
async def api_root():
    """Endpoint API racine"""
    try:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Spark Trend Analyzer API",
                "version": "1.0.0",
                "docs": "/docs",
                "ui": "/ui",
                "health": "/health",
                "config": "/config"
            }
        )
    except Exception as e:
        logger.error(f"Erreur: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/", tags=["Frontend"])
async def serve_root():
    """Rediriger vers l'interface web"""
    return FileResponse(
        Path(__file__).parent.parent.parent / "frontend" / "index_knox.html",
        media_type="text/html"
    )


@app.get("/ui", tags=["Frontend"])
async def serve_ui():
    """Servir l'interface web"""
    # Chercher dans plusieurs emplacements
    possible_paths = [
        Path(__file__).parent.parent.parent / "frontend" / "index_knox.html",
        Path(__file__).parent.parent.parent / "index_knox.html",
    ]
    
    for ui_file in possible_paths:
        if ui_file.exists():
            return FileResponse(ui_file, media_type="text/html")
    
    raise HTTPException(status_code=404, detail="Interface non trouvée")


@app.get("/index_knox.html", tags=["Frontend"])
async def serve_index():
    """Servir index_knox.html"""
    possible_paths = [
        Path(__file__).parent.parent.parent / "frontend" / "index_knox.html",
        Path(__file__).parent.parent.parent / "index_knox.html",
    ]
    
    for ui_file in possible_paths:
        if ui_file.exists():
            return FileResponse(ui_file, media_type="text/html")
    
    raise HTTPException(status_code=404, detail="Interface non trouvée")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Vérifier l'état de l'API"""
    try:
        # Vérifier la configuration
        config_valid = bool(Config.OPENAI_API_KEY)
        config_status = "OK" if config_valid else "MISSING_OPENAI_API_KEY"
        
        # Vérifier les autres dépendances
        additional_checks = {
            "knox_configured": bool(Config.KNOX_HOST),
            "ad_credentials_configured": bool(Config.AD_USER and Config.AD_PASSWORD),
            "llm_model": Config.LLM_MODEL
        }
        
        return HealthResponse(
            status="healthy" if config_valid else "degraded",
            timestamp=datetime.now().isoformat(),
            api_version="1.0.0",
            config_status=config_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            api_version="1.0.0",
            config_status=f"ERROR: {str(e)}"
        )


@app.get("/config", response_model=ConfigResponse, tags=["Configuration"])
async def get_config():
    """Récupérer la configuration actuelle"""
    try:
        return ConfigResponse(
            knox_host=Config.KNOX_HOST or "Not configured",
            driver_memory=Config.DRIVER_MEMORY,
            driver_cores=Config.DRIVER_CORES,
            executor_memory=Config.EXECUTOR_MEMORY,
            executor_cores=Config.EXECUTOR_CORES,
            num_executors=Config.NUM_EXECUTORS,
            queue=Config.QUEUE,
            llm_model=Config.LLM_MODEL
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la configuration: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/analyze", response_model=TrendAnalysisResponse, tags=["Analysis"])
async def analyze_trends(request: TrendAnalysisRequest):
    """
    Analyser les tendances des données Spark
    
    Args:
        request: Requête contenant le prompt d'analyse
    
    Returns:
        Résultats de l'analyse avec recommandations
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Le prompt ne peut pas être vide")
    
    if not Config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY non configurée")
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY non configurée. Veuillez configurer votre clé OpenAI."
        )
    
    try:
        logger.info(f"Analyse en cours pour: {request.prompt[:100]}...")
        
        result = analyze_trend(request.prompt)
        
        return TrendAnalysisResponse(
            success=result.get("success", False),
            timestamp=datetime.now().isoformat(),
            result=result.get("result"),
            error=result.get("error")
        )
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )


@app.post("/analyze-async", tags=["Analysis"])
async def analyze_trends_async(request: TrendAnalysisRequest, background_tasks: BackgroundTasks):
    """
    Analyser les tendances de manière asynchrone (pour les longues analyses)
    
    Args:
        request: Requête contenant le prompt d'analyse
        background_tasks: Tâches à exécuter en arrière-plan
    
    Returns:
        ID de la tâche et statut
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Le prompt ne peut pas être vide")
    
    if not Config.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY non configurée"
        )
    
    try:
        logger.info(f"Analyse asynchrone en cours pour: {request.prompt[:100]}...")
        
        # Ajouter la tâche en arrière-plan
        background_tasks.add_task(analyze_trend, request.prompt)
        
        return {
            "status": "queued",
            "message": "Analyse en cours en arrière-plan",
            "prompt": request.prompt[:100]
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de la tâche asynchrone: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )


@app.get("/docs-custom", tags=["Documentation"])
async def documentation():
    """Documentation personnalisée de l'API"""
    return {
        "title": "Spark Trend Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "health": {
                "path": "/health",
                "method": "GET",
                "description": "Vérifier l'état de l'API"
            },
            "config": {
                "path": "/config",
                "method": "GET",
                "description": "Récupérer la configuration actuelle"
            },
            "analyze": {
                "path": "/analyze",
                "method": "POST",
                "description": "Analyser les tendances (synchrone)",
                "example_prompt": "Vérifie les tendances de splio.users pour le 20260121"
            },
            "analyze_async": {
                "path": "/analyze-async",
                "method": "POST",
                "description": "Analyser les tendances (asynchrone)"
            }
        },
        "required_env_vars": [
            "OPENAI_API_KEY",
            "KNOX_HOST",
            "AD_USER",
            "AD_PASSWORD"
        ]
    }


# ============================================
# API V1 ENDPOINTS (POUR LA FRONTEND)
# ============================================

@app.get("/api/v1/jobs", tags=["API v1"])
async def get_jobs(page: int = Query(1, ge=1), limit: int = Query(5, ge=1, le=100)):
    """Récupérer la liste des jobs avec pagination"""
    try:
        # Récupérer depuis la base de données
        jobs, total = db_service.get_jobs_paginated(page=page, limit=limit)
        
        # Ajouter les infos de pagination
        total_pages = (total + limit - 1) // limit
        
        return JSONResponse(
            status_code=200,
            content={
                "data": jobs,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": total_pages
                }
            }
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/api/v1/analyze", tags=["API v1"])
async def analyze_v1(request: TrendAnalysisV1Request):
    """Créer une nouvelle analyse"""
    try:
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Le prompt ne peut pas être vide")
        
        if not Config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY non configurée")
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY non configurée. Veuillez configurer votre clé OpenAI."
            )
        
        # Parser le prompt pour extraire table et date
        prompt_str = request.prompt.strip()
        logger.info(f"Prompt brut reçu: {prompt_str[:200]}")
        
        table_name = None
        target_date = None
        
        # Essayer de parser comme JSON d'abord
        try:
            if prompt_str.startswith('{'):
                import json as json_module
                prompt_json = json_module.loads(prompt_str)
                table_name = prompt_json.get('table_name', prompt_json.get('table'))
                target_date = prompt_json.get('target_date', prompt_json.get('date'))
                logger.info(f"✓ Parsé comme JSON: table={table_name}, date={target_date}")
        except:
            pass
        
        # Si pas de JSON, essayer le format texte "Analyse table=... date=..."
        if not table_name or not target_date:
            import re
            # Chercher table name - accepte "splio.users", "splio.active" etc
            # Regex 1: cherche "table=splio.active" ou "table = splio.active"
            table_match = re.search(r'table\s*=\s*([a-zA-Z0-9_.]+)', prompt_str, re.IGNORECASE)
            
            if not table_match:
                # Regex 2: cherche "splio.active" (pattern schema.table)
                table_match = re.search(r'([a-z]+\.[a-z]+)', prompt_str, re.IGNORECASE)
            
            # Regex 3: cherche les 8 chiffres consécutifs (date YYYYMMDD)
            date_match = re.search(r'(\d{8})', prompt_str)
            
            if table_match:
                table_name = table_match.group(1).strip('"\',{}')
            if date_match:
                target_date = date_match.group(1)
            
            if table_name and target_date:
                logger.info(f"✓ Parsé comme texte: table={table_name}, date={target_date}")
        
        # Valider les paramètres extraits
        if not table_name or not target_date:
            logger.error(f"❌ Impossible de parser les paramètres du prompt: {prompt_str[:100]}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Le prompt doit contenir le nom de la table et la date.",
                    "examples": [
                        "Analyse table=splio.active date=20260127",
                        "Vérifie les tendances de splio.users pour le 20260121",
                        '{"table_name": "splio.active", "target_date": "20260127"}'
                    ]
                }
            )
        
        # Formater le prompt pour l'exécution
        prompt = f"Analyse table={table_name} date={target_date}"
        logger.info(f"Prompt final: {prompt}")
        
        # Créer le job
        job_id = JobManager.create_job(prompt, request.spark_config, request.auto_recovery)
        
        logger.info(f"Analyse créée: {job_id} - {prompt}")
        
        # Lancer l'analyse en arrière-plan
        thread = Thread(target=JobManager.execute_analysis_async, args=(job_id, prompt, request.spark_config))
        thread.daemon = True
        thread.start()
        
        return JSONResponse(
            status_code=200,
            content={
                "job_id": job_id,
                "status": "queued",
                "message": "Analyse ajoutée à la file d'attente"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'analyse: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/api/v1/jobs/{job_id}", tags=["API v1"])
async def get_job_status(job_id: str):
    """Récupérer le statut et les résultats d'un job"""
    try:
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID ne peut pas être vide")
        
        job = JobManager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job non trouvé")
        
        # Rendre le job sérialisable
        job_serializable = make_json_serializable(job)
        
        # Si l'analyse est complétée, formater les résultats pour affichage
        if job_serializable.get("status") == "completed" and job_serializable.get("result"):
            result = job_serializable["result"]
            
            # Construire une réponse lisible
            response_data = {
                "job_id": job_serializable["job_id"],
                "status": job_serializable["status"],
                "created_at": job_serializable["created_at"],
                "prompt": job_serializable["prompt"]
            }
            
            # Si c'est une analyse directe avec données brutes
            if isinstance(result, dict):
                if result.get("success"):
                    response_data["analysis_result"] = {
                        "table_name": result.get("table_name"),
                        "target_date": result.get("target_date"),
                        "analysis": result.get("analysis"),
                        "queries": result.get("queries")
                    }
                else:
                    response_data["error"] = result.get("error")
            
            return JSONResponse(status_code=200, content=response_data)
        
        # Sinon, retourner le job complet
        return JSONResponse(status_code=200, content=job_serializable)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/api/v1/jobs/{job_id}/results", tags=["API v1"])
async def get_job_results_html(job_id: str):
    """Récupérer les résultats d'une analyse au format HTML"""
    from fastapi.responses import HTMLResponse
    
    try:
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID ne peut pas être vide")
        
        job = db_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job non trouvé")
        
        status = job.get("status")
        
        # Générer HTML basé sur le statut
        if status == "pending":
            html_content = f"""
            <html>
            <head><title>Analyse {job_id}</title>
            <style>body {{ font-family: Arial; margin: 20px; }}</style>
            </head>
            <body>
            <h1>Analyse Spark Trend</h1>
            <p><strong>Job ID:</strong> {job_id}</p>
            <p><strong>Status:</strong> <span style="color: orange;">⏳ {status}</span></p>
            <p><strong>Prompt:</strong> {job.get('prompt', 'N/A')}</p>
            <p>L'analyse est en cours de traitement... Veuillez actualiser la page dans quelques secondes.</p>
            <a href="/api/v1/jobs/{job_id}/results">↻ Actualiser</a>
            </body>
            </html>
            """
        elif status == "processing":
            html_content = f"""
            <html>
            <head><title>Analyse {job_id}</title>
            <style>body {{ font-family: Arial; margin: 20px; }}</style>
            </head>
            <body>
            <h1>Analyse Spark Trend</h1>
            <p><strong>Job ID:</strong> {job_id}</p>
            <p><strong>Status:</strong> <span style="color: blue;">🔄 {status}</span></p>
            <p><strong>Prompt:</strong> {job.get('prompt', 'N/A')}</p>
            <p>L'analyse est en cours de traitement... Veuillez actualiser la page dans quelques secondes.</p>
            <a href="/api/v1/jobs/{job_id}/results">↻ Actualiser</a>
            </body>
            </html>
            """
        elif status == "succès":
            result = job.get("result", {})
            
            if isinstance(result, dict) and result.get("success"):
                analysis = result.get("analysis", {})
                table_name = result.get("table_name", "N/A")
                target_date = result.get("target_date", "N/A")
                queries = result.get("queries", {})
                verdict = analysis.get("verdict", "unknown")
                comparisons = analysis.get("comparisons", [])
                alerts = analysis.get("alerts", [])
                recovery_plan = analysis.get("recovery_plan")
                
                # Couleur du verdict  
                verdict_colors = {
                    "negative": "#ef4444",
                    "warning": "#f97316",
                    "positive": "#22c55e",
                    "stable": "#3b82f6",
                    "neutral": "#6b7280"
                }
                verdict_color_hex = verdict_colors.get(verdict, "#6b7280")
                verdict_bg_color = f"{verdict_color_hex}15"
                
                # Construire les requêtes SQL HTML
                queries_html = ""
                if queries:
                    queries_html = "<h3>📝 Requêtes SQL Générées</h3>"
                    
                    query_target = queries.get("query_target", "")
                    query_reference = queries.get("query_reference", "")
                    
                    if query_target:
                        queries_html += f"""
                        <div class="query-container">
                            <span class="query-label">Requête Cible (Date: {queries.get('target_date', '')})</span>
                            <pre>{query_target}</pre>
                        </div>
                        """
                    
                    if query_reference:
                        queries_html += f"""
                        <div class="query-container">
                            <span class="query-label">Requête Référence (Date: {queries.get('reference_date', '')})</span>
                            <pre>{query_reference}</pre>
                        </div>
                        """
                
                # Construire les comparaisons HTML avec données brutes
                comparisons_html = ""
                if comparisons:
                    comparisons_html = "<h3>📊 Résultats des Comparaisons</h3><table>"
                    comparisons_html += "<tr><th>Métrique</th><th>Valeur Cible</th><th>Valeur Référence</th><th>Variation</th><th>Variation %</th><th>Alerte</th></tr>"
                    for comp in comparisons:
                        alert_level = comp.get("alert", "NORMAL").upper()
                        alert_icon = {
                            "CRITICAL": "🔴",
                            "WARNING": "🟠",
                            "POSITIVE": "🟢",
                            "NORMAL": "⚪"
                        }.get(alert_level, "⚪")
                        comparisons_html += f"""
                        <tr>
                            <td><strong>{comp.get('metric', 'N/A')}</strong></td>
                            <td>{comp.get('target_value', 'N/A'):,.0f}</td>
                            <td>{comp.get('reference_value', 'N/A'):,.0f}</td>
                            <td>{comp.get('variation', 0):,.0f}</td>
                            <td><strong>{comp.get('variation_pct', 'N/A')}</strong></td>
                            <td>{alert_icon} {alert_level}</td>
                        </tr>
                        """
                    comparisons_html += "</table>"
                
                # Construire les alertes HTML
                alerts_html = ""
                if alerts:
                    alerts_html = "<h3>⚠️ Alertes Détectées</h3><ul class='alert-list'>"
                    for alert in alerts:
                        alerts_html += f"<li class='alert-item'>{alert}</li>"
                    alerts_html += "</ul>"
                
                # Construire le plan de rattrapage HTML
                recovery_html = ""
                if recovery_plan and recovery_plan.get("recovery_needed"):
                    recovery_html = "<h3>🔧 Plan de Rattrapage Proposé</h3>"
                    if recovery_plan.get("summary"):
                        recovery_html += f"<p style='font-size: 14px; color: #555; margin-bottom: 15px;'><strong>Résumé:</strong> {recovery_plan.get('summary')}</p>"
                    
                    for action in recovery_plan.get("actions", []):
                        priority = action.get('priority', 'MEDIUM').upper()
                        recovery_html += f"""
                        <div class="recovery-action priority-{priority}">
                            <span class="action-priority">{priority}</span>
                            <div class="action-title">{action.get('action', 'N/A')}</div>
                            <div class="action-details">{action.get('details', '')}</div>
                            <div class="action-steps">
                                <ol>
                        """
                        for step in action.get('steps', []):
                            recovery_html += f"<li>{step}</li>"
                        recovery_html += """
                                </ol>
                            </div>
                        </div>
                        """

                
                html_content = f"""
                <html>
                <head>
                    <title>Résultats - {job_id}</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        * {{
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }}
                        body {{
                            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                            background: linear-gradient(135deg, #f5f5f5 0%, #efefef 100%);
                            padding: 20px;
                            min-height: 100vh;
                        }}
                        .container {{
                            max-width: 1100px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 12px;
                            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
                            overflow: hidden;
                        }}
                        .header {{
                            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
                            color: white;
                            padding: 50px 30px;
                            text-align: center;
                            border-bottom: 4px solid #D94D05;
                        }}
                        .header h1 {{
                            font-size: 32px;
                            font-weight: 700;
                            margin-bottom: 10px;
                            letter-spacing: -0.5px;
                        }}
                        .header p {{
                            font-size: 14px;
                            opacity: 0.95;
                            margin: 0;
                        }}
                        .summary {{
                            background: linear-gradient(to right, #fff9f5 0%, #fffbf8 100%);
                            padding: 30px;
                            border-bottom: 1px solid #f0e4d8;
                            display: grid;
                            grid-template-columns: 1fr 1fr 1fr;
                            gap: 25px;
                        }}
                        .summary-item {{
                            padding: 15px;
                            background: white;
                            border-radius: 8px;
                            border-left: 4px solid #F97316;
                        }}
                        .summary-item strong {{
                            display: block;
                            color: #F97316;
                            font-size: 11px;
                            text-transform: uppercase;
                            font-weight: 700;
                            letter-spacing: 0.5px;
                            margin-bottom: 8px;
                        }}
                        .summary-item span {{
                            display: block;
                            font-size: 20px;
                            font-weight: 600;
                            color: #1a1a1a;
                        }}
                        .verdict-section {{
                            padding: 30px;
                            text-align: center;
                            background: white;
                            border-bottom: 1px solid #f0f0f0;
                        }}
                        .verdict {{
                            font-size: 48px;
                            font-weight: 700;
                            color: {verdict_color_hex};
                            text-transform: capitalize;
                            padding: 25px;
                            background: {verdict_bg_color};
                            border-radius: 12px;
                            display: inline-block;
                            margin-bottom: 15px;
                        }}
                        .content {{
                            padding: 35px;
                        }}
                        h3 {{
                            color: #1a1a1a;
                            font-size: 18px;
                            font-weight: 700;
                            border-bottom: 3px solid #F97316;
                            padding-bottom: 12px;
                            margin-top: 35px;
                            margin-bottom: 20px;
                            display: flex;
                            align-items: center;
                            gap: 10px;
                        }}
                        h3:first-child {{
                            margin-top: 0;
                        }}
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                            margin: 20px 0;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
                            border-radius: 8px;
                            overflow: hidden;
                        }}
                        th {{
                            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
                            color: white;
                            padding: 14px 16px;
                            text-align: left;
                            font-weight: 600;
                            font-size: 13px;
                            text-transform: uppercase;
                            letter-spacing: 0.3px;
                        }}
                        td {{
                            padding: 14px 16px;
                            border-bottom: 1px solid #f0f0f0;
                            font-size: 14px;
                        }}
                        tr {{
                            transition: background-color 0.2s ease;
                        }}
                        tbody tr:hover {{
                            background-color: #faf8f6;
                        }}
                        tbody tr:last-child td {{
                            border-bottom: none;
                        }}
                        pre {{
                            background: #f8f8f8;
                            border: 1px solid #e0e0e0;
                            border-radius: 6px;
                            padding: 14px;
                            overflow-x: auto;
                            font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                            font-size: 12px;
                            color: #333;
                            line-height: 1.4;
                        }}
                        pre::-webkit-scrollbar {{
                            height: 6px;
                        }}
                        pre::-webkit-scrollbar-track {{
                            background: #f0f0f0;
                        }}
                        pre::-webkit-scrollbar-thumb {{
                            background: #F97316;
                            border-radius: 3px;
                        }}
                        .query-container {{
                            background: white;
                            border: 1px solid #e8e8e8;
                            border-radius: 8px;
                            padding: 16px;
                            margin-bottom: 16px;
                        }}
                        .query-label {{
                            font-size: 12px;
                            font-weight: 700;
                            color: #F97316;
                            text-transform: uppercase;
                            margin-bottom: 10px;
                            display: block;
                            letter-spacing: 0.3px;
                        }}
                        .alert-list {{
                            list-style: none;
                        }}
                        .alert-item {{
                            padding: 12px 16px;
                            margin-bottom: 10px;
                            background: #fff8f5;
                            border-left: 4px solid #F97316;
                            border-radius: 4px;
                            font-size: 14px;
                            color: #333;
                        }}
                        .recovery-action {{
                            border-left: 4px solid #F97316;
                            padding: 18px;
                            margin-bottom: 18px;
                            background: linear-gradient(to right, #fff9f5 0%, #fffbf8 100%);
                            border-radius: 6px;
                            transition: all 0.2s ease;
                        }}
                        .recovery-action:hover {{
                            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.1);
                        }}
                        .priority-HIGH {{
                            border-left-color: #dc2626;
                            background: linear-gradient(to right, #fef2f2 0%, #fef5f5 100%);
                        }}
                        .priority-MEDIUM {{
                            border-left-color: #F97316;
                            background: linear-gradient(to right, #fff9f5 0%, #fffbf8 100%);
                        }}
                        .priority-LOW {{
                            border-left-color: #059669;
                            background: linear-gradient(to right, #f0fdf4 0%, #f7fbf5 100%);
                        }}
                        .action-priority {{
                            display: inline-block;
                            padding: 4px 10px;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 700;
                            text-transform: uppercase;
                            margin-right: 10px;
                            letter-spacing: 0.3px;
                        }}
                        .priority-HIGH .action-priority {{
                            background: #fecaca;
                            color: #7f1d1d;
                        }}
                        .priority-MEDIUM .action-priority {{
                            background: #fed7aa;
                            color: #7c2d12;
                        }}
                        .priority-LOW .action-priority {{
                            background: #bbf7d0;
                            color: #064e3b;
                        }}
                        .action-title {{
                            font-weight: 600;
                            font-size: 15px;
                            color: #1a1a1a;
                            margin-bottom: 8px;
                        }}
                        .action-details {{
                            font-size: 13px;
                            color: #666;
                            margin-bottom: 10px;
                            font-style: italic;
                        }}
                        .action-steps {{
                            margin-top: 10px;
                        }}
                        .action-steps ol {{
                            margin-left: 20px;
                            font-size: 13px;
                            color: #555;
                            line-height: 1.6;
                        }}
                        .action-steps li {{
                            margin-bottom: 6px;
                        }}
                        .footer {{
                            padding: 20px 30px;
                            background: #f8f8f8;
                            border-top: 1px solid #e8e8e8;
                            text-align: center;
                            font-size: 12px;
                            color: #888;
                        }}
                        .back-button {{
                            display: inline-block;
                            margin-top: 20px;
                            padding: 10px 20px;
                            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
                            color: white;
                            text-decoration: none;
                            border-radius: 6px;
                            font-weight: 600;
                            transition: transform 0.2s, box-shadow 0.2s;
                        }}
                        .back-button:hover {{
                            transform: translateY(-2px);
                            box-shadow: 0 6px 20px rgba(249, 115, 22, 0.3);
                        }}
                        @media (max-width: 768px) {{
                            .summary {{
                                grid-template-columns: 1fr;
                            }}
                            .header {{
                                padding: 30px 20px;
                            }}
                            .header h1 {{
                                font-size: 24px;
                            }}
                            .content {{
                                padding: 20px;
                            }}
                            h3 {{
                                font-size: 16px;
                            }}
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>📊 Rapport d'Analyse Spark Trend</h1>
                            <p>Analyse de tendance pour {table_name} • {target_date}</p>
                        </div>
                        
                        <div class="summary">
                            <div class="summary-item">
                                <strong>Table analysée</strong>
                                <span>{table_name}</span>
                            </div>
                            <div class="summary-item">
                                <strong>Date cible</strong>
                                <span>{target_date}</span>
                            </div>
                            <div class="summary-item">
                                <strong>Rapport généré</strong>
                                <span>{datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
                            </div>
                        </div>
                        
                        <div class="verdict-section">
                            <div class="verdict">{verdict}</div>
                        </div>
                        
                        <div class="content">
                            {queries_html}
                            {alerts_html}
                            {comparisons_html}
                            {recovery_html}
                        </div>
                        
                        <div class="footer">
                            <p>Rapport généré avec succès</p>
                            <a href="javascript:window.history.back();" class="back-button">← Retour</a>
                        </div>
                    </div>
                </body>
                </html>
                """
            else:
                # Cas d'erreur
                error_msg = result.get("error", "Erreur inconnue") if isinstance(result, dict) else str(result)
                table_name = result.get("table_name", "N/A") if isinstance(result, dict) else "N/A"
                target_date = result.get("target_date", "N/A") if isinstance(result, dict) else "N/A"
                queries = result.get("queries", {}) if isinstance(result, dict) else {}
                
                queries_html = ""
                if isinstance(queries, dict) and queries:
                    queries_html = "<h3>📝 Requêtes Générées</h3>"
                    
                    query_target = queries.get("query_target", "")
                    query_reference = queries.get("query_reference", "")
                    
                    if query_target:
                        queries_html += """
                        <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-left: 4px solid #2196F3;">
                        <strong>Requête Cible:</strong>
                        <pre style="background: white; padding: 10px; overflow-x: auto;">{}</pre>
                        </div>
                        """.format(query_target)
                    
                    if query_reference:
                        queries_html += """
                        <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-left: 4px solid #FF9800;">
                        <strong>Requête Référence:</strong>
                        <pre style="background: white; padding: 10px; overflow-x: auto;">{}</pre>
                        </div>
                        """.format(query_reference)
                
                html_content = f"""
                <html>
                <head><title>Erreur - {job_id}</title>
                <style>
                    body {{ 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        overflow: hidden;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }}
                    h1 {{ margin: 0; font-size: 28px; }}
                    .summary {{
                        background: #f9f9f9;
                        padding: 20px;
                        border-bottom: 1px solid #ddd;
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                    }}
                    .summary-item {{
                        padding: 10px;
                    }}
                    .summary-item strong {{
                        display: block;
                        color: #ff6b6b;
                        font-size: 12px;
                        text-transform: uppercase;
                        margin-bottom: 5px;
                    }}
                    .summary-item span {{
                        display: block;
                        font-size: 16px;
                        color: #333;
                    }}
                    .error-box {{
                        font-size: 16px;
                        color: #cc0000;
                        padding: 15px;
                        text-align: center;
                        background: #ffe6e6;
                        border-left: 4px solid #cc0000;
                        border-radius: 4px;
                        margin: 20px 0;
                        font-family: 'Courier New', monospace;
                        word-break: break-all;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    h3 {{
                        color: #333;
                        border-bottom: 2px solid #ff6b6b;
                        padding-bottom: 10px;
                        margin-top: 30px;
                    }}
                    pre {{
                        background: #f5f5f5;
                        padding: 10px;
                        border-radius: 4px;
                        overflow-x: auto;
                        font-size: 12px;
                    }}
                    .footer {{
                        background: #f9f9f9;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #ddd;
                    }}
                    a {{
                        color: #667eea;
                        text-decoration: none;
                        margin: 0 10px;
                        font-weight: 600;
                    }}
                    a:hover {{ text-decoration: underline; }}
                </style>
                </head>
                <body>
                <div class="container">
                    <div class="header">
                        <h1>❌ Erreur lors de l'exécution</h1>
                    </div>
                    
                    <div class="summary">
                        <div class="summary-item">
                            <strong>Job ID</strong>
                            <span>{job_id}</span>
                        </div>
                        <div class="summary-item">
                            <strong>Status</strong>
                            <span>ERREUR</span>
                        </div>
                        {f'<div class="summary-item"><strong>Table</strong><span>{table_name}</span></div>' if table_name != "N/A" else ''}
                        {f'<div class="summary-item"><strong>Date cible</strong><span>{target_date}</span></div>' if target_date != "N/A" else ''}
                    </div>
                    
                    <div class="content">
                        <div class="error-box">
                            {error_msg}
                        </div>
                        
                        {queries_html}
                        
                        <h3>ℹ️ Suggestions</h3>
                        <ul>
                            <li>Vérifiez que le nom de la table est correct (ex: splio.active)</li>
                            <li>Assurez-vous que la date existe dans la table (format: YYYYMMDD)</li>
                            <li>Vérifiez vos droits d'accès aux données Spark</li>
                            <li>Consultez les logs pour plus de détails</li>
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <a href="/api/v1/jobs">← Retour à la liste des analyses</a>
                        <a href="/api/v1/jobs/{job_id}/results">↻ Actualiser</a>
                    </div>
                </div>
                </body>
                </html>
                """
        else:
            # Cas d'un statut inconnu ou inattendu
            html_content = f"""
            <html>
            <head><title>Analyse {job_id}</title>
            <meta charset="UTF-8">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #ffa500 0%, #ff8c00 100%);
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #ffa500 0%, #ff8c00 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                h1 {{ margin: 0; font-size: 28px; }}
                .content {{
                    padding: 30px;
                }}
                .info-box {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .footer {{
                    padding: 20px 30px;
                    background: #f9f9f9;
                    border-top: 1px solid #ddd;
                    text-align: center;
                }}
                a {{
                    color: #ffa500;
                    text-decoration: none;
                    margin: 0 10px;
                    font-weight: 600;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
            </head>
            <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Analyse Indisponible</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <p><strong>Job ID:</strong> {job_id}</p>
                        <p><strong>Statut:</strong> {status}</p>
                    </div>
                    
                    <h3>Informations du Job</h3>
                    <p><strong>Prompt:</strong> {job.get('prompt', 'N/A')}</p>
                    <p><strong>Créé à:</strong> {job.get('created_at', 'N/A')}</p>
                    <p><strong>Mis à jour à:</strong> {job.get('updated_at', 'N/A')}</p>
                    
                    {f'<p><strong>Erreur:</strong> {job.get("error", "Statut inconnu")}</p>' if job.get('error') else '<p><em>Aucune erreur enregistrée</em></p>'}
                    
                    <h3>Que faire?</h3>
                    <ul>
                        <li>Vérifiez que le nom de la table est correct (ex: splio.active)</li>
                        <li>Assurez-vous que la date existe dans la table (format: YYYYMMDD)</li>
                        <li>Vérifiez que la table contient des données pour cette date</li>
                        <li>Consultez les logs du serveur pour plus de détails</li>
                    </ul>
                </div>
                <div class="footer">
                    <a href="/api/v1/jobs">← Retour à la liste des analyses</a>
                    <a href="/api/v1/jobs/{job_id}/results">↻ Actualiser</a>
                </div>
            </div>
            </body>
            </html>
            """
        
        return HTMLResponse(content=html_content)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la génération HTML du job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/api/v1/recovery/{job_id}/execute", tags=["API v1"])
async def execute_recovery_v1(job_id: str, request: RecoveryExecuteRequest):
    """Exécuter une action de rattrapage"""
    try:
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID ne peut pas être vide")
        
        job = JobManager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job non trouvé")
        
        if not job.get("result"):
            raise HTTPException(status_code=400, detail="Aucun résultat disponible pour ce job")
        
        result = job.get("result")
        actions = result.get("actions", [])
        
        if request.action_index >= len(actions):
            raise HTTPException(status_code=400, detail="Index d'action invalide")
        
        action = actions[request.action_index]
        logger.info(f"Exécution du rattrapage pour le job {job_id}: {action}")
        
        # Ici on simulera l'exécution du rattrapage
        # En production, cela devrait lancer le JAR Spark
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Rattrapage lancé: {action.get('action', 'Unknown')}",
                "job_id": job_id
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du rattrapage: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.delete("/api/v1/jobs/{job_id}", tags=["API v1"])
async def delete_job(job_id: str):
    """Supprimer un job de la base de données"""
    try:
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID ne peut pas être vide")
        
        # Supprimer de la base de données
        success = db_service.delete_job(job_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Erreur lors de la suppression du job")
        
        # Supprimer aussi de la mémoire si elle existe
        if job_id in jobs_storage:
            del jobs_storage[job_id]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Job {job_id} supprimé avec succès"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Gestionnaire d'erreur HTTP"""
    logger.error(f"HTTP Exception: {exc.detail}")
    return {
        "success": False,
        "error": exc.detail,
        "timestamp": datetime.now().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Gestionnaire d'erreur générale"""
    logger.error(f"Erreur non gérée: {str(exc)}", exc_info=True)
    return {
        "success": False,
        "error": "Une erreur interne s'est produite",
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# STARTUP/SHUTDOWN
# ============================================

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage"""
    logger.info("API en cours de démarrage...")
    logger.info(f"LLM Model: {Config.LLM_MODEL}")
    logger.info(f"Knox Host: {Config.KNOX_HOST}")
    logger.info("API prête à recevoir les requêtes")


@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt"""
    logger.info("API en cours d'arrêt...")


if __name__ == "__main__":
    import uvicorn
    
    # Configuration pour uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

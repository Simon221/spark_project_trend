"""
Service pour gérer la base de données PostgreSQL
Stockage et récupération de l'historique des jobs
"""

import psycopg2
from psycopg2.extras import DictCursor, Json
from typing import List, Dict, Any, Optional, Tuple
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service pour gérer les opérations sur PostgreSQL"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "trends",
        user: str = "simon",
        password: str = "passer123"
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        
        # Initialiser la base de données
        self.init_db()
    
    def _get_connection(self):
        """Obtient une connexion PostgreSQL"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return conn
        except psycopg2.Error as e:
            logger.error(f"Erreur connexion PostgreSQL: {e}")
            raise Exception(f"Impossible de se connecter à PostgreSQL: {e}")
    
    def init_db(self):
        """Initialise la base de données - crée les tables si elles n'existent pas"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Créer la table jobs_history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs_history (
                    id SERIAL PRIMARY KEY,
                    job_id VARCHAR(50) UNIQUE NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    result JSONB,
                    prompt TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_job_id ON jobs_history(job_id);
                CREATE INDEX IF NOT EXISTS idx_status ON jobs_history(status);
                CREATE INDEX IF NOT EXISTS idx_created_at ON jobs_history(created_at DESC);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("✓ Base de données initialisée")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation DB: {e}")
            raise
    
    def save_job(
        self,
        job_id: str,
        status: str,
        prompt: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Sauvegarde ou met à jour un job en base"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Vérifier si le job existe déjà
            cursor.execute("SELECT id FROM jobs_history WHERE job_id = %s", (job_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Mise à jour
                cursor.execute("""
                    UPDATE jobs_history
                    SET status = %s, result = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = %s
                """, (status, Json(result) if result else None, job_id))
            else:
                # Insertion
                cursor.execute("""
                    INSERT INTO jobs_history (job_id, status, prompt, result)
                    VALUES (%s, %s, %s, %s)
                """, (job_id, status, prompt, Json(result) if result else None))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✓ Job {job_id} sauvegardé en base")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde job: {e}")
            return False
    
    def get_jobs_paginated(
        self,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Récupère les jobs avec pagination"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Calculer l'offset
            offset = (page - 1) * limit
            
            # Récupérer le total
            cursor.execute("SELECT COUNT(*) as total FROM jobs_history")
            total = cursor.fetchone()["total"]
            
            # Récupérer les jobs
            cursor.execute("""
                SELECT 
                    id,
                    job_id,
                    status,
                    result,
                    prompt,
                    created_at,
                    updated_at
                FROM jobs_history
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            jobs = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convertir les tuples en dicts
            jobs_list = []
            for job in jobs:
                job_dict = dict(job)
                # Convertir les timestamps en strings ISO
                if job_dict.get("created_at"):
                    job_dict["created_at"] = job_dict["created_at"].isoformat()
                if job_dict.get("updated_at"):
                    job_dict["updated_at"] = job_dict["updated_at"].isoformat()
                jobs_list.append(job_dict)
            
            return jobs_list, total
        except Exception as e:
            logger.error(f"❌ Erreur récupération jobs: {e}")
            return [], 0
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un job par son ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute("""
                SELECT 
                    id,
                    job_id,
                    status,
                    result,
                    prompt,
                    created_at,
                    updated_at
                FROM jobs_history
                WHERE job_id = %s
            """, (job_id,))
            
            job = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if job:
                job_dict = dict(job)
                if job_dict.get("created_at"):
                    job_dict["created_at"] = job_dict["created_at"].isoformat()
                if job_dict.get("updated_at"):
                    job_dict["updated_at"] = job_dict["updated_at"].isoformat()
                return job_dict
            
            return None
        except Exception as e:
            logger.error(f"❌ Erreur récupération job: {e}")
            return None
    
    def delete_job(self, job_id: str) -> bool:
        """Supprime un job de la base"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM jobs_history WHERE job_id = %s", (job_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✓ Job {job_id} supprimé de la base")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur suppression job: {e}")
            return False
    
    def delete_multiple_jobs(self, job_ids: List[str]) -> bool:
        """Supprime plusieurs jobs"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for job_id in job_ids:
                cursor.execute("DELETE FROM jobs_history WHERE job_id = %s", (job_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✓ {len(job_ids)} jobs supprimés de la base")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur suppression multiple: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute("""
                SELECT
                    COUNT(*) as total_jobs,
                    SUM(CASE WHEN status = 'succès' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'erreur' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'en cours' THEN 1 ELSE 0 END) as in_progress
                FROM jobs_history
            """)
            
            stats = dict(cursor.fetchone())
            cursor.close()
            conn.close()
            
            return stats
        except Exception as e:
            logger.error(f"❌ Erreur stats: {e}")
            return {}

# Quick Start Guide - Spark Trend Analyzer

## Installation

### 1. Installer les dépendances

```bash
pip install -r config/requirements-openai.txt
```

### 2. Configurer les variables d'environnement

```bash
# Copier le fichier d'exemple
cp config/.env.example .env

# Éditer .env avec vos paramètres
nano .env
```

**Configuration minimale requise:**
- `OPENAI_API_KEY`: Votre clé OpenAI (https://platform.openai.com/api-keys)
- `KNOX_HOST`: Adresse du gateway Knox (ex: mespmasterprd3.orange-sonatel.com:8443)
- `AD_USER`: Identifiant LDAP
- `AD_PASSWORD`: Mot de passe LDAP

### 3. Démarrer le serveur

**Option 1: Avec script (recommandé)**
```bash
chmod +x start.sh
./start.sh
```

**Option 2: Manuel**
```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

## Accès

### Interface Web
```
http://localhost:8000/ui
```

### Documentation API (Swagger)
```
http://localhost:8000/docs
```

### Health Check
```bash
curl http://localhost:8000/health
```

### Configuration
```bash
curl http://localhost:8000/config
```

## Endpoints Principaux

### 1. Créer une analyse
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Vérifie les tendances de splio.users pour le 20260121",
    "auto_recovery": true,
    "spark_config": {}
  }'
```

Réponse:
```json
{
  "job_id": "abc123...",
  "status": "queued",
  "message": "Analyse ajoutée à la file d'attente"
}
```

### 2. Récupérer la liste des jobs
```bash
curl http://localhost:8000/api/v1/jobs?limit=20
```

### 3. Vérifier le statut d'une analyse
```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### 4. Exécuter une action de rattrapage
```bash
curl -X POST http://localhost:8000/api/v1/recovery/{job_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action_index": 0,
    "spark_config": {}
  }'
```

## Dépannage

### Erreur: OPENAI_API_KEY non configurée
```
Solution: Ajouter OPENAI_API_KEY dans le fichier .env et redémarrer le serveur
```

### Erreur: Module spark_trend_agent not found
```
Solution: S'assurer que vous êtes dans le bon répertoire et que les dépendances sont installées
pip install -r requirements-openai.txt
```

### Erreur: Connection refused (Knox Gateway)
```
Solution: Vérifier que KNOX_HOST est correct et que le gateway est accessible
```

## Architecture

```
┌─────────────────────────────────────────┐
│      Frontend (index_knox.html)         │
│     React + Tailwind CSS + Babel        │
└────────────────┬────────────────────────┘
                 │
                 │ REST API
                 ▼
┌─────────────────────────────────────────┐
│       FastAPI Server (api_server.py)    │
│  ├─ /api/v1/analyze                     │
│  ├─ /api/v1/jobs                        │
│  ├─ /api/v1/recovery/{job_id}/execute   │
│  └─ /health, /config                    │
└────────────────┬────────────────────────┘
                 │
                 │ LangChain Agent
                 ▼
┌─────────────────────────────────────────┐
│  Spark Trend Agent (spark_trend_agent.py)
│  ├─ Query Generator (LangChain Tool)    │
│  ├─ Spark Executor (Livy)               │
│  ├─ Trend Analyzer                      │
│  └─ Recovery Proposer                   │
└────────────────┬────────────────────────┘
                 │
                 │ HTTPS + LDAP Auth
                 ▼
┌─────────────────────────────────────────┐
│   Knox Gateway + Apache Livy             │
│   (Cluster Spark Orange Sonatel)        │
└─────────────────────────────────────────┘
```

## Support

Pour plus d'informations:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Apache Livy Documentation](https://livy.apache.org/)

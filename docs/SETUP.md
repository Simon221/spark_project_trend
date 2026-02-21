# Spark Trend Analyzer - Setup & Deployment Guide

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.8+
- pip (Python package manager)
- Un compte OpenAI avec une clé API valide

### Installation en 3 étapes

1. **Installer les dépendances**
```bash
pip install -r requirements-openai.txt
```

2. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
nano .env
```

3. **Démarrer l'API**
```bash
./start.sh
# ou manuellement:
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

### Accès
- **Interface Web**: http://localhost:8000/ui
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📋 Structure du Projet

```
spark_project_trend/
├── api_server.py              # ✨ Server FastAPI (NOUVEAU)
├── spark_trend_agent.py       # Agent LangChain pour l'analyse
├── knox_livy_client.py        # Client Livy + Knox Gateway
├── index_knox.html            # Interface web React
├── config.js                  # Configuration frontend (NOUVEAU)
├── requirements-openai.txt    # Dépendances Python
├── .env                       # Variables d'environnement
├── .env.example               # Exemple de configuration (NOUVEAU)
├── start.sh                   # Script de démarrage (NOUVEAU)
├── test_api.py                # Suite de test (NOUVEAU)
├── QUICKSTART.md              # Guide rapide (NOUVEAU)
└── SETUP.md                   # Ce fichier (NOUVEAU)
```

## 🔧 Configuration Détaillée

### Variables d'environnement essentielles

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE    # https://platform.openai.com/api-keys
LLM_MODEL=gpt-4o                         # Modèle LLM à utiliser

# Knox Gateway Configuration
KNOX_HOST=mespmasterprd3.orange-sonatel.com:8443
AD_USER=your_username
AD_PASSWORD=your_password

# Spark Configuration
DRIVER_MEMORY=4g
DRIVER_CORES=2
EXECUTOR_MEMORY=4g
EXECUTOR_CORES=2
NUM_EXECUTORS=4
QUEUE=root.datalake

# Recovery Jar
RECOVERY_JAR_PATH=hdfs://path/to/recovery.jar
RECOVERY_JAR_CLASS=com.orange.sonatel.Recovery
```

## 🧪 Tests

### Valider la configuration
```bash
python test_api.py
```

Résultat attendu:
```
✅ Connexion API
✅ Health Check
✅ Configuration
✅ Jobs
✅ Environnement

✅ Tous les tests sont passés!
```

### Tester manuellement un endpoint
```bash
# Health check
curl http://localhost:8000/health

# Configuration
curl http://localhost:8000/config

# Créer une analyse
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Vérifie les tendances de splio.users pour le 20260121"}'
```

## 📊 Architecture

### Stack Technique
- **Frontend**: React 18 + Tailwind CSS + Babel
- **API**: FastAPI (Python)
- **LLM**: LangChain + OpenAI GPT-4o
- **Spark**: Apache Livy + Knox Gateway
- **Server**: Uvicorn ASGI

### Flux de Requête
```
Frontend (React)
    ↓
FastAPI /api/v1/analyze
    ↓
JobManager (File d'attente)
    ↓
LangChain Agent (Async)
    ├─ SparkQueryGenerator
    ├─ LivySparkExecutor
    ├─ TrendAnalyzer
    └─ RecoveryProposer
    ↓
Knox Gateway + Livy
    ↓
Apache Spark Cluster
```

## 🐛 Dépannage

### Erreur: "Error loading ASGI app. Could not import module"
**Solution**: Assurez-vous que `api_server.py` existe et les imports sont correctes
```bash
python -c "from api_server import app; print('✅ OK')"
```

### Erreur: "OPENAI_API_KEY not configured"
**Solution**: Vérifier que OPENAI_API_KEY est défini dans .env
```bash
grep OPENAI_API_KEY .env
# Si vide, ajouter votre clé
```

### Erreur: "Connection refused" (Knox Gateway)
**Solution**: Vérifier que KNOX_HOST est correct et accessible
```bash
curl -k https://mespmasterprd3.orange-sonatel.com:8443/
```

### La frontend ne se charge pas
**Solution**: Assurez-vous que vous accédez à http://localhost:8000/ui
- ❌ http://localhost:8080/index_knox.html (ancien)
- ✅ http://localhost:8000/ui (nouveau - même serveur)

## 📈 Performance & Optimisation

### Configuration recommandée pour production
```bash
# Réduire DRIVER_MEMORY si peu de données
DRIVER_MEMORY=2g
DRIVER_CORES=1

# Adapter NUM_EXECUTORS à votre cluster
NUM_EXECUTORS=8

# Utiliser gpt-4-turbo pour plus de performance
LLM_MODEL=gpt-4-turbo
LLM_TEMPERATURE=0.3
```

### Logs
```bash
# Voir les logs en live
tail -f api_server.log

# Logs des erreurs seulement
grep ERROR api_server.log
```

## ✨ Nouvelles Fonctionnalités Ajoutées

### ✅ api_server.py
- FastAPI server avec CORS habilitée
- Endpoints `/api/v1/*` pour la frontend
- Job management en mémoire
- Traitement asynchrone des analyses
- Sérialisation JSON robuste

### ✅ Gestion des erreurs
- Try/catch systématique
- Validation des inputs
- Messages d'erreur détaillés
- Logging structuré

### ✅ Configuration
- `.env.example` pour faciliter la config
- `config.js` pour le frontend
- `start.sh` pour démarrage facile
- `test_api.py` pour validation

### ✅ Documentation
- `QUICKSTART.md` pour démarrage rapide
- `SETUP.md` (ce fichier) pour configuration détaillée
- Commentaires dans le code

## 📞 Support & Contribution

Pour signaler un bug ou proposer une amélioration:
1. Créer une issue GitHub
2. Fournir les logs pertinents
3. Décrire les étapes de reproduction

## 📝 Changelog

### Version 1.0.0 (Actuelle)
- ✨ Ajout du serveur FastAPI (`api_server.py`)
- ✨ Support des requêtes asynchrones
- ✨ Gestion complète des jobs
- ✨ Validation des inputs robuste
- 🐛 Correction des erreurs JSON
- 🐛 Amélioration du logging
- 📚 Documentation complète

## 🔐 Sécurité

⚠️ **IMPORTANT POUR PRODUCTION**:
```python
# Remplacer dans api_server.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://votre-domaine.com"],  # ❌ Ne pas utiliser "*"
    allow_credentials=True,
    allow_methods=["GET", "POST"],                # ❌ Restreindre les méthodes
    allow_headers=["Content-Type"],               # ❌ Restreindre les headers
)
```

## 📚 Ressources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Python](https://python.langchain.com/)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [Apache Livy](https://livy.apache.org/)
- [Uvicorn](https://www.uvicorn.org/)

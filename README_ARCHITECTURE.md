# Spark Trend Analyzer - Architecture Réorganisée

📦 **Plateforme d'analyse de tendances BigData avec IA**

Une application FastAPI complète pour analyser les tendances des données Spark avec LangChain et OpenAI GPT-4o.

## 🗂️ Structure du Projet (Nouvelle Architecture)

```
spark_project_trend/
├── src/                          # Code source principal
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py            # FastAPI application
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── trend_analyzer.py    # LangChain agent
│   │   └── livy_client.py       # Knox Livy client
│   ├── models/
│   │   ├── __init__.py
│   │   └── config.py            # Configuration globale
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Logging utilities
│       └── serializers.py       # JSON serializers
│
├── frontend/                     # Application web
│   ├── index_knox.html
│   ├── config.js
│   └── static/
│
├── docs/                         # Documentation
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── SETUP.md
│   └── ...
│
├── config/                       # Fichiers de configuration
│   ├── .env
│   ├── .env.example
│   └── requirements-openai.txt
│
├── scripts/                      # Scripts utilitaires
│   ├── start.sh
│   └── commands.sh
│
├── tests/                        # Tests unitaires
│   ├── __init__.py
│   ├── test_api.py
│   └── test_health.py
│
├── main.py                       # Point d'entrée
├── setup.py                      # Configuration setuptools
├── pyproject.toml               # PEP 518 config
├── .gitignore
└── README.md
```

## 🚀 Démarrage Rapide

### Installation

```bash
# Cloner le projet
git clone <repository>
cd spark_project_trend

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate  # Windows

# Installer le package en mode développement
pip install -e .

# Ou installer via requirements
pip install -r config/requirements-openai.txt
```

### Configuration

```bash
# Copier la configuration d'exemple
cp config/.env.example .env

# Éditer .env avec vos paramètres
# OPENAI_API_KEY=sk-...
# KNOX_HOST=your-knox-server.com:8443
# AD_USER=your-username
# AD_PASSWORD=your-password
```

### Lancement

```bash
# Via le script
./scripts/start.sh

# Ou directement en Python
python main.py

# Ou avec uvicorn
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
```

L'application sera disponible à:
- **Interface web**: http://localhost:8000/ui
- **API REST**: http://localhost:8000
- **Documentation OpenAPI**: http://localhost:8000/docs

## 📚 Documentation

- [README Complet](docs/README.md) - Documentation détaillée
- [Quickstart](docs/QUICKSTART.md) - Guide de démarrage 5 minutes
- [Configuration](docs/SETUP.md) - Configuration complète
- [Corrections Apportées](docs/CORRECTIONS.md) - Historique des fixes
- [Status](docs/STATUS.md) - État du projet

## 🏗️ Architecture

### Packages et Modules

- **src.api.server** - FastAPI application avec 11 endpoints REST
- **src.agents.trend_analyzer** - LangChain agent avec 5 outils spécialisés
- **src.agents.livy_client** - Client Apache Livy pour Knox Gateway
- **src.models.config** - Configuration centralisée avec variables d'environnement
- **src.utils.logger** - Logging avec console et fichier
- **src.utils.serializers** - Utilitaires de sérialisation JSON

### API Endpoints

#### Health & Configuration
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /config` - Récupérer la configuration

#### Analysis
- `POST /analyze` - Analyse synchrone
- `POST /analyze-async` - Analyse asynchrone
- `GET /docs-custom` - Documentation personnalisée

#### API v1 (Frontend)
- `GET /api/v1/jobs` - Liste des jobs
- `POST /api/v1/analyze` - Créer une analyse
- `GET /api/v1/jobs/{job_id}` - Statut d'une analyse
- `POST /api/v1/recovery/{job_id}/execute` - Exécuter rattrapage

## 🛠️ Développement

### Tests

```bash
# Lancer les tests
pytest tests/

# Avec couverture
pytest tests/ --cov=src --cov-report=html
```

### Installation en Mode Développement

```bash
# Installer avec dépendances dev
pip install -e ".[dev]"

# Linting
flake8 src/

# Type checking
mypy src/

# Formatting
black src/
```

## 🔧 Configuration Avancée

### Variables d'Environnement

```bash
# OpenAI
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o

# Knox/Livy
KNOX_HOST=mespmasterprd3.orange-sonatel.com:8443
AD_USER=sddesigner
AD_PASSWORD=...

# Spark
DRIVER_MEMORY=4g
EXECUTOR_MEMORY=4g
NUM_EXECUTORS=4
QUEUE=root.datalake
```

### Fichiers de Configuration

- `.env` - Variables d'environnement (à créer)
- `config/.env.example` - Template d'exemple
- `config/requirements-openai.txt` - Dépendances Python

## 📦 Installation en Production

### Via pip

```bash
pip install .
spark-trend-analyzer  # Lancer l'application
```

### Via Docker (futur)

```dockerfile
# À implémenter
```

## 🐛 Troubleshooting

### OPENAI_API_KEY non trouvée

```bash
# Vérifier que .env est configuré
cat .env | grep OPENAI_API_KEY

# Vérifier que .env est chargé
python -c "from dotenv import load_dotenv; from src.models.config import Config; print(Config.OPENAI_API_KEY[:20])"
```

### Erreur de connexion Knox

```bash
# Vérifier KNOX_HOST
curl -k https://your-knox-host:8443/

# Vérifier les credentials AD
curl -k -u user:pass https://your-knox-host:8443/gateway/cdp-proxy-api/livy/v1/sessions
```

## 📋 Checklist Qualité

- ✅ Structure en package Python (src/)
- ✅ Configuration centralisée (Config class)
- ✅ Logging structuré
- ✅ Tests unitaires (test_api.py, verify_project.py)
- ✅ Documentation complète
- ✅ CORS configuré
- ✅ Error handling robuste
- ✅ Async/await support
- ✅ JWT ready (à implémenter)
- ✅ Rate limiting ready (à implémenter)

## 📝 Versions

- **API**: v1.0.0
- **Python**: ≥3.9
- **FastAPI**: 0.109.0
- **LangChain**: 0.1.0
- **OpenAI**: 1.3.9

## 📄 License

MIT

## 👤 Auteur

Simon Pierre Diouf

## 🤝 Contributions

Les contributions sont bienvenues! Veuillez:
1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

**Pour plus de détails, consultez [docs/README.md](docs/README.md)**

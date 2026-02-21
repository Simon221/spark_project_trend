# 🔶 Spark Trend Analyzer - Version Knox/Orange Sonatel + OpenAI GPT-4o

Plateforme d'analyse de tendances BigData avec LangChain Agent, OpenAI GPT-4o et Apache Spark.
Authentification LDAP via Knox Gateway, gestion asynchrone des jobs, interface web réactive.

**Status:** ✅ v1.0.0 - Production Ready

---

## ⚡ Démarrage Rapide (5 minutes)

```bash
# 1. Configuration
cp config/.env.example .env
nano .env  # Ajouter votre OPENAI_API_KEY

# 2. Installation
pip install -r config/requirements-openai.txt

# 3. Démarrage
python main.py

# 4. Accès
# Interface Web:    http://localhost:8000/ui
# API Documentation: http://localhost:8000/docs
# Health Check:      http://localhost:8000/health
```

➡️ **Plus de détails:** Voir [QUICKSTART.md](QUICKSTART.md)

## 🎯 API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/` | Root API |
| `GET` | `/health` | Health check |
| `GET` | `/config` | Configuration actuelle |
| `GET` | `/ui` | Interface web |
| `GET` | `/docs` | Documentation Swagger |
| **`GET`** | **`/api/v1/jobs`** | **Récupérer les jobs** |
| **`POST`** | **`/api/v1/analyze`** | **Créer une analyse** |
| **`GET`** | **`/api/v1/jobs/{job_id}`** | **Détails d'une analyse** |
| **`POST`** | **`/api/v1/recovery/{job_id}/execute`** | **Exécuter action rattrapage** |

---

## ⚙️ Configuration

### Variables Knox (obligatoires)

```bash
KNOX_HOST=mespmasterprd3.orange-sonatel.com:8443
AD_USER=sddesigner
AD_PASSWORD=votre-mot-de-passe-ldap
```

### Variables OpenAI (obligatoires)

```bash
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0

# Modèles disponibles:
# - gpt-4o (le plus récent, multimodal) ⭐ RECOMMANDÉ
# - gpt-4-turbo (rapide et performant)
# - gpt-4 (stable)
# - gpt-3.5-turbo (économique, 10x moins cher)

# Obtenir votre clé: https://platform.openai.com/api-keys
```

### Configuration Spark (modifiable dans l'interface)

```bash
DRIVER_MEMORY=4g
DRIVER_CORES=2
EXECUTOR_MEMORY=4g
EXECUTOR_CORES=2
NUM_EXECUTORS=4
QUEUE=root.datalake
```

### JAR de Rattrapage

```bash
RECOVERY_JAR_PATH=hdfs://path/to/recovery.jar
RECOVERY_JAR_CLASS=com.orange.sonatel.Recovery
```

## 🎯 Utilisation

### Via Interface Web

1. **Accédez à l'interface**
   ```
   http://localhost:8000/ui
   ```

2. **Configurez Spark (optionnel)**
   - Driver Memory, Cores
   - Executor Memory, Cores
   - Nombre d'executors
   - Queue Yarn

3. **Posez votre question**
   ```
   Vérifie les tendances de splio.users pour le 20260127
   ```

4. **Visualisez les résultats**
   - Comparaison avec les 7 derniers jours
   - Détection d'anomalies
   - Verdicts (Positif, Stable, Attention, Négatif)

5. **Lancez le rattrapage si nécessaire**
   - Cliquer sur "Exécuter" dans les actions proposées
   - Le JAR sera lancé via Livy avec vos paramètres Spark

### Via API REST

**Créer une analyse:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Vérifie les tendances de splio.users pour le 20260121",
    "auto_recovery": true,
    "spark_config": {}
  }'
```

**Récupérer les jobs:**
```bash
curl http://localhost:8000/api/v1/jobs?limit=20
```

**Vérifier le statut d'une analyse:**
```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

**Exécuter une action de rattrapage:**
```bash
curl -X POST http://localhost:8000/api/v1/recovery/{job_id}/execute \
  -H "Content-Type: application/json" \
  -d '{"action_index": 0, "spark_config": {}}'
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────┐
│   Frontend (React 18 + Tailwind CSS)            │
│   http://localhost:8000/ui                      │
└──────────────┬──────────────────────────────────┘
               │
               │ REST API /api/v1/*
               ▼
┌─────────────────────────────────────────────────┐
│   FastAPI Server (api_server.py) ⭐ NOUVEAU    │
│   • Gestion des jobs asynchrones                │
│   • Sérialisation JSON robuste                  │
│   • Gestion d'erreurs complète                  │
│   • Logging détaillé                            │
└──────────────┬──────────────────────────────────┘
               │
               │ LangChain Agent
               ▼
┌─────────────────────────────────────────────────┐
│   Spark Trend Agent (spark_trend_agent.py)      │
│   • Query Generator (SQL)                       │
│   • Spark Executor (Livy)                       │
│   • Trend Analyzer                              │
│   • Recovery Proposer                           │
└──────────────┬──────────────────────────────────┘
               │
               │ OpenAI GPT-4o
               │ LangChain 0.1.0
               │ Pydantic 2.5.3
               │
               ▼
┌─────────────────────────────────────────────────┐
│   Knox Gateway + Apache Livy                    │
│   • LDAP Authentication                         │
│   • HTTPS                                       │
│   • Session Management                          │
└──────────────┬──────────────────────────────────┘
               │
               │ Apache Spark SQL
               ▼
┌─────────────────────────────────────────────────┐
│   Spark Cluster (Orange Sonatel)                │
│   • Exécution des requêtes SQL                  │
│   • Rattrapage JAR                              │
└─────────────────────────────────────────────────┘
```

## � Structure du Projet

```
spark_project_trend/
├── 🔧 Core
│   ├── api_server.py              ⭐ Serveur FastAPI (NOUVEAU)
│   ├── spark_trend_agent.py       Agent LangChain
│   ├── knox_livy_client.py        Client Livy/Knox
│   └── index_knox.html            Interface React
│
├── 📚 Documentation
│   ├── README.md                  ← Vous êtes ici
│   ├── QUICKSTART.md              Démarrage rapide (5 min)
│   ├── SETUP.md                   Configuration complète
│   ├── CORRECTIONS.md             Corrections appliquées
│   ├── STATUS.md                  Statut du projet
│   ├── INDEX.md                   Navigation
│   └── FINAL_REPORT.txt           Rapport final
│
├── 🧪 Tests
│   ├── test_api.py                Suite de tests
│   └── verify_project.py          Vérification intégrité
│
├── ⚙️  Configuration
│   ├── .env                       Variables d'environnement
│   ├── .env.example               Template de configuration
│   ├── config.js                  Configuration frontend
│   └── requirements-openai.txt    Dépendances Python
│
└── 🚀 Scripts
    ├── start.sh                   Script de démarrage
    └── commands.sh                Raccourcis pratiques
```

## 🎨 Interface Web

**Features:**
- ✅ Configuration Spark dynamique
- ✅ Historique des analyses
- ✅ Détails en temps réel
- ✅ Lancement JAR en 1 clic
- ✅ Badge "Knox Gateway"
- ✅ Couleurs Orange/Sonatel
- ✅ Design moderne (Tailwind CSS)
- ✅ React 18 interactif

**Accédez via:**
```
http://localhost:8000/ui
```

---

## 🧪 Tests

**Valider la configuration:**
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

**Vérifier l'intégrité du projet:**
```bash
python verify_project.py
```

Résultat attendu:
```
✅ 15/15 fichiers requis trouvés
✅ PROJET COMPLET ET PRÊT!
```

---

## 🔒 Sécurité

### Développement (Actuel)
- ✅ CORS activé pour tous les domaines
- ✅ Auto-reload du serveur
- ✅ Logs détaillés
- ✅ Variables d'environnement sécurisées (.env ignoré par git)

### Production (À faire)
- ⚠️ Restreindre CORS: `allow_origins=["https://your-domain.com"]`
- ⚠️ Désactiver reload: `reload=False`
- ⚠️ Utiliser HTTPS/TLS
- ⚠️ Ajouter authentification JWT/OAuth2
- ⚠️ Utiliser secrets manager pour credentials
- ⚠️ Configurer rate limiting

### Sécurité Knox Gateway
- Authentification LDAP obligatoire
- SSL/TLS via Knox
- Sessions Livy temporaires et automatiquement fermées
- Mot de passe en variable d'environnement (pas versionné)

Voir [SETUP.md#Sécurité](SETUP.md#sécurité) pour plus de détails.

## 💡 Exemple Complet

### Via Python (LangChain Agent)

```python
from spark_trend_agent import analyze_trend

# Analyser les tendances
result = analyze_trend(
    "Vérifie les tendances de splio.users pour le 20260121"
)

# Résultat
print(result)
# {
#   "success": True,
#   "result": {
#     "status": "completed",
#     "analysis": {...},
#     "trend": "negative",
#     "actions": [...]
#   }
# }
```

### Via API REST

```bash
# Créer une analyse
JOB=$(curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Vérifie les tendances de splio.users pour le 20260121",
    "auto_recovery": true
  }' | jq -r '.job_id')

echo "Job ID: $JOB"

# Attendre un peu
sleep 2

# Vérifier le statut
curl http://localhost:8000/api/v1/jobs/$JOB | jq .

# Résultat:
# {
#   "job_id": "abc123...",
#   "status": "completed",
#   "prompt": "Vérifie les tendances de splio.users pour le 20260121",
#   "result": {...},
#   "error": null
# }
```

### Via Interface Web

1. Accédez à http://localhost:8000/ui
2. Tapez: "Vérifie les tendances de splio.users pour le 20260121"
3. Cliquez "Lancer l'analyse"
4. Consultez les résultats en temps réel

---

## ⚠️ Dépannage

| Erreur | Cause | Solution |
|--------|-------|----------|
| **Module api_server not found** | api_server.py manquant | `git pull` ou voir SETUP.md |
| **OPENAI_API_KEY not configured** | Variable env manquante | `nano .env` + redémarrer |
| **CORS policy blocked** | Ports différents | Utiliser `http://localhost:8000/ui` |
| **TypeError: 'dict' not callable** | Incompatibilité JSON | Vérifier la version FastAPI |
| **Connection refused (Knox)** | KNOX_HOST incorrect | Vérifier `.env` |
| **Unauthorized (LDAP)** | Credentials LDAP invalides | Vérifier AD_USER/AD_PASSWORD |
| **Session timeout** | Timeout trop court | Augmenter dans config |
| **Queue full** | Trop de jobs Spark | Réduire NUM_EXECUTORS |

**Besoin d'aide?**
1. Consultez [SETUP.md#Dépannage](SETUP.md#dépannage)
2. Consultez [CORRECTIONS.md](CORRECTIONS.md)
3. Exécutez `python test_api.py`
4. Vérifiez les logs: `tail -f api_server.log`

---

## 📚 Documentation Complète

| Document | Contenu | Durée |
|----------|---------|-------|
| **[QUICKSTART.md](QUICKSTART.md)** | Démarrage rapide + exemples | **5 min** ⭐ |
| **[SETUP.md](SETUP.md)** | Configuration détaillée | 15 min |
| **[CORRECTIONS.md](CORRECTIONS.md)** | Corrections appliquées | 10 min |
| **[STATUS.md](STATUS.md)** | Statut du projet | 5 min |
| **[INDEX.md](INDEX.md)** | Navigation du projet | On demand |
| **/docs** | Swagger API interactive | On demand |

---

## 🔗 Ressources Externes

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Python](https://python.langchain.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Apache Livy](https://livy.apache.org/)
- [Apache Spark SQL](https://spark.apache.org/docs/latest/sql-programming-guide.html)
- [Uvicorn ASGI Server](https://www.uvicorn.org/)

---

## 📈 Roadmap (Futures Améliorations)

- [ ] Persistence en base de données (PostgreSQL)
- [ ] File d'attente Redis
- [ ] Authentification JWT/OAuth2
- [ ] WebSocket pour updates temps réel
- [ ] Monitoring (Prometheus/Grafana)
- [ ] Containerization (Docker/Kubernetes)
- [ ] CI/CD (GitHub Actions)
- [ ] Cache distribué

---

## 📝 Changelog

### v1.0.0 (21 février 2026) ✅
- ✨ API Server complet (FastAPI)
- ✨ 11 endpoints REST
- ✨ Job management asynchrone
- ✨ Gestion d'erreurs robuste
- ✨ Validation stricte des inputs
- ✨ Sérialisation JSON fiable
- ✨ Tests automatisés
- ✨ Documentation complète
- 🐛 Correction erreurs JSON
- 🐛 Correction problèmes CORS
- 🐛 Correction environnement

Voir [CORRECTIONS.md](CORRECTIONS.md) pour détails.

---

## 🎉 Contribution & Support

Pour signaler un bug ou proposer une amélioration:
1. Créer une issue avec description claire
2. Fournir les logs pertinents
3. Décrire les étapes de reproduction

---

## 📄 Licence

Adapté pour Orange Sonatel - 2026

---

**Prêt à démarrer?** 🚀

```bash
./start.sh
```

Puis accédez à: **http://localhost:8000/ui**

Ou consultez [QUICKSTART.md](QUICKSTART.md) pour plus de détails.
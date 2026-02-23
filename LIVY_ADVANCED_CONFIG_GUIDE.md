# Guide: Configuration Avancée Livy pour le Rattrapage

## 📋 Vue d'ensemble

Le système de rattrapage (recovery) utilise Apache Livy pour soumettre des tâches Spark (JAR) pour récupérer des données manquantes. Les configurations avancées de Livy permettent de contrôler:

- **jars**: JARs supplémentaires à ajouter au classpath
- **files**: Fichiers à copier dans le répertoire de travail
- **archives**: Archives (tar/tgz/zip) à extraire automatiquement
- **pyFiles**: Fichiers Python pour PySpark jobs
- **conf**: Configuration Spark avancée (shuffles, allocation dynamique, etc.)

---

## 🔧 Configuration dans le fichier `.env`

### 1. LIVY_JARS
Ajoute des JARs supplémentaires au classpath Spark.

**Format**: Chemin HDFS séparés par des virgules

**Exemple**:
```env
LIVY_JARS=hdfs:///user/sddesigner/lib/commons-lang3-3.12.0.jar,hdfs:///user/sddesigner/lib/jackson-databind-2.15.0.jar
```

**Cas d'usage**:
- Dépendances du JAR de rattrapage
- Bibliothèques communes utilisées dans plusieurs projets
- Versions alternatives de librairies (remplace les versions pré-incluses)

---

### 2. LIVY_FILES
Copie les fichiers dans le répertoire de travail du job Spark.

**Format**: Chemins HDFS séparés par des virgules

**Exemple**:
```env
LIVY_FILES=hdfs:///config/app.properties,hdfs:///config/log4j.xml,hdfs:///sql/queries.sql
```

**Cas d'usage**:
- Fichiers de configuration application
- Fichiers de requêtes SQL
- Fichiers de logging customisés
- Scripts ou données statiques

---

### 3. LIVY_ARCHIVES
Extrait automatiquement les archives dans le répertoire de travail.

**Format**: Archives (tar.gz, tgz, zip) séparées par des virgules

**Exemple**:
```env
LIVY_ARCHIVES=hdfs:///archives/dependencies-2024.tar.gz,hdfs:///archives/models.zip
```

**Cas d'usage**:
- Distribuer plusieurs fichiers d'un coup
- Modèles ML dans archives compressées
- Dossiers entiers de ressources

---

### 4. LIVY_PY_FILES
Ajoute des fichiers Python au path Python du job (pour PySpark).

**Format**: Chemins HDFS séparés par des virgules

**Exemple**:
```env
LIVY_PY_FILES=hdfs:///python/utils.py,hdfs:///python/transformers.zip
```

**Cas d'usage**:
- Code Python partagé entre jobs
- Modules personnalisés
- ZIP contenant des packages Python

---

### 5. LIVY_CONF
Configuration Spark avancée au format JSON.

**Format**: Objet JSON avec clés de configuration Spark

**Exemple**:
```env
LIVY_CONF={"spark.sql.shuffle.partitions":"200","spark.dynamicAllocation.enabled":"true","spark.executor.heartbeatInterval":"60s"}
```

**Cas d'usage courant**:
```json
{
  "spark.sql.shuffle.partitions": "200",        // Nombre partitions pour shuffle SQL
  "spark.dynamicAllocation.enabled": "true",    // Allocation dynamique des executors
  "spark.shuffle.compress": "true",              // Compression du shuffle
  "spark.executor.heartbeatInterval": "60s",    // Timeout heartbeat
  "spark.sql.adaptive.enabled": "true",         // Query optimization adaptatif
  "spark.broadcast.blockSize": "128m"           // Taille broadcast
}
```

---

## 🚀 Flux d'exécution

### 1. Configuration chargée au démarrage du serveur
Au démarrage de `server.py`, la classe `Config` charge les variables d'environnement:

```python
livy_client = KnoxLivyClient(
    knox_host=Config.KNOX_HOST,
    ad_user=Config.AD_USER,
    ...
    jars=Config.get_livy_jars(),              # Parse LIVY_JARS depuis .env
    files=Config.get_livy_files(),            # Parse LIVY_FILES depuis .env
    conf=Config.get_livy_conf(),              # Parse LIVY_CONF depuis .env
    archives=Config.get_livy_archives(),      # Parse LIVY_ARCHIVES depuis .env
    py_files=Config.get_livy_py_files()       # Parse LIVY_PY_FILES depuis .env
)
```

### 2. Utilisateur clique sur "Faire un rattrapage"
L'interface affiche un formulaire avec:
- **Chemin du JAR**: `jarPath` (ex: `hdfs:///user/sddesigner/recovery.jar`)
- **Arguments**: `jarArgs` (ex: `--date 20240101 --table splio.active`)

### 3. API soumet le JAR à Livy
L'endpoint `POST /api/v1/recovery/execute-jar` appelle:

```python
result = livy_client.submit_jar(jar_path, jar_args)
```

### 4. KnoxLivyClient construit la payload complète
La méthode `submit_jar()` inclut TOUS les configs avancés:

```python
payload = {
    "file": jar_path,                    # JAR principal
    "args": [jar_args],                 # Arguments du JAR
    "driverMemory": "4g",               # Du Config
    "driverCores": 2,                   # Du Config
    "executorMemory": "4g",             # Du Config
    "executorCores": 2,                 # Du Config
    "numExecutors": 4,                  # Du Config
    "queue": "root.datalake",           # Du Config
    "proxyUser": "sddesigner",          # Du Config + PROXY_USER
    "conf": {...},                      # LIVY_CONF parsé depuis .env
    "archives": [...],                  # LIVY_ARCHIVES parsé depuis .env
    "files": [...],                     # LIVY_FILES parsé depuis .env
    "jars": [...]                       # LIVY_JARS parsé depuis .env
}
```

### 5. Livy reçoit et exécute le job
La payload est envoyée à `POST /batches` sur le gateway Knox.

---

## 📝 Exemples complets

### Exemple 1: JAR simple sans dépendances
```env
LIVY_JARS=
LIVY_FILES=hdfs:///config/app.properties
LIVY_ARCHIVES=
LIVY_PY_FILES=
LIVY_CONF={}
```

### Exemple 2: JAR avec dépendances et configuration
```env
LIVY_JARS=hdfs:///libs/commons-lang3-3.12.jar,hdfs:///libs/httpcomponents-client-4.5.jar
LIVY_FILES=hdfs:///config/app.properties,hdfs:///config/secrets.xml
LIVY_ARCHIVES=
LIVY_PY_FILES=
LIVY_CONF={"spark.sql.shuffle.partitions":"500","spark.dynamicAllocation.maxExecutors":"10"}
```

### Exemple 3: Récupération avec modèle ML
```env
LIVY_JARS=hdfs:///libs/ml-libs.jar
LIVY_FILES=hdfs:///config/database.properties
LIVY_ARCHIVES=hdfs:///models/model-2024.tar.gz
LIVY_PY_FILES=
LIVY_CONF={"spark.executor.memoryOverhead":"1g"}
```

---

## ✅ Vérification

Pour vérifier que les configurations sont bien chargées, utilisez:

```python
from src.models.config import Config

print("JARs:", Config.get_livy_jars())
print("Files:", Config.get_livy_files())
print("Archives:", Config.get_livy_archives())
print("PyFiles:", Config.get_livy_py_files())
print("Conf:", Config.get_livy_conf())
```

---

## 🔒 Notes de sécurité

1. **Chemins HDFS**: Utilisez des chemins absolus HDFS (`hdfs:///...`) ou des chemins réseau accessibles
2. **Permissions**: Assurez-vous que l'utilisateur `sddesigner` (PROXY_USER) a accès aux fichiers
3. **Secrets**: Ne commitez JAMAIS le `.env` avec des secrets en Git
4. **Format JSON**: Validez votre JSON dans `LIVY_CONF` avant de redémarrer le serveur

---

## 📖 Ressources supplémentaires

- [Documentation Livy REST API](https://livy.apache.org/docs/latest/rest-api)
- [Spark Configuration](https://spark.apache.org/docs/latest/configuration.html)
- [Apache Knox Gateway](https://knox.apache.org/)


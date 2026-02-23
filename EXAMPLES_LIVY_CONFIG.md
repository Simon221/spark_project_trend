# Exemples d'utilisation: Configuration Livy avancée

## 📌 Cas d'usage 1: JAR avec dépendances supplémentaires

**Scénario**: Votre JAR de rattrapage a besoin de dépendances externes (Apache Commons Lang, Jackson, etc.)

### Configuration .env
```env
LIVY_JARS=hdfs:///user/sddesigner/lib/commons-lang3-3.12.0.jar,hdfs:///user/sddesigner/lib/jackson-databind-2.15.0.jar,hdfs:///user/sddesigner/lib/httpcomponents-client-4.5.jar
LIVY_FILES=
LIVY_ARCHIVES=
LIVY_PY_FILES=
LIVY_CONF={}
```

### Résultat
- Toutes les JARs sont ajoutées au classpath Spark
- Votre code Java peut importer et utiliser ces libraires
- Utile pour éviter "ClassNotFoundException"

---

## 📌 Cas d'usage 2: Configuration Spark avancée

**Scénario**: Vous avez besoin de tuner les performances (shuffle partitions, allocation dynamique, etc.)

### Configuration .env
```env
LIVY_JARS=
LIVY_FILES=
LIVY_ARCHIVES=
LIVY_PY_FILES=
LIVY_CONF={
  "spark.sql.shuffle.partitions": "400",
  "spark.dynamicAllocation.enabled": "true",
  "spark.dynamicAllocation.minExecutors": "2",
  "spark.dynamicAllocation.maxExecutors": "20",
  "spark.shuffle.compress": "true",
  "spark.executor.heartbeatInterval": "60s",
  "spark.sql.adaptive.enabled": "true",
  "spark.broadcast.blockSize": "128m"
}
```

### Résultat
- Spark sera exécuté avec cette configuration
- Amélioration des performances pour les opérations groupées
- Utile pour gérer la mémoire et les ressources

---

## 📌 Cas d'usage 3: Distribution de fichiers de configuration

**Scénario**: Votre JAR a besoin de fichiers de configuration (properties, XML, logs, etc.)

### Configuration .env
```env
LIVY_JARS=
LIVY_FILES=hdfs:///config/app.properties,hdfs:///config/log4j.xml,hdfs:///sql/recovery-queries.sql,hdfs:///data/static-lookup.csv
LIVY_ARCHIVES=
LIVY_PY_FILES=
LIVY_CONF={}
```

### Structure attendue sur Spark
```
$WORK_DIR/
  ├─ app.properties        (depuis LIVY_FILES)
  ├─ log4j.xml             (depuis LIVY_FILES)
  ├─ recovery-queries.sql  (depuis LIVY_FILES)
  └─ static-lookup.csv     (depuis LIVY_FILES)
```

### Code Java/Scala pour accéder
```java
// Les fichiers sont dans le répertoire courant du job
FileInputStream fis = new FileInputStream("app.properties");
Properties props = new Properties();
props.load(fis);
```

### Résultat
- Configuration centralisée et versionnée en HDFS
- Facile à mettre à jour sans recompiler le JAR
- Chaque job obtient la dernière version

---

## 📌 Cas d'usage 4: Archives avec modèles ou données

**Scénario**: Vous avez besoin de distribuer un archive compressée (modèles ML, données statiques, etc.)

### Configuration .env
```env
LIVY_JARS=
LIVY_FILES=hdfs:///config/database.properties
LIVY_ARCHIVES=hdfs:///models/ml-models-2024.tar.gz,hdfs:///data/reference-tables.zip
LIVY_PY_FILES=
LIVY_CONF={}
```

### Structure du .tar.gz
```
ml-models-2024.tar.gz
  └─ models/
      ├─ churn-model.pkl
      ├─ recommendation-model.pkl
      └─ scoring-model.pkl
```

### Structure du .zip
```
reference-tables.zip
  ├─ cities.csv
  ├─ countries.csv
  └─ currencies.csv
```

### Résultat après extraction sur Spark
```
$WORK_DIR/
  ├─ models/
  │   ├─ churn-model.pkl
  │   ├─ recommendation-model.pkl
  │   └─ scoring-model.pkl
  ├─ cities.csv
  ├─ countries.csv
  ├─ currencies.csv
  └─ database.properties
```

---

## 📌 Cas d'usage 5: JAR complet avec toutes les options

**Scénario**: Setup production complet avec toutes les options

### Configuration .env
```env
# Dépendances supplémentaires
LIVY_JARS=hdfs:///lib/commons-lang3-3.12.0.jar,hdfs:///lib/jackson-core-2.15.0.jar,hdfs:///lib/postgresql-42.5.0.jar

# Fichiers de configuration
LIVY_FILES=hdfs:///config/app.properties,hdfs:///config/log4j.xml,hdfs:///config/database-prod.properties,hdfs:///queries/recovery.sql

# Archives compressées
LIVY_ARCHIVES=hdfs:///models/ml-models.tar.gz,hdfs:///data/reference-2024.zip

# Configuration Spark avancée
LIVY_CONF={
  "spark.sql.shuffle.partitions": "500",
  "spark.dynamicAllocation.enabled": "true",
  "spark.dynamicAllocation.minExecutors": "4",
  "spark.dynamicAllocation.maxExecutors": "50",
  "spark.executor.memoryOverhead": "2g",
  "spark.executor.heartbeatInterval": "60s",
  "spark.sql.adaptive.enabled": "true"
}
```

### Exemple d'appel depuis le UI
```
Chemin du JAR: hdfs:///user/sddesigner/recovery-app.jar
Arguments: --date 20240115 --table splio.active --mode parallel
```

### Flux d'exécution complet

1. **Payload Livy créée avec**:
   - 3 JARs ajoutés au classpath
   - 4 fichiers copiés dans le répertoire courant
   - 2 archives extraites
   - Configuration Spark applicée

2. **Spark exécute avec**:
   - 500 partitions pour les shuffles SQL
   - Jusqu'à 50 executors (allocation dynamique)
   - 2GB de mémoire overhead par executor
   - Optimisation adaptative des requêtes

3. **Résultat**: Job robuste et performant

---

## 📌 Cas d'usage 6: Rattrapage PySpark

**Scénario**: Vous avez besoin d'exécuter un script PySpark avec dépendances Python

### Configuration .env
```env
LIVY_JARS=
LIVY_FILES=hdfs:///config/spark-config.properties,hdfs:///data/lookup-tables.csv
LIVY_ARCHIVES=hdfs:///python/packages.zip
LIVY_PY_FILES=hdfs:///python/utils.py,hdfs:///python/transformers.zip
LIVY_CONF={"spark.sql.adaptive.enabled": "true"}
```

### Structure des fichiers Python
```
python/
  ├─ utils.py              (module utilitaire)
  ├─ transformers.zip      (package complet)
  └─ packages.zip          (dépendances pip)
```

### Code du job Spark
```python
# Les fichiers sont dans le path Python
import utils
from transformers import DataTransformer

# Le package est extrait et accessible
import json
config = json.load(open("spark-config.properties"))

# Les fichiers CSV sont accessibles
df = spark.read.csv("lookup-tables.csv", header=True)
```

---

## 📝 Template pour démarrer

Voici un template `.env` minimal pour copier-coller:

```env
# === Configuration Livy avancée ===
# À personnaliser selon vos besoins

# JARs à ajouter au classpath (chaîne CSV)
LIVY_JARS=

# Fichiers à copier (chaîne CSV)
LIVY_FILES=

# Archives à extraire (chaîne CSV)
LIVY_ARCHIVES=

# Fichiers Python pour PySpark (chaîne CSV)
LIVY_PY_FILES=

# Configuration Spark (JSON)
# Exemples:
# - "spark.sql.shuffle.partitions": "200"
# - "spark.dynamicAllocation.enabled": "true"
# - "spark.executor.memoryOverhead": "1g"
LIVY_CONF={}
```

---

## ✅ Checklist avant mise en production

- [ ] Tous les chemins HDFS sont valides (`hdfs:///...`)
- [ ] L'utilisateur `sddesigner` a accès en lecture à tous les chemins
- [ ] Les JSON dans `LIVY_CONF` sont valides (testez avec `python -m json.tool`)
- [ ] Les archives peuvent être extraites sans erreur
- [ ] Les JARs correspondent à la version Java du cluster
- [ ] Les fichiers de configuration sont à jour
- [ ] Vous avez sauvegardé une copie du `.env` (ne commitez PAS sur Git)
- [ ] Le serveur a été redémarré après modification du `.env`
- [ ] Un test de rattrapage a été lancé et s'est bien exécuté

---

## 🔧 Dépannage

### "ClassNotFoundException" quand le JAR s'exécute

**Cause probable**: Dépendance manquante

**Solution**: Ajoutez le JAR dans `LIVY_JARS`

```env
LIVY_JARS=hdfs:///lib/commons-lang3.jar,hdfs:///lib/missing-lib.jar
```

### "FileNotFoundException" dans le code du JAR

**Cause probable**: Fichier de configuration non distribué

**Solution**: Ajoutez le fichier dans `LIVY_FILES`

```env
LIVY_FILES=hdfs:///config/app.properties
```

### Job lent avec beaucoup de données

**Cause probable**: Configuration Spark sous-optimisée

**Solution**: Augmentez les partitions et activez l'allocation dynamique

```env
LIVY_CONF={
  "spark.sql.shuffle.partitions": "500",
  "spark.dynamicAllocation.enabled": "true",
  "spark.dynamicAllocation.maxExecutors": "30"
}
```

### Archive ne s'extrait pas correctement

**Cause probable**: Format d'archive non supporté ou chemin invalide

**Vérifiez**: 
- L'archive existe bien (`hdfs dfs -ls hdfs:///...`)
- Format supporté: `.tar`, `.tar.gz`, `.tgz`, `.zip`
- HDFS n'a pas de problème de permissions


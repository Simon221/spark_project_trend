# 🚀 Quick Start: Configuration Livy avancée

## Avant de commencer

L'implémentation des options avancées Livy est **complète et prête**. Voici comment l'utiliser.

---

## ⚡ 5 minutes pour démarrer

### Étape 1: Vérifiez le `.env`

```bash
cat .env | grep -E "LIVY_|PROXY_USER"
```

Vous devriez voir:
```
PROXY_USER=sddesigner
LIVY_JARS=
LIVY_FILES=
LIVY_ARCHIVES=
LIVY_PY_FILES=
LIVY_CONF={}
```

### Étape 2: Ajoutez vos configurations

Si vous avez besoin de dépendances ou de configurations, éditez le `.env`:

```env
# Exemple: Ajouter une dépendance Java
LIVY_JARS=hdfs:///user/sddesigner/lib/commons-lang3.jar

# Exemple: Ajouter un fichier de config
LIVY_FILES=hdfs:///config/app.properties

# Exemple: Configuration Spark
LIVY_CONF={"spark.sql.shuffle.partitions":"200"}
```

### Étape 3: Redémarrez le serveur

```bash
# Tuer l'ancien serveur
pkill -f "python.*server.py"

# Relancer
python src/api/server.py
```

### Étape 4: Testez

Lancez un rattrapage depuis l'interface web:
1. Allez sur une rapport avec `recovery_needed: true`
2. Cliquez sur "Faire un rattrapage"
3. Entrez le chemin du JAR et les arguments
4. Cliquez "Soumettre"

**Voilà! Vos configurations sont appliquées.**

---

## 📚 Documentation disponible

Après la configuration rapide, consultez:

1. **`LIVY_ADVANCED_CONFIG_GUIDE.md`** ← Pour comprendre chaque option
2. **`EXAMPLES_LIVY_CONFIG.md`** ← Pour des exemples réalistes (6 cas d'usage)
3. **`IMPLEMENTATION_SUMMARY.md`** ← Pour les détails techniques
4. **`VALIDATION.md`** ← Pour vérifier que tout fonctionne

---

## 🎯 Cas courants

### J'ai besoin d'ajouter une dépendance Java
```env
LIVY_JARS=hdfs:///lib/commons-lang3.jar
```

### Je veux distribuer un fichier de config
```env
LIVY_FILES=hdfs:///config/app.properties
```

### Je veux améliorer les performances Spark
```env
LIVY_CONF={"spark.sql.shuffle.partitions":"400","spark.dynamicAllocation.enabled":"true"}
```

### Je veux distribuer un modèle ML (compressé)
```env
LIVY_ARCHIVES=hdfs:///models/ml-models.tar.gz
```

---

## ❓ FAQ rapide

### Q: Où est stockée la configuration?
**R**: Dans le `.env` et chargée au démarrage du serveur

### Q: Faut-il redémarrer après chaque modification?
**R**: Oui, redémarrez le serveur pour charger les nouvelles configs

### Q: Puis-je configurer ça dans l'UI?
**R**: Non, c'est dans le `.env` pour être permanent et versionnabile

### Q: Quelle syntaxe pour les chemins?
**R**: `hdfs:///user/sddesigner/path/to/file` (avec le `///` après hdfs:)

### Q: Puis-je avoir plusieurs JARs?
**R**: Oui, séparez par des virgules: `jar1.jar,jar2.jar,jar3.jar`

### Q: Mon JSON `LIVY_CONF` est invalide, ça casse?
**R**: Non, ça log un warning et utilise `{}` par défaut

---

## 🔧 Architecture (résumé)

```
.env (variables)
  ↓
Config class (parsers)
  ↓
KnoxLivyClient (stockage)
  ↓
submit_jar() (payload)
  ↓
Livy REST API
  ↓
Spark cluster (application)
```

---

## ✅ Checklist pour la production

- [ ] J'ai actualisé le `.env` avec mes chemins HDFS réels
- [ ] J'ai testé que les chemins existent: `hdfs dfs -ls hdfs:///...`
- [ ] L'utilisateur `sddesigner` a accès en lecture aux fichiers
- [ ] Mon JSON `LIVY_CONF` est valide (testé avec Python)
- [ ] J'ai redémarré le serveur après modification du `.env`
- [ ] J'ai testé un rattrapage et il fonctionne
- [ ] Je n'ai pas commité le `.env` en Git (contient des secrets)

---

## 📞 Besoin d'aide?

Consultez les guides:
- **Quick help**: Ce fichier (vous êtes ici)
- **Configuration**: `LIVY_ADVANCED_CONFIG_GUIDE.md`
- **Exemples**: `EXAMPLES_LIVY_CONFIG.md`
- **Technique**: `IMPLEMENTATION_SUMMARY.md`
- **Validation**: `VALIDATION.md`

---

## 🎉 C'est tout!

La configuration avancée Livy est maintenant complète et intégrée. Vous pouvez:

✅ Ajouter des JARs au classpath
✅ Distribuer des fichiers de config
✅ Extraire des archives
✅ Configurer Spark avancément
✅ Supporter PySpark si besoin

**Bonne utilisation!** 🚀


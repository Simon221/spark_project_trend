#!/bin/bash

# Script de démarrage du serveur Spark Trend Analyzer (Nouvelle architecture)

echo "========================================"
echo "Spark Trend Analyzer API v1.0.0"
echo "========================================"

# Obtenir le répertoire de script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Vérifier que .env existe
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/config/.env" ]; then
        echo "📁 Utilisation de .env depuis config/"
        export $(cat "$PROJECT_ROOT/config/.env" | grep -v '^#' | xargs)
    else
        echo "❌ Erreur: Fichier .env non trouvé"
        echo "Créez un fichier .env basé sur config/.env.example"
        exit 1
    fi
else
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# Vérifier que les dépendances sont installées
echo "🔍 Vérification des dépendances..."
python -c "import fastapi, langchain, langchain_openai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Les dépendances ne sont pas installées"
    echo "Installation en cours..."
    
    REQUIREMENTS_FILE="$PROJECT_ROOT/requirements-openai.txt"
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        REQUIREMENTS_FILE="$PROJECT_ROOT/config/requirements-openai.txt"
    fi
    
    pip install -r "$REQUIREMENTS_FILE"
fi

# Vérifier les variables essentielles
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Erreur: OPENAI_API_KEY non configurée dans .env"
    exit 1
fi

if [ -z "$KNOX_HOST" ]; then
    echo "⚠️  Attention: KNOX_HOST non configurée (fonctionnalité limitée)"
fi

echo "✅ Configuration vérifiée"
echo "📝 OPENAI_API_KEY: $(echo $OPENAI_API_KEY | cut -c1-20)..."
[ -n "$KNOX_HOST" ] && echo "🔐 KNOX_HOST: $KNOX_HOST"
echo ""

# Changer vers le répertoire du projet
cd "$PROJECT_ROOT"

# Lancer le serveur
echo "🚀 Démarrage du serveur uvicorn sur http://localhost:8000"
echo "📡 Interface web: http://localhost:8000/ui"
echo "📚 Documentation API: http://localhost:8000/docs"
echo ""
echo "Appuyez sur CTRL+C pour arrêter le serveur"
echo ""

python main.py

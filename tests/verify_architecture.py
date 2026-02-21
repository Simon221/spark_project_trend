#!/usr/bin/env python3
"""
Vérification complète de la nouvelle structure architecturale
"""

import sys
import os
from pathlib import Path

# Ajouter le root au path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_structure():
    """Vérifier la structure des répertoires"""
    print("🔍 Vérification de la structure...")
    
    required_dirs = [
        "src",
        "src/api",
        "src/agents",
        "src/models",
        "src/utils",
        "frontend",
        "docs",
        "config",
        "scripts",
        "tests"
    ]
    
    for dir_path in required_dirs:
        full_path = PROJECT_ROOT / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ NOT FOUND")
            return False
    
    return True


def check_python_files():
    """Vérifier les fichiers Python importants"""
    print("\n🐍 Vérification des fichiers Python...")
    
    required_files = {
        "src/__init__.py": "src",
        "src/api/__init__.py": "api",
        "src/api/server.py": "API server",
        "src/agents/__init__.py": "agents",
        "src/agents/trend_analyzer.py": "Trend analyzer",
        "src/agents/livy_client.py": "Livy client",
        "src/models/__init__.py": "models",
        "src/models/config.py": "Configuration",
        "src/utils/__init__.py": "utils",
        "src/utils/logger.py": "Logger",
        "src/utils/serializers.py": "Serializers",
        "main.py": "Main entry point",
        "setup.py": "Setup configuration",
        "pyproject.toml": "PEP 518 config"
    }
    
    for file_path, description in required_files.items():
        full_path = PROJECT_ROOT / file_path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path} ({size} bytes) - {description}")
        else:
            print(f"  ✗ {file_path} NOT FOUND")
            return False
    
    return True


def check_imports():
    """Vérifier les imports Python"""
    print("\n📦 Vérification des imports...")
    
    imports_to_check = [
        ("src.models.config", "Config"),
        ("src.utils.logger", "setup_logger"),
        ("src.utils.serializers", "make_json_serializable"),
        ("src.agents", "KnoxLivyClient"),
        ("src.agents", "analyze_trend"),
        ("src.api", "app"),
    ]
    
    for module, symbol in imports_to_check:
        try:
            mod = __import__(module, fromlist=[symbol])
            obj = getattr(mod, symbol)
            print(f"  ✓ from {module} import {symbol}")
        except Exception as e:
            print(f"  ✗ from {module} import {symbol} - ERROR: {e}")
            return False
    
    return True


def check_config():
    """Vérifier la configuration"""
    print("\n⚙️  Vérification de la configuration...")
    
    try:
        from src.models.config import Config
        
        checks = [
            ("KNOX_HOST", Config.KNOX_HOST),
            ("DRIVER_MEMORY", Config.DRIVER_MEMORY),
            ("LLM_MODEL", Config.LLM_MODEL),
            ("TREND_THRESHOLDS", Config.TREND_THRESHOLDS),
            ("TABLE_SCHEMAS", Config.TABLE_SCHEMAS),
        ]
        
        for name, value in checks:
            if value:
                print(f"  ✓ Config.{name}")
            else:
                print(f"  ⚠️  Config.{name} (not configured)")
        
        return True
    except Exception as e:
        print(f"  ✗ Config check failed: {e}")
        return False


def check_frontend():
    """Vérifier les fichiers frontend"""
    print("\n🎨 Vérification du frontend...")
    
    frontend_files = [
        "frontend/index_knox.html",
        "frontend/config.js",
    ]
    
    for file_path in frontend_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path} ({size} bytes)")
        else:
            print(f"  ⚠️  {file_path} not found (optional)")
    
    return True


def check_documentation():
    """Vérifier la documentation"""
    print("\n📚 Vérification de la documentation...")
    
    doc_files = [
        "docs/README.md",
        "docs/QUICKSTART.md",
        "docs/SETUP.md",
        "ARCHITECTURE_REORGANIZATION.md",
        "README_ARCHITECTURE.md",
    ]
    
    found = 0
    for file_path in doc_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path} ({size} bytes)")
            found += 1
        else:
            print(f"  ⚠️  {file_path} not found")
    
    return found >= 3


def check_scripts():
    """Vérifier les scripts"""
    print("\n🔧 Vérification des scripts...")
    
    scripts = [
        "scripts/start.sh",
        "scripts/commands.sh",
    ]
    
    for script_path in scripts:
        full_path = PROJECT_ROOT / script_path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            is_executable = os.access(full_path, os.X_OK)
            exec_marker = "✓" if is_executable else "⚠️ "
            print(f"  {exec_marker} {script_path} ({size} bytes)")
        else:
            print(f"  ✗ {script_path} not found")
    
    return True


def main():
    """Exécuter toutes les vérifications"""
    print("=" * 60)
    print("VÉRIFICATION DE LA NOUVELLE ARCHITECTURE")
    print("=" * 60)
    
    checks = [
        ("Structure des répertoires", check_structure),
        ("Fichiers Python", check_python_files),
        ("Imports Python", check_imports),
        ("Configuration", check_config),
        ("Frontend", check_frontend),
        ("Documentation", check_documentation),
        ("Scripts", check_scripts),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n❌ ERREUR lors de la vérification {check_name}: {e}")
            results.append((check_name, False))
    
    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print(f"\nTotal: {passed}/{total} vérifications réussies")
    
    if passed == total:
        print("\n🎉 ARCHITECTURE VALIDÉE AVEC SUCCÈS!")
        print("\n📝 Prochaines étapes:")
        print("  1. Éditer .env avec vos paramètres")
        print("  2. Installer les dépendances: pip install -r config/requirements-openai.txt")
        print("  3. Lancer l'application: ./scripts/start.sh ou python main.py")
        print("  4. Accéder à http://localhost:8000/ui")
        return 0
    else:
        print(f"\n❌ {total - passed} vérification(s) échouée(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

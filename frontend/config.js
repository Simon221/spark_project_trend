// Configuration Frontend - Spark Trend Analyzer
// À placer dans le dossier static/ ou à charger avant le script React

const CONFIG = {
  // API Configuration
  API: {
    BASE_URL: 'http://localhost:8000',
    VERSION: 'v1',
    TIMEOUT: 30000 // 30 secondes
  },
  
  // UI Configuration
  UI: {
    AUTO_REFRESH: 5000, // Mise à jour tous les 5 secondes
    MAX_JOBS_DISPLAYED: 20,
    THEME: 'orange' // couleur principale
  },
  
  // Spark Configuration par défaut
  SPARK_DEFAULTS: {
    driverMemory: '4g',
    driverCores: 2,
    executorMemory: '4g',
    executorCores: 2,
    numExecutors: 4,
    queue: 'root.datalake'
  },
  
  // Exemples de prompts
  EXAMPLES: [
    "Vérifie les tendances de splio.users pour le 20260127",
    "Compare splio.active du 20260127 avec les 7 derniers jours",
    "Analyse le nombre d'utilisateurs actifs et les emails uniques"
  ]
};

// Export pour les modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}

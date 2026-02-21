"""
Plateforme d'Analyse de Tendances Spark avec LangChain Agent
Utilise Apache Livy pour exécuter des requêtes Spark et analyser les tendances
"""

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timedelta
import logging

from .livy_client import KnoxLivyClient
from ..models.config import Config

logger = logging.getLogger(__name__)


# ============================================
# LANGCHAIN TOOLS
# ============================================

class QueryGeneratorInput(BaseModel):
    """Input pour le générateur de requêtes"""
    table_name: str = Field(..., description="Nom complet de la table (ex: splio.active)")
    target_date: str = Field(..., description="Date cible au format YYYYMMDD")
    reference_date: Optional[str] = Field(None, description="Date de référence (optionnel, sinon J-7)")
    metrics: Optional[List[str]] = Field(None, description="Métriques spécifiques à calculer (optionnel)")


class SparkQueryGeneratorTool(BaseTool):
    """Tool pour générer des requêtes SQL Spark optimisées"""
    
    name: str = "spark_query_generator"
    description: str = """
    Génère des requêtes SQL Spark pour analyser les tendances d'une table.
    Input: table_name (ex: splio.users), target_date (YYYYMMDD), 
           reference_date (optionnel, sinon J-7), metrics (optionnel)
    Output: Dictionnaire avec query_target et query_reference
    """
    args_schema: type[BaseModel] = QueryGeneratorInput
    
    def _run(self, table_name: str, target_date: str, 
             reference_date: Optional[str] = None,
             metrics: Optional[List[str]] = None) -> Dict[str, str]:
        """Génère les requêtes SQL"""
        
        # Nettoyer les inputs (en cas de passage JSON)
        if isinstance(table_name, str) and table_name.strip().startswith('{'):
            try:
                import json
                data = json.loads(table_name)
                table_name = data.get('table_name', table_name)
                target_date = data.get('target_date', target_date)
                reference_date = data.get('reference_date', reference_date)
                metrics = data.get('metrics', metrics)
            except:
                pass  # Garder les valeurs originales
        
        logger.info(f"Génération requêtes: table={table_name}, target={target_date}")
        
        # Calculer la date de référence si non fournie (J-7)
        if not reference_date:
            target_dt = datetime.strptime(target_date, "%Y%m%d")
            ref_dt = target_dt - timedelta(days=7)
            reference_date = ref_dt.strftime("%Y%m%d")
        
        # Récupérer les métriques par défaut si non fournies
        if not metrics:
            schema_info = Config.TABLE_SCHEMAS.get(table_name, {})
            metrics = schema_info.get("metrics", ["COUNT(*) as cnt"])
        
        # Construire les requêtes
        metrics_str = ", ".join(metrics)
        
        query_target = f"""
SELECT 
    '{target_date}' as date,
    {metrics_str}
FROM {table_name}
WHERE day = '{target_date}'
        """.strip()
        
        query_reference = f"""
SELECT 
    '{reference_date}' as date,
    {metrics_str}
FROM {table_name}
WHERE day = '{reference_date}'
        """.strip()
        
        logger.info(f"Requête cible: {query_target[:80]}...")
        
        return {
            "query_target": query_target,
            "query_reference": query_reference,
            "target_date": target_date,
            "reference_date": reference_date
        }


class SparkExecutorInput(BaseModel):
    """Input pour l'exécuteur Spark"""
    sql_query: str = Field(description="Requête SQL à exécuter")


class LivySparkExecutorTool(BaseTool):
    """Tool pour exécuter des requêtes Spark via Livy Knox"""
    
    name: str = "livy_spark_executor"
    description: str = """
    Exécute une requête SQL sur Spark via Apache Livy + Knox Gateway.
    Input: sql_query (requête SQL complète)
    Output: Résultats de la requête au format JSON
    """
    args_schema: type[BaseModel] = SparkExecutorInput
    livy_client: KnoxLivyClient = None
    
    def __init__(self):
        super().__init__()
        self.livy_client = KnoxLivyClient(
            knox_host=Config.KNOX_HOST,
            ad_user=Config.AD_USER,
            ad_password=Config.AD_PASSWORD,
            driver_memory=Config.DRIVER_MEMORY,
            driver_cores=Config.DRIVER_CORES,
            executor_memory=Config.EXECUTOR_MEMORY,
            executor_cores=Config.EXECUTOR_CORES,
            num_executors=Config.NUM_EXECUTORS,
            queue=Config.QUEUE
        )
    
    def _run(self, sql_query: str) -> Dict[str, Any]:
        """Exécute la requête SQL"""
        try:
            logger.info(f"Exécution SQL: {sql_query[:100]}...")
            
            if not hasattr(self, 'livy_client') or not self.livy_client:
                from .livy_client import KnoxLivyClient
                self.livy_client = KnoxLivyClient(
                    knox_host=Config.KNOX_HOST,
                    ad_user=Config.AD_USER,
                    ad_password=Config.AD_PASSWORD
                )
            
            result = self.livy_client.execute_sql(sql_query)
            logger.info(f"✓ Résultat: {result.get('count', 0)} lignes")
            return result
        except Exception as e:
            logger.error(f"Erreur SQL: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class TrendAnalyzerInput(BaseModel):
    """Input pour l'analyseur de tendances"""
    target_data: Dict = Field(description="Données de la date cible")
    reference_data: Dict = Field(description="Données de la date de référence")


class TrendAnalyzerTool(BaseTool):
    """Tool pour analyser les tendances entre deux jeux de données"""
    
    name: str = "trend_analyzer"
    description: str = """
    Analyse les tendances en comparant les données cibles avec les données de référence.
    Input: target_data et reference_data (résultats de requêtes Spark)
    Output: Analyse détaillée avec variations, alertes et verdict
    """
    args_schema: type[BaseModel] = TrendAnalyzerInput
    
    def _run(self, target_data: Dict, reference_data: Dict) -> Dict[str, Any]:
        """Analyse les tendances"""
        
        if not target_data.get("success") or not reference_data.get("success"):
            return {
                "success": False,
                "error": "Données invalides"
            }
        
        target_rows = target_data.get("data", [])
        ref_rows = reference_data.get("data", [])
        
        if not target_rows or not ref_rows:
            return {
                "success": False,
                "error": "Pas de données à comparer"
            }
        
        # Comparer toutes les métriques numériques
        target_metrics = target_rows[0]
        ref_metrics = ref_rows[0]
        
        analysis = {
            "success": True,
            "comparisons": [],
            "alerts": [],
            "verdict": "neutral"
        }
        
        severity_score = 0
        
        for key in target_metrics:
            if key == "date":
                continue
            
            try:
                target_val = float(target_metrics[key])
                ref_val = float(ref_metrics[key])
                
                if ref_val == 0:
                    continue
                
                variation = (target_val - ref_val) / ref_val
                variation_pct = variation * 100
                
                comparison = {
                    "metric": key,
                    "target_value": target_val,
                    "reference_value": ref_val,
                    "variation": variation,
                    "variation_pct": f"{variation_pct:.2f}%"
                }
                
                # Vérifier les seuils
                thresholds = Config.TREND_THRESHOLDS.get("volume", {})
                
                if variation < thresholds.get("critical", -0.25):
                    comparison["alert"] = "CRITICAL"
                    severity_score += 3
                    analysis["alerts"].append(f"🔴 {key}: {variation_pct:.1f}% (critique)")
                elif variation < thresholds.get("warning", -0.10):
                    comparison["alert"] = "WARNING"
                    severity_score += 1
                    analysis["alerts"].append(f"🟠 {key}: {variation_pct:.1f}% (attention)")
                elif variation > 0.05:
                    comparison["alert"] = "POSITIVE"
                    analysis["alerts"].append(f"🟢 {key}: +{variation_pct:.1f}% (positif)")
                else:
                    comparison["alert"] = "NORMAL"
                
                analysis["comparisons"].append(comparison)
                
            except (ValueError, TypeError):
                continue
        
        # Déterminer le verdict global
        if severity_score >= 3:
            analysis["verdict"] = "negative"
            analysis["recommendation"] = "Rattrapage recommandé"
        elif severity_score >= 1:
            analysis["verdict"] = "warning"
            analysis["recommendation"] = "Surveillance nécessaire"
        elif any(c.get("alert") == "POSITIVE" for c in analysis["comparisons"]):
            analysis["verdict"] = "positive"
            analysis["recommendation"] = "Tendance favorable"
        else:
            analysis["verdict"] = "stable"
            analysis["recommendation"] = "Situation normale"
        
        return analysis


class RecoveryProposerInput(BaseModel):
    """Input pour le proposeur de rattrapage"""
    trend_analysis: Dict = Field(description="Résultats de l'analyse de tendance")


class RecoveryProposerTool(BaseTool):
    """Tool pour proposer des actions de rattrapage"""
    
    name: str = "recovery_proposer"
    description: str = """
    Propose des actions de rattrapage basées sur l'analyse des tendances.
    Input: trend_analysis (résultats du TrendAnalyzer)
    Output: Plan d'action détaillé avec étapes concrètes
    """
    args_schema: type[BaseModel] = RecoveryProposerInput
    
    def _run(self, trend_analysis: Dict) -> Dict[str, Any]:
        """Propose un plan de rattrapage"""
        
        verdict = trend_analysis.get("verdict", "neutral")
        
        if verdict not in ["negative", "warning"]:
            return {
                "recovery_needed": False,
                "message": "Aucun rattrapage nécessaire"
            }
        
        # Analyser les métriques problématiques
        comparisons = trend_analysis.get("comparisons", [])
        critical_metrics = [c for c in comparisons if c.get("alert") == "CRITICAL"]
        warning_metrics = [c for c in comparisons if c.get("alert") == "WARNING"]
        
        actions = []
        
        # Actions pour métriques critiques
        if critical_metrics:
            actions.append({
                "priority": "HIGH",
                "action": "Relancer les jobs de traitement",
                "details": f"Métriques critiques: {', '.join(m['metric'] for m in critical_metrics)}",
                "steps": [
                    "1. Vérifier les logs des jobs Spark",
                    "2. Identifier les partitions échouées",
                    "3. Relancer avec '--conf spark.speculation=true'",
                    "4. Monitorer l'exécution"
                ]
            })
            
            actions.append({
                "priority": "HIGH",
                "action": "Vérifier les sources de données",
                "details": "Possible problème upstream",
                "steps": [
                    "1. Valider la disponibilité des sources",
                    "2. Vérifier les timestamps d'ingestion",
                    "3. Comparer avec les jours précédents"
                ]
            })
        
        # Actions pour warnings
        if warning_metrics:
            actions.append({
                "priority": "MEDIUM",
                "action": "Ajuster les paramètres de traitement",
                "details": f"Optimisation nécessaire pour: {', '.join(m['metric'] for m in warning_metrics)}",
                "steps": [
                    "1. Analyser les métriques Spark (shuffle, GC)",
                    "2. Ajuster le parallélisme",
                    "3. Optimiser les jointures si nécessaire"
                ]
            })
        
        # Action de surveillance
        actions.append({
            "priority": "LOW",
            "action": "Activer la surveillance renforcée",
            "details": "Monitoring continu jusqu'à résolution",
            "steps": [
                "1. Configurer des alertes sur les métriques",
                "2. Vérifier les tendances toutes les heures",
                "3. Escalader si dégradation continue"
            ]
        })
        
        return {
            "recovery_needed": True,
            "severity": verdict,
            "actions": actions,
            "summary": f"{len(actions)} actions proposées ({len(critical_metrics)} critiques, {len(warning_metrics)} warnings)"
        }


class RecoveryExecutorInput(BaseModel):
    """Input pour l'exécuteur de rattrapage"""
    table_name: str = Field(..., description="Nom de la table à rattraper")
    target_date: str = Field(..., description="Date à rattraper (YYYYMMDD)")
    jar_args: Optional[List[str]] = Field(None, description="Arguments additionnels pour le JAR (optionnel)")


class RecoveryExecutorTool(BaseTool):
    """Tool pour exécuter le JAR de rattrapage"""
    
    name: str = "recovery_executor"
    description: str = """
    Exécute le JAR de rattrapage pour retraiter des données.
    Input: table_name, target_date, jar_args (optionnel)
    Output: Résultat de l'exécution du JAR
    """
    args_schema: type[BaseModel] = RecoveryExecutorInput
    livy_client: KnoxLivyClient = None
    
    def __init__(self):
        super().__init__()
        self.livy_client = KnoxLivyClient(
            knox_host=Config.KNOX_HOST,
            ad_user=Config.AD_USER,
            ad_password=Config.AD_PASSWORD,
            driver_memory=Config.DRIVER_MEMORY,
            driver_cores=Config.DRIVER_CORES,
            executor_memory=Config.EXECUTOR_MEMORY,
            executor_cores=Config.EXECUTOR_CORES,
            num_executors=Config.NUM_EXECUTORS,
            queue=Config.QUEUE
        )
    
    def _run(
        self,
        table_name: str,
        target_date: str,
        jar_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Exécute le rattrapage"""
        try:
            # Préparer les arguments pour le JAR
            args = jar_args or []
            args.extend([table_name, target_date])
            
            # Exécuter le JAR
            result = self.livy_client.execute_jar(
                jar_path=Config.RECOVERY_JAR_PATH,
                args=args,
                main_class=Config.RECOVERY_JAR_CLASS
            )
            
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# ============================================
# AGENT PRINCIPAL
# ============================================

def create_trend_analysis_agent():
    """Crée l'agent d'analyse de tendances"""
    
    # Initialiser les tools
    tools = [
        SparkQueryGeneratorTool(),
        LivySparkExecutorTool(),
        TrendAnalyzerTool(),
        RecoveryProposerTool(),
        RecoveryExecutorTool()
    ]
    
    # Template du prompt pour l'agent - Format REACT strict
    template = """Tu es un expert en analyse de données Spark pour Orange Sonatel.
    
Tu dois analyser les tendances des données et proposer des actions de rattrapage si nécessaire.

Outils disponibles:
{tools}

Noms des outils: {tool_names}

Instructions strictes:
1. Utilise spark_query_generator pour créer les requêtes SQL Spark
2. Exécute les requêtes avec livy_spark_executor (cible, puis référence)
3. Analyse les résultats avec trend_analyzer
4. Si tendance négative, propose actions avec recovery_proposer

IMPORTANT: Pour chaque utilisation d'outil:
- Affiche exactement: Action: [nom_outil]
- Puis: Action Input: [json valide avec tous les paramètres]
- Attends le résultat entre <TOOL_RESULT> et </TOOL_RESULT>

Question utilisateur: {input}

Pensée: {agent_scratchpad}"""
    
    prompt = PromptTemplate.from_template(template)
    
    # LLM - OpenAI GPT-4o
    llm = ChatOpenAI(
        model=Config.LLM_MODEL,
        temperature=Config.LLM_TEMPERATURE,
        openai_api_key=Config.OPENAI_API_KEY
    )
    
    # Créer l'agent REACT
    agent = create_react_agent(llm, tools, prompt)
    
    # Créer l'executor avec meilleure gestion des erreurs
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=15,
        handle_parsing_errors="Invalid Format: Missing 'Action Input:' after 'Action:'"
    )
    
    return agent_executor


# ============================================
# FONCTION PRINCIPALE
# ============================================

def analyze_trend(user_prompt: str) -> Dict[str, Any]:
    """
    Fonction principale pour analyser les tendances
    
    Args:
        user_prompt: Prompt utilisateur (ex: "Analyse table=splio.active date=20260127" 
                     ou '{"table_name": "splio.active", "target_date": "20260127"}')
    
    Returns:
        Résultats de l'analyse avec recommandations
    """
    
    agent = create_trend_analysis_agent()
    
    try:
        # Parser le prompt pour extraire les paramètres directs
        logger.info(f"Analyse du prompt: {user_prompt[:100]}")
        
        table_name = None
        target_date = None
        
        # Essayer de parser comme JSON d'abord
        try:
            if user_prompt.strip().startswith('{'):
                data = json.loads(user_prompt)
                table_name = data.get('table_name', data.get('table'))
                target_date = data.get('target_date', data.get('date'))
                logger.info(f"✓ Parsé comme JSON: table={table_name}, date={target_date}")
        except Exception as e:
            logger.debug(f"Pas du JSON valide: {e}")
        
        # Si pas de JSON, essayer le format texte "Analyse table=... date=..."
        if not table_name or not target_date:
            import re
            table_match = re.search(r'table[=:\s]+([^\s,}]+)', user_prompt, re.IGNORECASE)
            date_match = re.search(r'date[=:\s]+(\d{8})', user_prompt, re.IGNORECASE)
            
            if table_match:
                table_name = table_match.group(1).strip('"\',{}')
            if date_match:
                target_date = date_match.group(1)
            
            if table_name and target_date:
                logger.info(f"✓ Parsé comme texte: table={table_name}, date={target_date}")
        
        # Si on a les paramètres, exécuter directement
        if table_name and target_date:
            logger.info(f"Exécution directe: table={table_name}, date={target_date}")
            return execute_direct_analysis(table_name, target_date)
        
        # Sinon utiliser l'agent
        logger.info("Format non reconnu, utilisation de l'agent")
        result = agent.invoke({"input": user_prompt})
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Erreur analyse: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def execute_direct_analysis(table_name: str, target_date: str) -> Dict[str, Any]:
    """
    Exécute l'analyse directement sans passer par l'agent
    
    Basé sur le workflow du script bash livy_v2.sh
    """
    logger.info(f"Exécution directe: {table_name} / {target_date}")
    
    try:
        # 1. Générer les requêtes SQL
        qg = SparkQueryGeneratorTool()
        queries = qg._run(table_name, target_date)
        
        if not queries.get("query_target"):
            return {"success": False, "error": "Impossible de générer les requêtes"}
        
        logger.info("✓ Requêtes générées")
        
        # 2. Initialiser le client Livy
        from .livy_client import KnoxLivyClient
        livy = KnoxLivyClient(
            knox_host=Config.KNOX_HOST,
            ad_user=Config.AD_USER,
            ad_password=Config.AD_PASSWORD,
            driver_memory=Config.DRIVER_MEMORY,
            driver_cores=Config.DRIVER_CORES,
            executor_memory=Config.EXECUTOR_MEMORY,
            executor_cores=Config.EXECUTOR_CORES,
            num_executors=Config.NUM_EXECUTORS,
            queue=Config.QUEUE
        )
        
        # 3. Créer la session Livy (attends idle)
        session_id = livy.create_session()
        logger.info(f"✓ Session créée: {session_id}")
        
        # 4. Exécuter les requêtes cible et référence
        target_data = livy.execute_sql(queries["query_target"])
        logger.info(f"✓ Requête cible exécutée: {target_data.get('count', 0)} lignes")
        
        ref_data = livy.execute_sql(queries["query_reference"])
        logger.info(f"✓ Requête référence exécutée: {ref_data.get('count', 0)} lignes")
        
        # 5. Analyser les tendances
        ta = TrendAnalyzerTool()
        analysis = ta._run(target_data, ref_data)
        logger.info(f"✓ Analyse complétée: verdict={analysis.get('verdict')}")
        
        # 6. Proposer des actions si nécessaire
        if analysis.get("verdict") in ["negative", "warning"]:
            rp = RecoveryProposerTool()
            recovery = rp._run(analysis)
            analysis["recovery_plan"] = recovery
            logger.info(f"✓ Plan de rattrapage proposé")
        
        # 7. Nettoyer la session
        livy.close_session()
        logger.info("✓ Session fermée")
        
        return {
            "success": True,
            "table_name": table_name,
            "target_date": target_date,
            "queries": queries,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Erreur exécution directe: {e}")
        return {
            "success": False,
            "error": str(e)
        }

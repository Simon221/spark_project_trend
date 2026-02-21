"""
Client Livy adapté pour Knox Gateway avec authentification LDAP
Compatible avec le système Sonatel/Orange
"""

import requests
import time
import json
from typing import Dict, Any, Optional, List
from urllib3.exceptions import InsecureRequestWarning
import logging

# Désactiver les warnings SSL pour Knox
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)


class KnoxLivyClient:
    """Client pour interagir avec Livy via Knox Gateway"""
    
    def __init__(
        self,
        knox_host: str,
        ad_user: str,
        ad_password: str,
        driver_memory: str = "4g",
        driver_cores: int = 2,
        executor_memory: str = "4g",
        executor_cores: int = 2,
        num_executors: int = 4,
        queue: str = "root.datalake",
        proxy_user: str = None,
        heartbeat_timeout_in_second: int = 0,
        conf: Dict[str, Any] = None,
        archives: List[str] = None,
        files: List[str] = None,
        jars: List[str] = None,
        py_files: List[str] = None
    ):
        self.knox_host = knox_host
        self.ad_user = ad_user
        self.ad_password = ad_password
        self.base_url = f"https://{knox_host}/gateway/cdp-proxy-api/livy/v1"
        
        # Configuration Spark
        self.driver_memory = driver_memory
        self.driver_cores = driver_cores
        self.executor_memory = executor_memory
        self.executor_cores = executor_cores
        self.num_executors = num_executors
        self.queue = queue
        self.proxy_user = proxy_user or ad_user
        self.heartbeat_timeout_in_second = heartbeat_timeout_in_second
        self.conf = conf or {}
        self.archives = archives or []
        self.files = files or []
        self.jars = jars or []
        self.py_files = py_files or []
        
        self.session_id = None
        self.auth = (ad_user, ad_password)
        self.headers = {
            'Content-Type': 'application/json',
            'X-Requested-By': 'hive'
        }
    
    def create_session(self, kind: str = "spark") -> int:
        """Crée une session Spark via Livy"""
        logger.info("=== Création de la session Spark ===")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"User: {self.ad_user}")
        
        payload = {
            "kind": kind,
            "proxyUser": self.proxy_user,
            "driverMemory": self.driver_memory,
            "driverCores": self.driver_cores,
            "executorMemory": self.executor_memory,
            "executorCores": self.executor_cores,
            "numExecutors": self.num_executors,
            "queue": self.queue,
            "heartbeatTimeoutInSecond": self.heartbeat_timeout_in_second
        }
        
        # Ajouter les paramètres optionnels s'ils sont fournis
        if self.conf:
            payload["conf"] = self.conf
        if self.archives:
            payload["archives"] = self.archives
        if self.files:
            payload["files"] = self.files
        if self.jars:
            payload["jars"] = self.jars
        if self.py_files:
            payload["pyFiles"] = self.py_files
        
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = None
        try:
            logger.info(f"POST à {self.base_url}/sessions")
            response = requests.post(
                f"{self.base_url}/sessions",
                json=payload,
                headers=self.headers,
                auth=self.auth,
                verify=False,
                timeout=30
            )
            
            logger.info(f"Status HTTP: {response.status_code}")
            logger.info(f"Réponse brute: {response.text}")
            
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur requête HTTP: {e}")
            if response is not None:
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Headers: {dict(response.headers)}")
                logger.error(f"   Body: {response.text}")
            raise Exception(f"Impossible de créer la session: {e}")
        
        try:
            data = response.json()
            logger.info(f"Réponse JSON: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON: {e}")
            logger.error(f"   Réponse brute: {response.text}")
            raise Exception(f"Réponse Livy invalide (non-JSON): {response.text}")
        
        self.session_id = data.get("id")
        
        if not self.session_id:
            logger.error(f"❌ Pas d'ID de session dans la réponse!")
            logger.error(f"   Keys disponibles: {list(data.keys())}")
            logger.error(f"   Réponse complète: {data}")
            raise Exception(f"Impossible d'obtenir l'ID de session. Réponse: {data}")
        
        logger.info(f"✓ Session créée: {self.session_id}")
        
        # Attendre que la session soit prête
        self._wait_for_session()
        
        return self.session_id
    
    def _wait_for_session(self, timeout: int = 120):
        """Attend que la session soit prête"""
        logger.info(f"Attente de la session (timeout: {timeout}s)...")
        
        start_time = time.time()
        wait_interval = 5
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/sessions/{self.session_id}",
                    headers=self.headers,
                    auth=self.auth,
                    verify=False,
                    timeout=30
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️  Erreur GET session: {e}")
                time.sleep(wait_interval)
                continue
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  Erreur JSON session: {e}")
                time.sleep(wait_interval)
                continue
            
            state = data.get("state", "unknown")
            
            elapsed = time.time() - start_time
            logger.info(f"  [{elapsed:.0f}s] État session {self.session_id}: {state}")
            
            if state == "idle":
                logger.info("✓ Session idle! Attente supplémentaire de 2s pour être sûr...")
                time.sleep(2)  # Délai supplémentaire pour que la session soit VRAIMENT prête
                
                # Valider que la session est toujours accessible
                try:
                    verify_response = requests.get(
                        f"{self.base_url}/sessions/{self.session_id}",
                        headers=self.headers,
                        auth=self.auth,
                        verify=False,
                        timeout=30
                    )
                    verify_data = verify_response.json()
                    final_state = verify_data.get("state", "unknown")
                    logger.info(f"✓ Session validée! État final: {final_state}")
                    return
                except Exception as e:
                    logger.error(f"❌ Erreur validation session: {e}")
                    raise Exception(f"Session créée mais devient inaccessible: {e}")
                    
            elif state in ["error", "dead", "killed"]:
                error = data.get("error", state)
                logger.error(f"❌ Session échouée: {error}")
                raise Exception(f"Session échouée: {state}")
            
            time.sleep(wait_interval)
        
        logger.error(f"❌ Timeout après {timeout}s d'attente")
        raise TimeoutError("Timeout lors de l'attente de la session")
    
    def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """Exécute une requête SQL via Livy"""
        if not self.session_id:
            self.create_session()
        
        logger.info(f"=== Exécution SQL avec session {self.session_id} ===")
        logger.info(f"Requête SQL: {sql_query[:200]}...")
        logger.info(f"Requête complète:\n{sql_query}")
        
        # Valider que la session est toujours active AVANT de soumettre
        try:
            session_check = requests.get(
                f"{self.base_url}/sessions/{self.session_id}",
                headers=self.headers,
                auth=self.auth,
                verify=False,
                timeout=30
            )
            session_data = session_check.json()
            session_state = session_data.get("state", "unknown")
            logger.info(f"État session avant statement: {session_state}")
            
            if session_state != "idle":
                logger.warning(f"⚠️  Session n'est pas idle: {session_state}")
                if session_state in ["error", "dead", "killed"]:
                    raise Exception(f"Session n'est plus valide: {session_state}")
        except Exception as e:
            logger.error(f"❌ Erreur vérification session: {e}")
            raise
        
        # Normaliser la requête en une seule ligne pour éviter les problèmes avec les newlines
        normalized_query = ' '.join(sql_query.split())
        
        # Code Scala: .show() fonctionne et retourne une table ASCII formatée
        code = f'spark.sql("{normalized_query}").show()'
        
        payload = {"code": code}
        
        logger.info(f"Code Scala à exécuter:\n{code}")
        
        response = None
        try:
            logger.info(f"POST à {self.base_url}/sessions/{self.session_id}/statements")
            response = requests.post(
                f"{self.base_url}/sessions/{self.session_id}/statements",
                json=payload,
                headers=self.headers,
                auth=self.auth,
                verify=False,
                timeout=30
            )
            
            logger.info(f"Status HTTP: {response.status_code}")
            logger.info(f"Réponse brute: {response.text[:500]}")
            
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur requête HTTP: {e}")
            if response is not None:
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Headers: {dict(response.headers)}")
                logger.error(f"   Body: {response.text}")
            raise Exception(f"Erreur lors de la soumission du statement: {e}")
        
        # Parser la réponse JSON
        try:
            data = response.json()
            logger.info(f"Réponse JSON parsée: {json.dumps(data, indent=2)[:500]}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON: {e}")
            logger.error(f"   Réponse brute: {response.text}")
            raise Exception(f"Réponse Livy invalide (non-JSON): {response.text}")
        
        # Vérifier la présence de l'ID
        statement_id = data.get("id")
        
        if statement_id is None:
            logger.error(f"❌ Pas d'ID de statement dans la réponse!")
            logger.error(f"   Keys disponibles: {list(data.keys())}")
            logger.error(f"   Réponse complète: {data}")
            raise Exception(f"Impossible d'obtenir l'ID du statement. Réponse: {json.dumps(data)}")
        
        logger.info(f"✓ Statement soumis: ID={statement_id}")
        
        # Attendre le résultat
        result = self._wait_for_statement(statement_id)
        
        return result
    
    def _wait_for_statement(self, statement_id: int, timeout: int = 180) -> Dict:
        """Attend les résultats d'un statement"""
        logger.info("Attente des résultats...")
        
        start_time = time.time()
        wait_interval = 5
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/sessions/{self.session_id}/statements/{statement_id}",
                    headers=self.headers,
                    auth=self.auth,
                    verify=False,
                    timeout=30
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur GET statement: {e}")
                raise Exception(f"Erreur lors de la vérification du statement: {e}")
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Erreur parsing JSON statement: {e}")
                logger.error(f"Réponse brute: {response.text}")
                raise Exception(f"Réponse invalide du statement: {response.text}")
            
            state = data.get("state", "unknown")
            
            logger.info(f"  État statement: {state}")
            logger.debug(f"  Données complètes: {data}")
            
            if state == "available":
                logger.info("✓ Statement terminé!")
                return self._parse_results(data)
            elif state == "error":
                error_output = data.get("output", {})
                error_trace = error_output.get("traceback", "")
                error_evalue = error_output.get("evalue", "")
                error = error_evalue or error_output.get("error", "Unknown error")
                
                logger.error(f"❌ Erreur statement: {error}")
                logger.error(f"Error evalue: {error_evalue}")
                if error_trace:
                    logger.error(f"Stack trace:\n{error_trace}")
                logger.error(f"Output complet: {json.dumps(error_output, indent=2)}")
                raise Exception(f"Statement échoué: {error}\n{error_trace}")
            
            time.sleep(wait_interval)
        
        raise TimeoutError(f"Timeout ({timeout}s) lors de l'exécution du statement")
    
    def _parse_results(self, statement_data: Dict) -> Dict:
        """Parse les résultats du statement"""
        try:
            output = statement_data.get("output", {})
            
            if output.get("status") != "ok":
                error = output.get("evalue", output.get("error", "Unknown error"))
                logger.error(f"❌ Erreur output status non-ok: {error}")
                return {
                    "success": False,
                    "error": error
                }
            
            # Vérifier aussi la présence d'une erreur evalue même si status="ok"
            # Livy peut retourner status="ok" avec une evalue contenant l'erreur réelle
            evalue = output.get("evalue", "")
            if evalue and ("error" in evalue.lower() or "exception" in evalue.lower()):
                logger.error(f"❌ Erreur détectée dans evalue: {evalue}")
                return {
                    "success": False,
                    "error": evalue
                }
            
            # Récupérer les données
            data_obj = output.get("data", {})
            text_plain = data_obj.get("text/plain", "[]")
            
            # LOGS DÉTAILLÉS POUR DÉBOGUER
            logger.info(f"=== PARSE RESULTS DEBUG ===")
            logger.info(f"Type de data_obj: {type(data_obj)}")
            logger.info(f"Contenu data_obj: {json.dumps(data_obj, indent=2, default=str)}")
            logger.info(f"Type de text_plain: {type(text_plain)}")
            logger.info(f"Repr text_plain: {repr(text_plain)}")
            logger.info(f"Longueur text_plain: {len(str(text_plain))}")
            logger.info(f"Première 500 chars: {str(text_plain)[:500]}")
            
            # Convertir en string si ce n'est pas déjà une string
            if not isinstance(text_plain, str):
                logger.warning(f"⚠️  text_plain n'est pas une string, conversion...")
                text_plain = str(text_plain)
            
            # Parser le JSON - gérer différents formats de réponse
            try:
                logger.info(f"Tentative de parsing du format reçu...")
                
                # Format 1: Table ASCII de .show()
                # +--------+-------------+...
                # |    col1|       col2|...
                # +--------+-------------+...
                # |   val1|        val2|...
                # +--------+-------------+...
                if text_plain.startswith("+"):
                    logger.info("Format détecté: Table ASCII de .show()")
                    lines = text_plain.strip().split("\n")
                    
                    # Extraire les en-têtes (ligne 2)
                    header_line = lines[1] if len(lines) > 1 else ""
                    headers = [h.strip() for h in header_line.split("|")[1:-1]]
                    logger.info(f"En-têtes trouvés: {headers}")
                    
                    # Extraire les données (lignes 3 à n-1, en sautant les séparateurs)
                    results_list = []
                    for i in range(3, len(lines), 2):  # Sauter les séparations (lignes +---+)
                        if i >= len(lines) or lines[i].startswith("+"):
                            break
                        values = [v.strip() for v in lines[i].split("|")[1:-1]]
                        if values:
                            # Créer un dict avec en-têtes et valeurs
                            row = {}
                            for header, value in zip(headers, values):
                                # Essayer de convertir en nombre si possible
                                try:
                                    if "." in value:
                                        row[header] = float(value)
                                    else:
                                        row[header] = int(value)
                                except ValueError:
                                    row[header] = value
                            results_list.append(row)
                    
                    logger.info(f"✓ Parsé {len(results_list)} lignes de table ASCII")
                
                # Format 2: JSON array [ ... ]
                elif text_plain.startswith("["):
                    logger.info("Format détecté: JSON array")
                    results_list = json.loads(text_plain)
                
                # Format 3: JSON lines (chaque ligne est un JSON)
                elif text_plain.startswith("{"):
                    logger.info("Format détecté: JSON lines")
                    lines = text_plain.strip().split("\n")
                    results_list = []
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                results_list.append(json.loads(line))
                            except json.JSONDecodeError as e:
                                logger.warning(f"⚠️  Impossible de parser ligne JSON: {line[:100]}")
                
                # Format 4: Python tuple/list
                elif text_plain.startswith("("):
                    logger.info("Format détecté: Python tuple/list")
                    import ast
                    results_list = ast.literal_eval(text_plain)
                
                else:
                    logger.warning(f"Format inconnu, retour du texte brut")
                    results_list = [{"raw": text_plain}]
                
                # Si c'est une liste de strings JSON
                if results_list and isinstance(results_list[0], str):
                    parsed_results = [json.loads(r) for r in results_list]
                else:
                    # C'est déjà parsé
                    parsed_results = results_list
                
                logger.info(f"✓ Parsed {len(parsed_results)} lignes")
                
                return {
                    "success": True,
                    "data": parsed_results,
                    "count": len(parsed_results)
                }
                
            except (json.JSONDecodeError, ValueError, SyntaxError) as parse_err:
                logger.error(f"❌ Erreur parsing JSON/Python: {parse_err}")
                logger.error(f"Type erreur: {type(parse_err)}")
                logger.error(f"Texte tentative COMPLET:\n{text_plain}")
                logger.error(f"Repr texte: {repr(text_plain)}")
                
                # Si ça échoue, retourner au moins le texte brut
                return {
                    "success": True,
                    "data": [{"raw": text_plain}],
                    "count": 1,
                    "warning": f"Parse error: {parse_err}"
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur parsing résultats: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "raw": statement_data
            }
    
    def execute_jar(
        self,
        jar_path: str,
        args: List[str] = None,
        main_class: str = None
    ) -> Dict[str, Any]:
        """Exécute un JAR via Livy (mode batch)"""
        logger.info(f"Soumission JAR: {jar_path}")
        
        payload = {
            "file": jar_path,
            "proxyUser": self.ad_user,
            "driverMemory": self.driver_memory,
            "driverCores": self.driver_cores,
            "executorMemory": self.executor_memory,
            "executorCores": self.executor_cores,
            "numExecutors": self.num_executors,
            "queue": self.queue
        }
        
        if args:
            payload["args"] = args
        
        if main_class:
            payload["className"] = main_class
        
        response = requests.post(
            f"{self.base_url}/batches",
            json=payload,
            headers=self.headers,
            auth=self.auth,
            verify=False
        )
        response.raise_for_status()
        
        data = response.json()
        batch_id = data.get("id")
        
        if not batch_id:
            raise Exception("Impossible d'obtenir l'ID du batch")
        
        logger.info(f"✓ Batch soumis: {batch_id}")
        
        # Attendre le résultat
        result = self._wait_for_batch(batch_id)
        
        return result
    
    def _wait_for_batch(self, batch_id: int, timeout: int = 600) -> Dict:
        """Attend la fin d'un batch job"""
        logger.info("Attente du batch...")
        
        start_time = time.time()
        wait_interval = 10
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/batches/{batch_id}",
                headers=self.headers,
                auth=self.auth,
                verify=False
            )
            
            data = response.json()
            state = data.get("state", "unknown")
            
            logger.info(f"  État batch: {state}")
            
            if state == "success":
                logger.info("✓ Batch terminé avec succès!")
                return {
                    "success": True,
                    "batch_id": batch_id,
                    "data": data
                }
            elif state in ["error", "dead", "killed"]:
                return {
                    "success": False,
                    "error": f"Batch échoué: {state}",
                    "data": data
                }
            
            time.sleep(wait_interval)
        
        raise TimeoutError("Timeout lors de l'exécution du batch")
    
    def close_session(self):
        """Ferme la session"""
        if self.session_id:
            logger.info(f"Fermeture session {self.session_id}...")
            
            try:
                response = requests.delete(
                    f"{self.base_url}/sessions/{self.session_id}",
                    headers=self.headers,
                    auth=self.auth,
                    verify=False
                )
                logger.info("✓ Session fermée")
            except Exception as e:
                logger.error(f"Erreur fermeture session: {e}")
            
            self.session_id = None
    
    def get_session_info(self) -> Dict:
        """Récupère les infos de la session"""
        if not self.session_id:
            return {"error": "Pas de session active"}
        
        response = requests.get(
            f"{self.base_url}/sessions/{self.session_id}",
            headers=self.headers,
            auth=self.auth,
            verify=False
        )
        
        return response.json()

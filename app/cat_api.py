import logging
from logging.handlers import RotatingFileHandler
import json
import os
from urllib import request
from fastapi import FastAPI, HTTPException, Request
import sqlite3
from typing import List, Dict, Optional
import time
from prometheus_client import make_asgi_app, Counter, Histogram
import uvicorn

# Configuração do FastAPI
app = FastAPI(title="Cat API - Case Itau", description="API para informações sobre raças de gatos")

# Configuração de logging para Loki e terminal
def setup_logging():
    # Cria diretório de logs caso não exista
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger("catapi")
    logger.setLevel(logging.INFO)
    
    # Formataçao em JSON para o Loki
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "time": self.formatTime(record),
                "level": record.levelname,
                "message": record.getMessage(),
                "service": "cat-api",
                "endpoint": getattr(record, 'endpoint', ''),
                "method": getattr(record, 'method', ''),
                "status": getattr(record, 'status', ''),
                "latency": getattr(record, 'latency', 0),
                "client": getattr(record, 'client', ''),
            }
            return json.dumps(log_record)
    
    # Handler para arquivo (Loki via Promtail)
    file_handler = RotatingFileHandler(
        f'{log_dir}/catapi.log',
        maxBytes=10*1024*1024,  # 10MB - caso gere a carga em ambiente local, esse rotate ajuda a nao lotar o disco
        backupCount=5
    )
    file_handler.setFormatter(JsonFormatter())
    
    # Handler para terminal (formato legível)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        #'%(asctime)s - %(levelname)s - %(message)s [%(endpoint)s %(method)s %(status)s %(latency).2fms]'
        '%(asctime)s - %(levelname)s - %(message)s [%(endpoint)s %(method)s %(status)s ]'
    )
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

# habilita métricas para Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

REQUEST_COUNT = Counter(
    'request_count', 'Total de requisições recebidas',
    ['endpoint', 'method', 'http_status']
)

REQUEST_LATENCY = Histogram(
    'request_latency_seconds', 'Latência das requisições',
    ['endpoint']
)

# Classe para acesso ao banco de dados
class CatDatabase:
    def __init__(self, db_name: str = 'cat_data.db'):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
    
    def get_all_breeds(self) -> List[Dict]:
        """Obtém todas as raças de gatos"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, origin, temperament, description FROM breeds')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_breed_by_id(self, breed_id: str) -> Optional[Dict]:
        """Obtém uma raça específica pelo ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, origin, temperament, description 
            FROM breeds 
            WHERE id = ?
        ''', (breed_id,))
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def get_breed_by_name(self, breed_name: str) -> Optional[Dict]:
        """Obtém uma raça específica pelo nome"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, origin, temperament, description 
            FROM breeds 
            WHERE name = ?
        ''', (breed_name,))
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def get_breeds_by_temperament(self, temperament: str) -> List[Dict]:
        """Obtém raças por temperamento"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, origin, temperament, description 
            FROM breeds 
            WHERE temperament LIKE ?
        ''', (f'%{temperament}%',))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_breeds_by_origin(self, origin: str) -> List[Dict]:
        """Obtém raças por origem"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, origin, temperament, description 
            FROM breeds 
            WHERE origin LIKE ?
        ''', (f'%{origin}%',))
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        self.conn.close()


# Middleware aprimorado para logs e métricas
@app.middleware("http")
async def log_and_track_metrics(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path
    
    try:
        response = await call_next(request)
        latency = (time.time() - start_time) * 1000  # em milissegundos
        
        # Log da requisição
        logger.info(
            "Request processed",
            extra={
                'endpoint': endpoint,
                'method': request.method,
                'status': response.status_code,
                'latency': latency,
                'client': request.client.host if request.client else None
            }
        )
        
        # Métricas
        REQUEST_COUNT.labels(
            endpoint=endpoint,
            method=request.method,
            http_status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
        
        return response
    
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        logger.error(
            f"Request failed: {str(e)}",
            extra={
                'endpoint': endpoint,
                'method': request.method,
                'status': 500,
                'latency': latency,
                'client': request.client.host if request.client else None
            }
        )
        
        REQUEST_COUNT.labels(
            endpoint=endpoint,
            method=request.method,
            http_status=500
        ).inc()
        
        raise e

# Rotas da API
@app.get("/breeds", response_model=List[Dict], tags=["Raças"])
async def list_all_breeds(request: Request):
    """
    Lista todas as raças de gatos disponíveis.
    Retorna id, nome, origem, temperamento e descrição de cada raça.
    """
    logger.info("Fetching all breeds", extra={
        'endpoint': request.url.path,
        'method': request.method
    })
    
    db = CatDatabase()
    try:
        breeds = db.get_all_breeds()
        logger.info(f"Found {len(breeds)} breeds", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 200
        })
        return breeds
    except Exception as e:
        logger.error(f"Error fetching breeds: {str(e)}", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 500
        })
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.get("/breeds/{breed_id}", response_model=Dict, tags=["Raças"])
async def get_breed_info(breed_id: str, request: Request):
    """
    Obtém informações detalhadas sobre uma raça específica.
    """
    logger.info(f"Fetching breed {breed_id}", extra={
        'endpoint': request.url.path,
        'method': request.method
    })
    
    db = CatDatabase()
    try:
        breed = db.get_breed_by_id(breed_id)
        if not breed:
            logger.warning(f"Breed {breed_id} not found", extra={
                'endpoint': request.url.path,
                'method': request.method,
                'status': 404
            })
            raise HTTPException(status_code=404, detail="Raça não encontrada")
        
        logger.info(f"Successfully fetched breed {breed_id}", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 200
        })
        return breed
    except Exception as e:
        logger.error(f"Error fetching breed {breed_id}: {str(e)}", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 500
        })
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.get("/breeds/by-temperament/{temperament}", response_model=List[Dict], tags=["Filtros"])
async def get_breeds_by_temperament(temperament: str, request: Request):
    """
    Lista raças de gatos que possuem o temperamento especificado.
    """

    logger.info(f"Fetching temperament {temperament}", extra={
        'endpoint': request.url.path,
        'method': request.method
    })

    db = CatDatabase()
    try:
        breeds = db.get_breeds_by_temperament(temperament)
        if not breeds:
            logger.warning(f"Breed {temperament} not found", extra={
                'endpoint': request.url.path,
                'method': request.method,
                'status': 404
            })
            raise HTTPException(status_code=404, detail="Temperamento não encontrado")
        logger.info(f"Successfully fetched temperament {temperament}", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 200
        })
        return breeds
    except Exception as e:
        logger.error(f"Error fetching temperaments: {str(e)}", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 500
        })
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.get("/breeds/by-origin/{origin}", response_model=List[Dict], tags=["Filtros"])
async def get_breeds_by_origin(origin: str, request: Request):
    """
    Lista raças de gatos que são originárias do local especificado.
    """

    logger.info(f"Fetching breeds by origin {origin}", extra={
        'endpoint': request.url.path,
        'method': request.method
    })

    db = CatDatabase()
    try:
        breeds = db.get_breeds_by_origin(origin)
        if not breeds:
            logger.warning(f"Breed from {origin} not found", extra={
                'endpoint': request.url.path,
                'method': request.method,
                'status': 404
            })
            raise HTTPException(
                status_code=404,
                detail=f"Nenhuma raça encontrada com origem em '{origin}'"
            )
        logger.info(f"Successfully fetched breed from {origin}", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 200
        })
        return breeds
    except Exception as e:
        logger.error(f"Error fetching Origin from: {str(e)}", extra={
            'endpoint': request.url.path,
            'method': request.method,
            'status': 500
        })
        raise HTTPException(status_code=500, detail="Internal server error")    
    finally:
        db.close()

@app.get("/health", tags=["Utilitários"])
async def health_check(request: Request):
    """Verifica o status da API"""
    logger.info("Health check", extra={
        'endpoint': request.url.path,
        'method': request.method,
        'status': 200
    })
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
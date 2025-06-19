# cats-api - Case Itau

# Introduçao

A soluçao a seguir tem como base a API Publica The Cats API https://thecatapi.com/, na qual é consumido os dados conforme a solicitação a seguir:

- Para cada uma das raças de gatos disponíveis, armazenar as informações de origem, temperamento e descrição em uma base de dados. (se disponível)  
-  Para cada uma das raças acima, salvar o endereço de 3 imagens em uma base de dados. (se disponível)  
-  Salvar o endereço de 3 imagens de gatos com chapéu.  
-  Salvar o endereço de 3 imagens de gatos com óculos.

Todos os dados são commitados em um banco de dados local em formato de arquivo para posteriormente serem consumidos pela nova API.

A API interna, aqui denominada de ```cat-api```, consome essa base de dados e tem em si, as seguintes capacidades:

- listar todas as raças
- listar as informações de uma raça
- A partir de um temperamento listar as raças
- A partir de uma origem listar as raças

Todos os metodos dessa API expõe metricas de execução para o **Prometheus**, assim como tambem gera os logs, onde há um agent do **promtail** escutando o arquivo e enviando para o **Grafana Loki**. 

Todos esses dados de Observabilidade podem ser visualizados pelo Grafana a partir de uma URL descrita nessa doc.

Existe uma peça a parte para execução da carga para testar a API gerando metricas e logs para a validaçao da mesma pelo grafana.

---

# Arquitetura

Seguem um diagrama basico da soluçao

![diagrama basico](images/cat-api_arq.png)

---

# Ferramentas e serviços utilizados


**Linguagem.:** Python com FastAPI e bash
**Database.:** Sqlite3
**API Publica.:** The Cats API
**Container.:** Docker / docker-compose
**Metricas.:** Prometheus
**Logs.:** Loki
**Visualizaçao.:** Grafana
**Gerador de carga.:** Grafana K6

## Acessos ao serviço cat-api

Endpoint API = [http://IP:8000/](http://<IP>:8000/)
Grafana da API = [Dashbord - Cat Api](http://<IP>:8000/)

Grafana do teste de carga = [Dashbord - Prometheus K6]( https://jrlabs.grafana.net/d/ccbb2351-2ae2-462f-ae0e-f2c893ad1028/k6-prometheus?orgId=1&from=now-3h&to=now&timezone=browser&var-DS_PROMETHEUS=&var-testid=&var-quantile_stat=&var-adhoc_filter=)

---

# Documentaçao da API

> **ℹ️ Info:** 
>Aqui, vale ressaltar que, um dos motivos da escolha do uso do FastAPI é que ele por padrão já expôe o ```/docs``` com o swagger como documentaçao da API e por ele mesmo é possivel fazer alguns testes nos metodos da API.


## Principais Endpoints

1. Listar Todas as Raças

    - **GET** ```/breeds```
    - **Descrição:** Retorna todas as raças de gatos disponíveis

Exemplo de sucesso:

```json
[
  {
    "id": "beng",
    "name": "Bengal",
    "origin": "United States",
    "temperament": "Alert, Agile, Energetic",
    "description": "Bengals are a lot of fun..."
  }
]
```

2. Obter Raça por ID

    - **GET** ```/breeds/{breed_id}```
    - **Parâmetros**:

        breed_id: ID da raça (ex: "*beng*")

**Exemplo de resposta com sucesso:**
```json
{
  "id": "beng",
  "name": "Bengal",
  "origin": "United States",
  "temperament": "Alert, Agile, Energetic",
  "description": "Bengals are a lot of fun..."
}

```

3. Buscar por Temperamento

    - **GET** ```/breeds/by-temperament/{temperament}```
    - **Parâmetros**:

        temperament: Traço de personalidade (ex: "*Agile*")

**Exemplo de resposta com sucesso:**
```json
[
  {
    "id": "beng",
    "name": "Bengal",
    "temperament": "Alert, Agile, Energetic"
  }
]
```

4. Buscar por Origem

    - **GET** ```/breeds/by-origin/{origin}```
    - **Parâmetros**:

        origin: País de origem (ex: "U*nited States*")

**Exemplo de resposta com sucesso:**
```json
[
  {
    "id": "beng",
    "name": "Bengal",
    "origin": "United States"
  }
]
```

5. Health Check

    - **GET** ```/health```

**Exemplo de resposta com sucesso:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

6. Métricas Prometheus

    - GET ```/metrics```

    **Descrição:** Endpoint para coleta de métricas pelo Prometheus


---

# Como executar no ambiente local

Considerando que ja possua docker e docker-compose no seu ambiente, siga os passos

1. Clone o repositorio

2. Gere a sua API_KEY no [The Cats API](https://thecatapi.com/)

3. Insira sua chave no arquivo ```docker-compose.yml``` no serviço ```cat-api```, em ```environments:```

4. A partir do mesmo nivel de diretorio do ```docker-compose.yml```, execute:

```bash
docker-compose up -d
``` 

Aguarde todos os serviços ficarem com o status **UP**
Exemplo:
![Services UP](images/docker-services-up.png)

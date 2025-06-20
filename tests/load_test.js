import { check, sleep } from 'k6';
import http from 'k6/http';
import { Trend, Rate, Counter } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

// Configurações básicas
export const options = {
  stages: [
    { duration: '2m', target: 25 },  // Ramp up para 25 usuários em 5 minutos
    { duration: '3m', target: 80 }, // Ramp up para 50 usuários
    { duration: '3m', target: 130 }, // Ramp up para 100 usuários
    { duration: '3m', target: 180 }, // Ramp up para 150 usuários
    { duration: '3m', target: 250 }, // Pico de 200 usuários
    { duration: '3m', target: 0 },   // Ramp down gradual
  ],
  thresholds: {
    http_req_failed: ['rate<0.03'],  // Menos de 1% de falhas
    http_req_duration: ['p(95)<500'], // 95% das requisições abaixo de 500ms
  },
  ext: {
    loadimpact: {
      projectID: 12345,
      name: 'Cat API load Test'
    }
  }
};

// Métricas customizadas
const responseTrend = new Trend('response_time');
const errorRate = new Rate('error_rate');
const successCounter = new Counter('success_count');

// Massa de teste - IDs de raças de gatos conhecidas
const breedIds = [
  'awir', // American Wirehair
  'amau', // Arabian Mau
  'amis', // Australian Mist
  'bali', // Balinese
  'bamb',  // Bambino
  'xyzo'  // para falhar
];

// Função para gerar temperamentos aleatórios
const temperaments = [
  'Affectionate',
  'Intelligent',
  'Playful',
  'Gentle',
  'Social',
  'Loyal',
  'Curious',
  'tristonho' // para falhar
];

// Função para gerar origens aleatórias
const origins = [
  'United States',
  'United Arab Emirates',
  'Australia',
  'Thailand',
  'Japan'
];

export default function () {
  // Definir operações de teste com pesos diferentes
  const operations = [
    { weight: 3, exec: testListBreeds },
    { weight: 2, exec: testGetBreed },
    { weight: 2, exec: testGetByTemperament },
    { weight: 2, exec: testGetByOrigin },
    { weight: 0, exec: testHealthCheck }
  ];
  
  // Selecionar operação baseada nos pesos
  const op = __chooseWeighted(operations);
  op.exec();
  
  // Pequena pausa entre requisições
  sleep(Math.random() * 2);
}

// Atencao: alterar os valores da 'cons url' para o ambiente de teste local ou remoto conforme necessário

// Operação 1: Listar todas as raças
function testListBreeds() {
  const url = 'http://3.20.164.233:8000/breeds';
  const res = http.get(url);
  
  trackMetrics(res, 'list_breeds');
}

// Operação 2: Obter raça específica
function testGetBreed() {
  const breedId = breedIds[Math.floor(Math.random() * breedIds.length)];
  const url = `http://3.20.164.233:8000/breeds/${breedId}`;
  const res = http.get(url);
  
  trackMetrics(res, 'get_breed');
}

// Operação 3: Buscar por temperamento
function testGetByTemperament() {
  const temp = temperaments[Math.floor(Math.random() * temperaments.length)];
  const url = `http://3.20.164.233:8000/breeds/by-temperament/${temp}`;
  const res = http.get(url);
  
  trackMetrics(res, 'get_by_temperament');
}

// Operação 4: Buscar por origem
function testGetByOrigin() {
  const origin = origins[Math.floor(Math.random() * origins.length)];
  const url = `http://3.20.164.233:8000/breeds/by-origin/${origin}`;
  const res = http.get(url);
  
  trackMetrics(res, 'get_by_origin');
}

// Operação 5: Health check
function testHealthCheck() {
  const url = 'http://3.20.164.233:8000/health';
  const res = http.get(url);
  
  trackMetrics(res, 'health_check');
}

// Função para rastrear métricas comuns
function trackMetrics(res, operation) {
  responseTrend.add(res.timings.duration);
  
  check(res, {
    'status was 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  }) ? successCounter.add(1) : errorRate.add(1);
}

// Função auxiliar para seleção ponderada
function __chooseWeighted(choices) {
  const sum = choices.reduce((acc, choice) => acc + choice.weight, 0);
  let r = Math.random() * sum;
  return choices.find((choice) => (r -= choice.weight) < 0);
}

// Gera um relatório resumido ao final do teste
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'load_test_summary.json': JSON.stringify(data),
  };
}
import requests
import sqlite3
from typing import List, Dict, Optional
import json
from datetime import datetime
import os

class CatAPI:
    BASE_URL = "https://api.thecatapi.com/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    def get_all_breeds(self) -> List[Dict]:
        """Obtém todas as raças de gatos disponíveis"""
        response = requests.get(f"{self.BASE_URL}/breeds", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_breed_images(self, breed_id: str, limit: int = 3) -> List[str]:
        """Obtém imagens para uma raça específica"""
        params = {
            "breed_ids": breed_id,
            "limit": limit
        }
        response = requests.get(f"{self.BASE_URL}/images/search", headers=self.headers, params=params)
        response.raise_for_status()
        return [img['url'] for img in response.json()]
    
    def get_cats_with_hats(self, limit: int = 3) -> List[str]:
        """Obtém imagens de gatos com chapéus"""
        params = {
            "category_ids": 1,  # ID Consultado pelo endpoint v1/categories/
            "limit": limit
        }
        response = requests.get(f"{self.BASE_URL}/images/search", headers=self.headers, params=params)
        response.raise_for_status()
        return [img['url'] for img in response.json()]
    
    def get_cats_with_glasses(self, limit: int = 3) -> List[str]:
        """Obtém imagens de gatos com óculos"""
        params = {
            "category_ids": 4, # ID Consultado pelo endpoint v1/categories/
            "limit": limit
        }
        response = requests.get(f"{self.BASE_URL}/images/search", headers=self.headers, params=params)
        response.raise_for_status()
        return [img['url'] for img in response.json()]


class CatDatabase:
    def __init__(self, db_name: str = 'cat_data.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS breeds (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                origin TEXT,
                temperament TEXT,
                description TEXT,
                last_updated TIMESTAMP
            )
        ''')
        

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS breed_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                breed_id TEXT NOT NULL,
                image_url TEXT NOT NULL UNIQUE,
                FOREIGN KEY (breed_id) REFERENCES breeds (id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cats_with_hats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_url TEXT NOT NULL UNIQUE,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cats_with_glasses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_url TEXT NOT NULL UNIQUE,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def save_breed(self, breed_data: Dict):
        self.cursor.execute('''
            INSERT OR REPLACE INTO breeds 
            (id, name, origin, temperament, description, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            breed_data.get('id'),
            breed_data.get('name'),
            breed_data.get('origin'),
            breed_data.get('temperament'),
            breed_data.get('description'),
            datetime.now()
        ))
        self.conn.commit()
    
    def save_breed_images(self, breed_id: str, image_urls: List[str]):
        for url in image_urls:
            try:
                self.cursor.execute('''
                    INSERT INTO breed_images (breed_id, image_url)
                    VALUES (?, ?)
                ''', (breed_id, url))
            except sqlite3.IntegrityError:
                continue
        self.conn.commit()
    
    def save_cats_with_hats(self, image_urls: List[str]):
        for url in image_urls:
            try:
                self.cursor.execute('''
                    INSERT INTO cats_with_hats (image_url)
                    VALUES (?)
                ''', (url,))
            except sqlite3.IntegrityError:
                continue
        self.conn.commit()
    
    def save_cats_with_glasses(self, image_urls: List[str]):
        for url in image_urls:
            try:
                self.cursor.execute('''
                    INSERT INTO cats_with_glasses (image_url)
                    VALUES (?)
                ''', (url,))
            except sqlite3.IntegrityError:
                continue
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# Obtem a chave de acesso a API
CAT_API_KEY = os.getenv('CAT_API_KEY')

def main():
    # Configurações
    API_KEY = CAT_API_KEY

    # Inicializa API e banco de dados
    cat_api = CatAPI(API_KEY)
    db = CatDatabase()
    
    print("Coletando dados da The Cat API...")
    
    try:
        # a. Coletar informações das raças
        breeds = cat_api.get_all_breeds()
        print(f"Encontradas {len(breeds)} raças de gatos.")
        
        for breed in breeds:
            # Salvar informações básicas da raça
            db.save_breed(breed)
            
            # b. Coletar e salvar imagens da raça
            if 'id' in breed:
                try:
                    images = cat_api.get_breed_images(breed['id'])
                    db.save_breed_images(breed['id'], images)
                    print(f"Salvas {len(images)} imagens para a raça {breed['name']}")
                except Exception as e:
                    print(f"Erro ao obter imagens para {breed['name']}: {str(e)}")
        
        # c. Coletar e salvar imagens de gatos com chapéus
        cats_with_hats = cat_api.get_cats_with_hats()
        db.save_cats_with_hats(cats_with_hats)
        print(f"Salvas {len(cats_with_hats)} imagens de gatos com chapéus")
        
        # d. Coletar e salvar imagens de gatos com óculos
        cats_with_glasses = cat_api.get_cats_with_glasses()
        db.save_cats_with_glasses(cats_with_glasses)
        print(f"Salvas {len(cats_with_glasses)} imagens de gatos com óculos")
        
        print("Coleta de dados concluída com sucesso!")
    
    except Exception as e:
        print(f"Erro durante a coleta de dados: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
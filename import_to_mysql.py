#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Z/X Card Database Import Script
Imports card data from CSV into MySQL database
"""

import csv
import mysql.connector
from mysql.connector import Error
import re
import os
from typing import Dict, List, Optional, Tuple

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Update with your MySQL password
    'database': 'zx_cards',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

class ZXCardImporter:
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor()
            print("Successfully connected to MySQL database")
            return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MySQL database"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("Disconnected from MySQL database")
    
    def get_lookup_id(self, table: str, code: str) -> Optional[int]:
        """Get ID from lookup table by code"""
        try:
            query = f"SELECT id FROM {table} WHERE code = %s"
            self.cursor.execute(query, (code,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"Error getting {table} ID for code {code}: {e}")
            return None
    
    def parse_card_data(self, row: Dict[str, str]) -> Dict[str, any]:
        """Parse and clean card data from CSV row"""
        # Clean and prepare data
        card_data = {
            'card_id': row['card_id'].strip(),
            'card_number': row['card_number'].strip(),
            'name': row['name'].strip(),
            'furi': row['furi'].strip() if row['furi'] else None,
            'race': row['race'].strip() if row['race'] else None,
            'cost': row['cost'].strip() if row['cost'] else None,
            'power': row['power'].strip() if row['power'] else None,
            'life': row['life'].strip() if row['life'] else None,
            'illustrator': row['illustrator'].strip() if row['illustrator'] else None,
            'text': row['text'].strip() if row['text'] else None,
            'image_url': row['image_url'].strip() if row['image_url'] else None,
        }
        
        # Determine rarity
        rarity_code = self.determine_rarity(row['rarity'])
        card_data['rarity_id'] = self.get_lookup_id('rarities', rarity_code) if rarity_code else None
        
        # Determine card type
        type_code = self.determine_card_type(row['type'])
        card_data['type_id'] = self.get_lookup_id('card_types', type_code) if type_code else None
        
        # Determine color (this would need to be extracted from card data or text)
        color_code = self.determine_color(row)
        card_data['color_id'] = self.get_lookup_id('colors', color_code) if color_code else None
        
        return card_data
    
    def determine_rarity(self, rarity_text: str) -> Optional[str]:
        """Determine rarity code from rarity text"""
        if not rarity_text:
            return None
            
        rarity_text = rarity_text.strip().upper()
        
        # Map common rarity patterns
        rarity_mapping = {
            'N': 'n',
            'R': 'r',
            'R+': 'R+-gacha',
            'SR': 'SR-gacha',
            'SSR': 'SSR-gacha',
            'RR': 'RR-gacha',
            'LR': 'l',
            'UR': 'u',
            'CR': 'c',
            'SEC': 'SEC-gacha',
            'OBR': 'OBR-gacha',
            'BR': 'BR-gacha',
            'WR': 'WR-gacha',
            'MGNR': 'MGNR-gacha',
            '日本一R': 'nipponichiR',
            'R（隐藏）': 'R-secret',
        }
        
        # Check for exact matches first
        for key, value in rarity_mapping.items():
            if key in rarity_text:
                return value
        
        # Check for single character rarities
        if len(rarity_text) == 1 and rarity_text.isalpha():
            return rarity_text.lower()
        
        return None
    
    def determine_card_type(self, type_text: str) -> Optional[str]:
        """Determine card type code from type text"""
        if not type_text:
            return None
            
        type_text = type_text.strip()
        
        type_mapping = {
            '玩家': 'player',
            '玩家EX': 'player-ex',
            'Z/X': 'zx',
            'Z/X EX': 'zx-ex',
            'Z/X OB': 'zx-ob',
            'Z/X TOKEN': 'zx-token',
            '事件': 'event',
            '事件EX': 'event-ex',
            '升格': 'promotion',
            '升格EX': 'promotion-ex',
            '剑临': 'sword-coming',
            '标记': 'marker',
            '链结': 'link',
        }
        
        return type_mapping.get(type_text)
    
    def determine_color(self, row: Dict[str, str]) -> Optional[str]:
        """Determine color from card data"""
        # This is a simplified approach - in reality, you might need to parse
        # the card text or use other methods to determine color
        text = (row.get('text', '') + ' ' + row.get('name', '')).lower()
        
        color_keywords = {
            'red': ['红', '赤', 'red'],
            'blue': ['蓝', '青', 'blue'],
            'white': ['白', 'white'],
            'black': ['黑', 'black'],
            'green': ['绿', 'green'],
        }
        
        for color, keywords in color_keywords.items():
            if any(keyword in text for keyword in keywords):
                return color
        
        return 'none'  # Default to no color
    
    def insert_card(self, card_data: Dict[str, any]) -> Optional[int]:
        """Insert card into database and return card ID"""
        try:
            query = """
            INSERT INTO cards (
                card_id, card_number, name, furi, rarity_id, type_id, 
                race, cost, power, life, illustrator, text, image_url, color_id
            ) VALUES (
                %(card_id)s, %(card_number)s, %(name)s, %(furi)s, %(rarity_id)s, %(type_id)s,
                %(race)s, %(cost)s, %(power)s, %(life)s, %(illustrator)s, %(text)s, %(image_url)s, %(color_id)s
            )
            """
            
            self.cursor.execute(query, card_data)
            self.connection.commit()
            
            # Get the inserted card ID
            card_id = self.cursor.lastrowid
            return card_id
            
        except Error as e:
            print(f"Error inserting card {card_data['card_id']}: {e}")
            self.connection.rollback()
            return None
    
    def import_cards_from_csv(self, csv_file: str):
        """Import all cards from CSV file"""
        if not os.path.exists(csv_file):
            print(f"CSV file {csv_file} not found")
            return
        
        print(f"Starting import from {csv_file}")
        
        imported_count = 0
        error_count = 0
        
        with open(csv_file, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Parse card data
                    card_data = self.parse_card_data(row)
                    
                    # Insert card
                    card_db_id = self.insert_card(card_data)
                    
                    if card_db_id:
                        imported_count += 1
                        if imported_count % 100 == 0:
                            print(f"Imported {imported_count} cards...")
                    else:
                        error_count += 1
                        print(f"Failed to import card {row['card_id']} at row {row_num}")
                        
                except Exception as e:
                    error_count += 1
                    print(f"Error processing row {row_num}: {e}")
        
        print(f"Import completed!")
        print(f"Successfully imported: {imported_count} cards")
        print(f"Errors: {error_count} cards")
    
    def create_indexes(self):
        """Create additional indexes for better performance"""
        indexes = [
            "CREATE INDEX idx_cards_name_search ON cards(name)",
            "CREATE INDEX idx_cards_number_search ON cards(card_number)",
            "CREATE INDEX idx_cards_rarity_type ON cards(rarity_id, type_id)",
            "CREATE INDEX idx_cards_cost_power ON cards(cost, power)",
            "CREATE FULLTEXT INDEX idx_cards_text_search ON cards(text)",
        ]
        
        for index_query in indexes:
            try:
                self.cursor.execute(index_query)
                print(f"Created index: {index_query.split()[2]}")
            except Error as e:
                print(f"Error creating index: {e}")
        
        self.connection.commit()
    
    def verify_import(self):
        """Verify the import was successful"""
        try:
            # Count total cards
            self.cursor.execute("SELECT COUNT(*) FROM cards")
            total_cards = self.cursor.fetchone()[0]
            
            # Count by rarity
            self.cursor.execute("""
                SELECT r.name_jp, COUNT(*) as count 
                FROM cards c 
                LEFT JOIN rarities r ON c.rarity_id = r.id 
                GROUP BY c.rarity_id, r.name_jp 
                ORDER BY count DESC
            """)
            rarity_counts = self.cursor.fetchall()
            
            # Count by type
            self.cursor.execute("""
                SELECT ct.name_jp, COUNT(*) as count 
                FROM cards c 
                LEFT JOIN card_types ct ON c.type_id = ct.id 
                GROUP BY c.type_id, ct.name_jp 
                ORDER BY count DESC
            """)
            type_counts = self.cursor.fetchall()
            
            print(f"\n=== Import Verification ===")
            print(f"Total cards imported: {total_cards}")
            
            print(f"\nCards by Rarity:")
            for rarity, count in rarity_counts:
                print(f"  {rarity or 'Unknown'}: {count}")
            
            print(f"\nCards by Type:")
            for card_type, count in type_counts:
                print(f"  {card_type or 'Unknown'}: {count}")
                
        except Error as e:
            print(f"Error verifying import: {e}")

def main():
    """Main function"""
    importer = ZXCardImporter()
    
    try:
        # Connect to database
        if not importer.connect():
            return
        
        # Import cards from CSV
        importer.import_cards_from_csv('zx_cards.csv')
        
        # Create additional indexes
        print("\nCreating additional indexes...")
        importer.create_indexes()
        
        # Verify import
        importer.verify_import()
        
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        importer.disconnect()

if __name__ == "__main__":
    main()

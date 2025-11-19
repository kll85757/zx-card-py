-- Z/X Card Database Schema
-- Created for comprehensive card management system

-- Create database
CREATE DATABASE IF NOT EXISTS zx_cards CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE zx_cards;

-- Colors lookup table
CREATE TABLE colors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(10) NOT NULL UNIQUE,
    name_jp VARCHAR(50) NOT NULL,
    name_en VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rarities lookup table
CREATE TABLE rarities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name_jp VARCHAR(50) NOT NULL,
    name_en VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Card types lookup table
CREATE TABLE card_types (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name_jp VARCHAR(50) NOT NULL,
    name_en VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Marks lookup table
CREATE TABLE marks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(10) NOT NULL UNIQUE,
    name_jp VARCHAR(50) NOT NULL,
    name_en VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags lookup table
CREATE TABLE tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    name_jp VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main cards table
CREATE TABLE cards (
    id INT PRIMARY KEY AUTO_INCREMENT,
    card_id VARCHAR(20) NOT NULL UNIQUE,
    card_number VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    furi VARCHAR(200),
    rarity_id INT,
    type_id INT,
    race VARCHAR(100),
    cost VARCHAR(10),
    power VARCHAR(10),
    life VARCHAR(10),
    illustrator VARCHAR(100),
    text TEXT,
    image_url VARCHAR(500),
    color_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_card_number (card_number),
    INDEX idx_name (name),
    INDEX idx_rarity (rarity_id),
    INDEX idx_type (type_id),
    INDEX idx_color (color_id),
    INDEX idx_cost (cost),
    INDEX idx_power (power),
    
    FOREIGN KEY (rarity_id) REFERENCES rarities(id) ON DELETE SET NULL,
    FOREIGN KEY (type_id) REFERENCES card_types(id) ON DELETE SET NULL,
    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET NULL
);

-- Card marks junction table (many-to-many)
CREATE TABLE card_marks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    card_id INT NOT NULL,
    mark_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_card_mark (card_id, mark_id),
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
    FOREIGN KEY (mark_id) REFERENCES marks(id) ON DELETE CASCADE
);

-- Card tags junction table (many-to-many)
CREATE TABLE card_tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    card_id INT NOT NULL,
    tag_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_card_tag (card_id, tag_id),
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Insert colors data
INSERT INTO colors (code, name_jp, name_en) VALUES
('none', '无', 'None'),
('red', '红', 'Red'),
('blue', '蓝', 'Blue'),
('white', '白', 'White'),
('black', '黑', 'Black'),
('green', '绿', 'Green');

-- Insert rarities data
INSERT INTO rarities (code, name_jp, name_en) VALUES
('b', 'b', 'b'),
('c', 'c', 'c'),
('k', 'k', 'k'),
('l', 'l', 'l'),
('m', 'm', 'm'),
('n', 'n', 'n'),
('o', 'o', 'o'),
('p', 'p', 'p'),
('q', 'q', 'q'),
('SR-gacha', 'SR（线上抽卡）', 'SR (Gacha)'),
('r', 'r', 'r'),
('s', 's', 's'),
('R+-gacha', 'R+（线上抽卡）', 'R+ (Gacha)'),
('t', 't', 't'),
('u', 'u', 'u'),
('v', 'v', 'v'),
('w', 'w', 'w'),
('x', 'x', 'x'),
('y', 'y', 'y'),
('z', 'z', 'z'),
('A', 'A', 'A'),
('nipponichiR', '日本一R', 'Nipponichi R'),
('B', 'B', 'B'),
('C', 'C', 'C'),
('R-secret', 'R（隐藏）', 'R (Secret)'),
('D', 'D', 'D'),
('E', 'E', 'E'),
('F', 'F', 'F'),
('G', 'G', 'G'),
('H', 'H', 'H'),
('I', 'I', 'I'),
('J', 'J', 'J'),
('RR-gacha', 'RR（线上抽卡）', 'RR (Gacha)'),
('MGNR-gacha', 'MGNR（线上抽卡）', 'MGNR (Gacha)'),
('WR-gacha', 'WR（线上抽卡）', 'WR (Gacha)'),
('BR-gacha', 'BR（线上抽卡）', 'BR (Gacha)'),
('OBR-gacha', 'OBR（线上抽卡）', 'OBR (Gacha)'),
('K', 'K', 'K'),
('SSR-gacha', 'SSR（线上抽卡）', 'SSR (Gacha)'),
('SEC-gacha', 'SEC（线上抽卡）', 'SEC (Gacha)'),
('SEC-gahca', 'SEC-gahca', 'SEC-gahca');

-- Insert card types data
INSERT INTO card_types (code, name_jp, name_en) VALUES
('player', '玩家', 'Player'),
('player-ex', '玩家EX', 'Player EX'),
('zx', 'Z/X', 'Z/X'),
('zx-ex', 'Z/X EX', 'Z/X EX'),
('zx-ob', 'Z/X OB', 'Z/X OB'),
('zx-token', 'Z/X TOKEN', 'Z/X TOKEN'),
('event', '事件', 'Event'),
('event-ex', '事件EX', 'Event EX'),
('promotion', '升格', 'Promotion'),
('promotion-ex', '升格EX', 'Promotion EX'),
('sword-coming', '剑临', 'Sword Coming'),
('marker', '标记', 'Marker'),
('link', '链结', 'Link');

-- Insert marks data
INSERT INTO marks (code, name_jp, name_en) VALUES
('b', 'b', 'b'),
('ES', '觉醒之种', 'Evolution Seed'),
('IG', '点燃', 'Ignition');

-- Insert tags data
INSERT INTO tags (code, name_jp, name_en) VALUES
('life-recovery', '生命恢复', 'Life Recovery'),
('void-messenger', '虚空使者', 'Void Messenger'),
('starter-card', '起始卡', 'Starter Card'),
('gate-card', '门扉卡', 'Gate Card'),
('starter-resource', '起始资源', 'Starter Resource'),
('overdrive', '超限驱动', 'Overdrive'),
('absolute-boundary', '绝界', 'Absolute Boundary'),
('range', '射程', 'Range'),
('zero-point-optimization', '零点优化', 'Zero Point Optimization'),
('evolution-force', '进化原力', 'Evolution Force'),
('zx-extend-drive', 'Z/X延伸驱动', 'Z/X Extend Drive'),
('heaven-breaking-descent', '破天降临', 'Heaven Breaking Descent'),
('god-level', '神Lv', 'God Level'),
('awakened-level', '觉醒者Lv', 'Awakened Level'),
('level-acceleration-god', 'Lv加速-神', 'Level Acceleration - God'),
('level-acceleration-awakened', 'Lv加速-觉醒者', 'Level Acceleration - Awakened'),
('resource-synergy', '资源联动', 'Resource Synergy'),
('universal-popular', '泛用热门', 'Universal Popular'),
('effect-correction', '效果修正', 'Effect Correction'),
('sealed-god-designation', '封神指定', 'Sealed God Designation'),
('legend-designation', '传说指定', 'Legend Designation');

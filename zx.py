import requests
from bs4 import BeautifulSoup
import csv
import time
import json

BASE_URL = "https://haronomagia.com/zxcard/?is_searchresult=1&sm=1&srt=1&fr=&clt=1&rct=1&cs1=-1&cs2=-1&pw1=-1&pw2=-1&lf1=-1&lf2=-1&skt=1&fr2=&fr3=&page={}"
API_URL = "https://haronomagia.com/zxcard/api.php"

def get_cards_api(page):
    """通过API获取卡牌信息"""
    try:
        # 尝试不同的API模式
        modes_to_try = [
            {'mode': 'get_cardlist', 'page': page},
            {'mode': 'cardlist', 'page': page},
            {'mode': 'get_cards', 'page': page},
            {'mode': 'list', 'page': page},
            {'mode': 'search', 'page': page},
            {'mode': 'get_cardlist', 'page': page, 'limit': 50},
            {'mode': 'get_cardlist', 'page': page, 'per_page': 50}
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://haronomagia.com/zxcard/'
        }
        
        for data in modes_to_try:
            print(f"尝试API模式: {data}")
            resp = requests.post(API_URL, data=data, headers=headers)
            print(f"API请求状态码: {resp.status_code}")
            
            if resp.status_code == 200 and len(resp.text.strip()) > 0:
                print(f"API响应内容长度: {len(resp.text)}")
                # 保存API响应以便调试
                with open(f"api_response_{page}_{data['mode']}.html", "w", encoding="utf-8") as f:
                    f.write(resp.text)
                print(f"API响应已保存到 api_response_{page}_{data['mode']}.html")
                
                # 尝试解析HTML响应
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("tr")
                print(f"API响应中找到 {len(rows)} 行数据")
                
                if len(rows) > 0:
                    cards = []
                    for row in rows[1:]:  # 跳过表头
                        cols = row.find_all("td")
                        if not cols or len(cols) < 6:
                            continue

                        card = {
                            "card_id": cols[0].get_text(strip=True),
                            "name": cols[1].get_text(strip=True),
                            "series": cols[2].get_text(strip=True),
                            "rarity": cols[3].get_text(strip=True),
                            "type": cols[4].get_text(strip=True),
                            "cost": cols[5].get_text(strip=True),
                            "power": cols[6].get_text(strip=True) if len(cols) > 6 else "",
                            "text": cols[7].get_text(strip=True) if len(cols) > 7 else "",
                            "color": cols[8].get_text(strip=True) if len(cols) > 8 else "",
                            "image_url": row.find("img")["src"] if row.find("img") else ""
                        }
                        cards.append(card)
                    
                    if cards:
                        return cards
            else:
                print(f"API模式 {data['mode']} 失败或无内容")
        
        print("所有API模式都失败了")
        return []
            
    except Exception as e:
        print(f"API请求异常: {e}")
        return []

def get_cards(page):
    """爬取单页卡牌信息"""
    # 首先尝试API方式
    cards = get_cards_api(page)
    if cards:
        return cards
    
    # 如果API失败，回退到原来的HTML解析方式
    url = BASE_URL.format(page)
    
    # 尝试使用session来保持状态
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    print(f"访问URL: {url}")
    resp = session.get(url)
    resp.encoding = "utf-8"
    if resp.status_code != 200:
        print(f"请求失败: {url}, 状态码: {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = []

    # 调试：查看页面内容
    print(f"页面标题: {soup.title.string if soup.title else '无标题'}")
    
    # 查找所有表格
    tables = soup.find_all("table")
    print(f"找到 {len(tables)} 个表格")
    
    # 查找所有div
    divs = soup.find_all("div")
    print(f"找到 {len(divs)} 个div")
    
    # 查找所有class包含card的元素
    card_elements = soup.find_all(class_=lambda x: x and 'card' in x.lower())
    print(f"找到 {len(card_elements)} 个包含'card'的元素")
    
    # 查找卡牌数据 - 使用新的结构
    card_elements = soup.find_all("dl", class_="card_info")
    print(f"找到 {len(card_elements)} 个卡牌元素")
    
    # 保存页面内容到文件以便调试
    with open(f"debug_page_{page}.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"页面内容已保存到 debug_page_{page}.html")
    
    for card_element in card_elements:
        try:
            # 提取卡牌ID
            card_id = card_element.get("data-card_id", "")
            
            # 提取卡牌编号
            card_number_elem = card_element.find("p", class_="card_number")
            card_number = card_number_elem.get_text(strip=True) if card_number_elem else ""
            
            # 提取卡牌名称
            name_elem = card_element.find("p", class_="name")
            name = name_elem.get_text(strip=True) if name_elem else ""
            
            # 提取假名
            furi_elem = card_element.find("p", class_="furi")
            furi = furi_elem.get_text(strip=True) if furi_elem else ""
            
            # 提取图片URL
            img_elem = card_element.find("img")
            image_url = img_elem.get("src", "") if img_elem else ""
            
            # 查找详细信息 - 使用更精确的选择器
            card_detail = card_element.find("dl", class_="card_detail")
            if card_detail:
                # 提取稀有度
                rare_elem = card_detail.find("dd", class_="rare")
                if rare_elem:
                    rarity_text = rare_elem.get_text(strip=True)
                    # 移除"レア"标签，只保留稀有度值
                    rarity = rarity_text.replace("レア", "").strip()
                else:
                    rarity = ""
                
                # 提取卡牌类型
                type_elem = card_detail.find("dd", class_="type")
                if type_elem:
                    type_text = type_elem.get_text(strip=True)
                    # 移除"カードタイプ"标签，只保留类型值
                    card_type = type_text.replace("カードタイプ", "").strip()
                else:
                    card_type = ""
                
                # 提取种族
                race_elem = card_detail.find("dd", class_="race")
                if race_elem:
                    race_text = race_elem.get_text(strip=True)
                    # 移除"種族"标签，只保留种族值
                    race = race_text.replace("種族", "").strip()
                else:
                    race = ""
                
                # 提取费用
                cost_elem = card_detail.find("dd", class_="cost")
                if cost_elem:
                    cost_text = cost_elem.get_text(strip=True)
                    # 移除"コスト"标签，只保留费用值
                    cost = cost_text.replace("コスト", "").strip()
                else:
                    cost = ""
                
                # 提取力量
                power_elem = card_detail.find("dd", class_="power")
                if power_elem:
                    power_text = power_elem.get_text(strip=True)
                    # 移除"パワー"标签，只保留力量值
                    power = power_text.replace("パワー", "").strip()
                else:
                    power = ""
                
                # 提取生命值
                life_elem = card_detail.find("dd", class_="life")
                if life_elem:
                    life_text = life_elem.get_text(strip=True)
                    # 移除"ライフ"标签，只保留生命值
                    life = life_text.replace("ライフ", "").strip()
                else:
                    life = ""
                
                # 提取插画师
                illust_elem = card_detail.find("dd", class_="illust")
                if illust_elem:
                    illust_text = illust_elem.get_text(strip=True)
                    # 移除"イラストレーター"标签，只保留插画师名
                    illustrator = illust_text.replace("イラストレーター", "").strip()
                else:
                    illustrator = ""
                
                # 提取卡牌文本
                text_elem = card_detail.find("p", class_="text")
                card_text = text_elem.get_text(strip=True) if text_elem else ""
            else:
                rarity = card_type = race = cost = power = life = illustrator = card_text = ""
            
            card = {
                "card_id": card_id,
                "card_number": card_number,
                "name": name,
                "furi": furi,
                "rarity": rarity,
                "type": card_type,
                "race": race,
                "cost": cost,
                "power": power,
                "life": life,
                "illustrator": illustrator,
                "text": card_text,
                "image_url": image_url
            }
            cards.append(card)
            print(f"提取卡牌: {card_number} - {name}")
            
        except Exception as e:
            print(f"解析卡牌时出错: {e}")
            continue

    return cards


def main():
    all_cards = []
    page = 1

    while True:
        print(f"正在爬取第 {page} 页...")
        cards = get_cards(page)
        if not cards:
            break
        all_cards.extend(cards)
        page += 1
        time.sleep(1)  # 防止请求过快

    # 保存到 CSV
    if all_cards:
        keys = all_cards[0].keys()
        with open("zx_cards.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_cards)
        print(f"完成！共抓取 {len(all_cards)} 张卡牌，已保存到 zx_cards.csv")
    else:
        print("未找到任何卡牌数据")


if __name__ == "__main__":
    main()

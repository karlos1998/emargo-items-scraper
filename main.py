import os
import requests
from bs4 import BeautifulSoup
import mysql.connector
from urllib.parse import urljoin
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

db = mysql.connector.connect(
    host="localhost",
    user="user",
    password="password",
    database="items_db"
)
cursor = db.cursor()

os.makedirs("itemy", exist_ok=True)

def save_to_db(item):
    sql = """
    INSERT INTO base_items (name, stat, pr, cl, src)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE name = VALUES(name)
    """
    cursor.execute(sql, (item['name'], item['stat'], item['pr'], item['cl'], item['src']))
    db.commit()
    logging.info(f"Zapisano do bazy: {item['name']}")

def download_image(src_path, img_url, retries=5, delay=3):
    image_path = os.path.join("itemy", src_path)
    if not os.path.exists(image_path):
        for attempt in range(retries):
            try:
                response = requests.get(img_url, timeout=10)
                response.raise_for_status()
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                with open(image_path, "wb") as file:
                    file.write(response.content)
                logging.info(f"Pobrano obrazek: {img_url} jako {src_path}")
                return src_path
            except requests.RequestException as e:
                logging.warning(f"Problem z pobraniem {img_url} (próba {attempt + 1} z {retries}): {e}")
                time.sleep(delay)
        logging.error(f"Nie udało się pobrać obrazka: {img_url}")
        return None
    return src_path

base_url = "https://web.archive.org"
start_url = "https://web.archive.org/web/20151117161812/http://emargo.pl/przedmioty"
try:
    response = requests.get(start_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    logging.info("Pobrano stronę główną.")
except requests.RequestException as e:
    logging.error(f"Nie udało się pobrać strony głównej: {e}")
    exit()

links = [
    urljoin(base_url, link["href"])
    for link in soup.find_all("a", href=True)
    if "przedmioty/dla/" in link["href"]
]

logging.info(f"Znaleziono {len(links)} linków do podstron.")

# Przejdź po linkach i zbierz dane o przedmiotach
for link in links:
    try:
        page = requests.get(link, timeout=30)
        page.raise_for_status()
        sub_soup = BeautifulSoup(page.content, "html.parser")
        logging.info(f"Pobrano podstronę: {link}")
    except requests.RequestException as e:
        logging.warning(f"Nie udało się pobrać podstrony {link}: {e}")
        continue

    items = sub_soup.find_all("div", class_="item", ctip="item")

    for item in items:
        try:
            stats = item["stats"].split("||")
            img_src_full = item.img["src"]
            img_src = img_src_full.split("/margonem/obrazki/")[1]  # Ścieżka do bazy danych bez "itemy/"

            img_path = download_image(img_src, urljoin(base_url, img_src_full))
            if img_path is None:
                logging.warning(f"Pominięto przedmiot z powodu problemu z obrazkiem: {stats[0]}")
                continue

            item_data = {
                "name": stats[0],
                "stat": stats[1],
                "pr": stats[3],
                "cl": stats[2],
                "src": img_src
            }
            save_to_db(item_data)
        except KeyError as e:
            logging.warning(f"Pominięto przedmiot z powodu brakującego atrybutu: {e}")
        except IndexError as e:
            logging.warning(f"Niekompletne dane w stats dla przedmiotu: {e}")

cursor.close()
db.close()
logging.info("Proces zakończony.")
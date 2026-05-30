import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# Set a tall window so more rows are in viewport
options.add_argument("--window-size=1920,10000")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

print("Loading Sofascore rankings...")
driver.get("https://www.sofascore.com/football/rankings/fifa")

WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "table tr"))
)

# Scroll the table container specifically
print("Scrolling table...")
for i in range(50):
    driver.execute_script("""
        const table = document.querySelector('table');
        if (table) {
            let parent = table.parentElement;
            while (parent) {
                parent.scrollTop += 500;
                parent = parent.parentElement;
            }
        }
        window.scrollBy(0, 500);
    """)
    time.sleep(0.3)

# Check how many rows we got
rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
print(f"Rows found in DOM: {len(rows)}")

html = driver.page_source
driver.quit()

df = pd.read_html(html)[0]
df = df[['#', 'Country', 'Total pts']].copy()
df.columns = ['rank', 'team', 'points']
df['rank'] = df['rank'].astype(str).str.extract(r'(\d+)').astype(int)
df['points'] = pd.to_numeric(df['points'], errors='coerce')
df = df.dropna(subset=['points'])
df = df.sort_values('rank').reset_index(drop=True)

df.to_csv("data/raw/fifa_rankings.csv", index=False)
print(f"Saved {len(df)} teams")
print(f"Last 5 rows:\n{df.tail()}")

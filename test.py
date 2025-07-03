import os
import time
import pandas as pd
from datetime import datetime
from multiprocessing import Process, Manager, Lock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

NUM_USERS = 1
EDGEDRIVER_PATH = "msedgedriver.exe"
HACKERRANK_URL = "https://www.hackerrank.com/"

def wait_for_hackerrank_home(driver, timeout=60):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'logo-dark.svg') and contains(@class, 'pagenav-logo-dark')]"))
    )


def run_hackerrank_session(user_id, all_results, lock, results_dir, timestamp):
    session_results = []
    user_name = f"user{user_id + 1}"
    print(f"[{user_name}] Starting session...")

    edge_options = EdgeOptions()
    edge_options.add_argument("--inprivate")
    driver = webdriver.Edge(service=EdgeService(EDGEDRIVER_PATH), options=edge_options)

    try:
        print(f"[{user_name}] Navigating to HackerRank...")
        start = time.time()
        driver.get(HACKERRANK_URL)
        wait_for_hackerrank_home(driver)
        end = time.time()

        load_time = end - start
        print(f"[{user_name}] HackerRank loaded in {load_time:.2f} seconds.")

        session_results.append({
            "user_name": user_name,
            "url": HACKERRANK_URL,
            "load_time": load_time
        })

        ss_path = os.path.join(results_dir, f"hackerrank_{user_name}_{timestamp}.png")
        driver.save_screenshot(ss_path)

    finally:
        driver.quit()
        with lock:
            all_results.extend(session_results)

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"hackerrank_loadtest_results/test_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)
    OUTPUT_EXCEL = os.path.join(results_dir, "hackerrank_load_times.xlsx")

    manager = Manager()
    all_results = manager.list()
    lock = manager.Lock()
    processes = []

    for i in range(NUM_USERS):
        p = Process(target=run_hackerrank_session, args=(i, all_results, lock, results_dir, timestamp))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print("All sessions completed.")

    df = pd.DataFrame(list(all_results), columns=["user_name", "url", "load_time"])
    agg_df = pd.DataFrame({
        "min_load_time": [df["load_time"].min()],
        "max_load_time": [df["load_time"].max()],
        "avg_load_time": [df["load_time"].mean()],
        "num_users": [NUM_USERS]
    })

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="individual_results", index=False)
        agg_df.to_excel(writer, sheet_name="summary", index=False)

    print("Excel report saved at:", OUTPUT_EXCEL)

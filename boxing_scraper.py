import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from send_message import send_email
import os
from datetime import datetime
import json

def scrape_dk():
    # URL of the DraftKings UFC odds page
    url = "https://sportsbook.draftkings.com/leagues/boxing/boxing"

    max_retries = 5

    retry_delay = 60 # delay in seconds before retrying

    for attempt in range(max_retries):

        try:

            # Fetch the HTML content from the URL
            response = requests.get(url)

            if response.status_code == 200:
                # Store response content
                html_content = response.content

                # Parse the HTML content using BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')

                fighters_list = []

                all_fighters_odds_list = []

                bout_ids = []

                # Looping through list of html elements that start with "tr"
                for i in soup.find_all("div", class_="sportsbook-outcome-cell"):

                    if "sportsbook-outcome-cell__label" in str(i) and "sportsbook-odds american default-color" in str(i):

                        fighters_list.append(i.find('span', class_='sportsbook-outcome-cell__label').text.strip())

                        all_fighters_odds_list.append(i.find('span', class_='sportsbook-odds american default-color').text.strip())

                        target_div = i.find("div", class_="sportsbook-outcome-cell__body")

                        data_tracking = target_div.get('data-tracking')

                        data_tracking_json = json.loads(data_tracking)

                        event_id = data_tracking_json.get('eventId')

                        bout_ids.append(int(event_id))

                if fighters_list and len(fighters_list) % 2 == 0:

                    # Make a list of the first fighters in the bout using the list of all fighters
                    fighter_1 = [fighters_list[i] for i in range(0, len(fighters_list), 2)]

                    # Make a list of the second fighters (opponents) in the bout using the list of all fighters
                    fighter_2 = [fighters_list[i + 1] for i in range(0, len(fighters_list), 2)]

                    # Make a list of the odds for the first fighters
                    fighter_1_odds = [all_fighters_odds_list[i] for i in range(0, len(all_fighters_odds_list), 2)]

                    # Make a list of the odds for the second fighters (opponents)
                    fighter_2_odds = [all_fighters_odds_list[i + 1] for i in range(0, len(all_fighters_odds_list), 2)]

                    # Make a list of the bout ids 
                    fighter_bout_id = [bout_ids[i] for i in range(0, len(fighters_list), 2)]

                    # Sort the column data to make ready to return
                    data = list(zip(fighter_1, fighter_1_odds, fighter_2, fighter_2_odds, fighter_bout_id))

                    return data
                
                else:
                    
                    return False
            
            else:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{current_time}] Failed to retrieve data: {response.status_code}")
                return None
            
        except requests.RequestException as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{current_time}] Request failed: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
# Function to append data to a CSV file
def append_data_to_csv(df, file_path):
    if not os.path.isfile(file_path):
        df.to_csv(file_path, index=False)
    else:
        df.to_csv(file_path, mode='a', header=False, index=False)

# Function to load data from a CSV file
def load_data_from_csv(filename):
    try:
        df = pd.read_csv(filename)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['fighter_1', 'fighter_1_odds', 'fighter_2', 'fighter_2_odds', 'fighter_bout_id'])
    
def main():
    # Get the current directory of the script
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Define the path to the CSV file
    csv_filename = os.path.join(current_directory, 'boxing_odds.csv')

    
    
    while True:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{current_time}] running')

        stored_fight_data_df = load_data_from_csv(csv_filename)

        scraped_data = scrape_dk()

        if scraped_data:
            # Create new dataframe using data scraped from DK website
            newly_scraped_fight_data_df = pd.DataFrame(scraped_data, columns=['fighter_1', 'fighter_1_odds', 'fighter_2', 'fighter_2_odds', 'fighter_bout_id'])

            # Identify new fights by comparing fighter_bout_id against previous data
            new_fights = []
            for bout_id in newly_scraped_fight_data_df['fighter_bout_id'].tolist():
                if bout_id not in stored_fight_data_df['fighter_bout_id'].tolist():
                    new_fights.append(bout_id)

            if new_fights:
                # This part creates a boolean Series that indicates whether each value in the 'fighter_bout_id' column of the newly_scraped_fight_data_df DataFrame is present in the new_fights list.
                # isin(new_fights) checks each 'fighter_bout_id' against the new_fights list and returns True for rows where the 'fighter_bout_id' is in the list and False otherwise.
                new_fights_df = newly_scraped_fight_data_df[newly_scraped_fight_data_df['fighter_bout_id'].isin(new_fights)]
                body = f"{new_fights_df[['fighter_1', 'fighter_1_odds', 'fighter_2', 'fighter_2_odds']].to_string(index=False, header=False)}"

                # Append new fight data to CSV file
                append_data_to_csv(new_fights_df, csv_filename)

                # Send email update of new fight data (name of file, message body, and subject)
                send_email(csv_filename, body, "New Boxing Odds")

        time.sleep(10)  # Wait for 60 seconds before scraping again

if __name__ == "__main__":
    main()


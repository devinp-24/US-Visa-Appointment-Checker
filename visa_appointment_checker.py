import requests
from bs4 import BeautifulSoup
import schedule
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import smtplib
from email.mime.text import MIMEText
import datetime
import os

# Constants
CHECK_INTERVAL = 7 * 60  # 7 minutes
LOGIN_URL = 'https://ais.usvisa-info.com/en-ca/niv/users/sign_in'
LOGIN_EMAIL = os.environ.get('VISA_LOGIN_EMAIL', '')
LOGIN_PASSWORD = os.environ.get('VISA_LOGIN_PASSWORD', '')
FROM_EMAIL = os.environ.get('ALERT_FROM_EMAIL', '')
FROM_PASSWORD = os.environ.get('ALERT_FROM_PASSWORD', '')
TO_EMAIL_KOODO = os.environ.get('ALERT_TO_KOODO', '')
TO_EMAIL_AIRTEL = os.environ.get('ALERT_TO_AIRTEL', '')
MAX_RETRIES = 3
RETRY_BACKOFF = 10  # 10 seconds

def login():
    driver = webdriver.Chrome()
    driver.get(LOGIN_URL)

    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'user_email')))
    driver.find_element(By.ID, 'user_email').send_keys(LOGIN_EMAIL)

    driver.find_element(By.ID, 'user_password').send_keys(LOGIN_PASSWORD)

    checkbox_label = driver.find_element(By.CSS_SELECTOR, "label[for='policy_confirmed']")
    driver.execute_script("arguments[0].click();", checkbox_label)

    driver.find_element(By.NAME, 'commit').click()

    WebDriverWait(driver, 10).until(EC.url_changes(LOGIN_URL))

    try:
        continue_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.button.primary.small[href*='continue']"))
        )
        print("Logged in successfully!")
        
        driver.execute_script("arguments[0].click();", continue_button)
        print("Clicked the 'Continue' button.")
          
        # Wait for the "Schedule Appointment" option to be present
        schedule_option = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//a[contains(., 'Schedule Appointment')]"))
        )
        print("Navigated to the next page.")
        
        driver.execute_script("arguments[0].click();", schedule_option)
        print("Clicked the 'Schedule Appointment' option.")
        
        # Wait for the green "Schedule Appointment" button to be clickable
        schedule_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button.primary[href*='continue']"))
        )
                
        # Scroll into view and click the button using JavaScript
        driver.execute_script("arguments[0].scrollIntoView(true);", schedule_button)
        driver.execute_script("arguments[0].click();", schedule_button)
        print("Clicked the green 'Schedule Appointment' button using JavaScript.")
                
        consular_location_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'appointments_consulate_appointment_facility_id'))
        )
        select = Select(consular_location_select)
        select.select_by_visible_text('Vancouver')
        print("Selected 'Vancouver' from the dropdown.")

        date_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'appointments_consulate_appointment_date_input'))
        )
        date_input.click()
        print("Opened the date picker by clicking the 'Date of Appointment' input field.")

        available_date = find_first_available_date(driver)
        print(f"The first available appointment date is: {available_date}")

        send_sms(available_date)

        time.sleep(30)
        
    except Exception as e:
        print(f"Failed to log in or navigate: {e}")
        driver.quit()
        return None
    
    return driver


def find_first_available_date(driver):
    while True:
        # Get all available dates on the current calendar
        available_dates = driver.find_elements(By.XPATH, "//td/a[@class='ui-state-default']")
        
        if available_dates:
            first_available = available_dates[0]
            first_available_text = first_available.text
            parent_td = first_available.find_element(By.XPATH, "..")
            month = int(parent_td.get_attribute("data-month")) + 1
            year = int(parent_td.get_attribute("data-year"))
            date_str = f"{first_available_text} {month} {year}"
            first_available_date = datetime.datetime.strptime(date_str, "%d %m %Y")
            return first_available_date.strftime("%B %d, %Y")

        # Click the next button to move to the next month
        next_button = driver.find_element(By.CSS_SELECTOR, "a.ui-datepicker-next")
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(1)  # Add a short delay to allow the calendar to update

def send_sms(date):
    subject = "Visa Appointment Availability"
    body = f"The first available appointment date is: {date}"
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = ', '.join([TO_EMAIL_KOODO, TO_EMAIL_AIRTEL])
    
    try:
        server = smtplib.SMTP('smtp-mail.outlook.com', 587)
        server.starttls()
        server.login(FROM_EMAIL, FROM_PASSWORD)
        server.sendmail(FROM_EMAIL, [TO_EMAIL_KOODO, TO_EMAIL_AIRTEL], msg.as_string())
        server.quit()
        print("SMS sent successfully!")
    except Exception as e:
        print(f"Failed to send SMS: {e}")

def check_appointments():
    retries = 0
    backoff = RETRY_BACKOFF
    driver = None
    while retries < MAX_RETRIES:
        try:
            driver = login()
            if driver:
                driver.quit()
                return
        except Exception as e:
            print(f"Error during checking appointments: {e}")
        retries += 1
        print(f"Retrying... ({retries}/{MAX_RETRIES})")
        time.sleep(backoff)
        backoff *= 2  # Exponential backoff
    print("Max retries reached. Exiting.")

if __name__ == "__main__":
    # Schedule the job to run every CHECK_INTERVAL seconds
    schedule.every(CHECK_INTERVAL).seconds.do(check_appointments)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Script stopped by user.")

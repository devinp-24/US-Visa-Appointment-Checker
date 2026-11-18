# US Visa Appointment Checker

A Python + Selenium script that watches the US visa scheduling portal for open appointment slots at the Vancouver consulate and texts me as soon as one appears. I built it in September 2023, when appointment slots were hard to get and checking by hand meant refreshing the portal over and over.

## How it works

1. Logs into the portal and steps through the multi-step booking flow (Continue → Schedule Appointment → choose consulate).
2. Opens the date picker and pages forward month by month until it finds the first available date.
3. Sends an SMS alert to my Canadian and Indian numbers by emailing each carrier's email-to-SMS address over SMTP.
4. Repeats every 7 minutes using `schedule`.

**Reliability.** Every step waits for the page element it needs (`WebDriverWait` with expected conditions) instead of sleeping for a fixed time. Some buttons don't respond to normal clicks, so it clicks them with JavaScript. If a run fails, it retries up to 3 times, doubling the wait between attempts (10s, 20s, 40s).

## Setup

```bash
pip install selenium schedule requests beautifulsoup4
```

Credentials are read from environment variables rather than stored in the code:

```bash
export VISA_LOGIN_EMAIL="..."
export VISA_LOGIN_PASSWORD="..."
export ALERT_FROM_EMAIL="..."        # Outlook account that sends the alerts
export ALERT_FROM_PASSWORD="..."     # app password, not your main password
export ALERT_TO_KOODO="<number>@msg.telus.com"
export ALERT_TO_AIRTEL="<number>@airtelmail.com"

python visa_appointment_checker.py
```

You need Chrome installed. Recent versions of Selenium download the matching ChromeDriver automatically.

## Known limitations

- The selectors are tied to the portal's page layout as of 2023, so a site redesign would break them.
- If no date is ever available, the date search keeps paging forward without stopping.

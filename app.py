from flask import Flask, request, render_template, jsonify
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Airtable configuration
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
BASE_ID = os.getenv('BASE_ID')
EMPLOYEES_TABLE_NAME = os.getenv('EMPLOYEES_TABLE_NAME')
ATTENDANCE_TABLE_NAME = os.getenv('ATTENDANCE_TABLE_NAME')

# Airtable API URLs
EMPLOYEES_URL = f'https://api.airtable.com/v0/{BASE_ID}/{EMPLOYEES_TABLE_NAME}'
ATTENDANCE_URL = f'https://api.airtable.com/v0/{BASE_ID}/{ATTENDANCE_TABLE_NAME}'

HEADERS = {
    'Authorization': f'Bearer {AIRTABLE_API_KEY}',
    'Content-Type': 'application/json'
}

def post_to_airtable(data):
    """Post data to Airtable and return the response."""
    try:
        response = requests.post(ATTENDANCE_URL, headers=HEADERS, json=data)
        response.raise_for_status()  # Raises HTTPError for bad responses
        return response
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request failed: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        """Handle POST requests."""
        data = request.get_json()  # Get JSON data from the request
        badge_number = data.get('badgeNumber')  # Extract the badge number

        if badge_number:
            airtable_data = {
                'fields': {
                    'badgeNumber': badge_number,
                }
            }
            response = post_to_airtable(airtable_data)
            if response and response.status_code == 201:
                return jsonify({"message": "Success! Record created."}), 201
            else:
                return jsonify({"message": "Error: Could not create record."}), 500
        else:
            return jsonify({"message": "Error: Badge number is required."}), 400

    return render_template('index.html', message=None)

if __name__ == '__main__':
    app.run(debug=True, port=8003)

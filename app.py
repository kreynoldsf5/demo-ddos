import requests
from flask import Flask, jsonify, render_template
import time
import threading

app = Flask(__name__)

nginx_status_url = "http://nginx:80/nginx_status"  # NGINX stub_status URL inside Docker network

# Deques to store the last 15 minutes of data (900 seconds)
request_history = []
connection_history = []

previous_total_requests = None  # To track the previous cumulative request count

def fetch_nginx_status():
    """Fetch NGINX metrics from /nginx_status and update request and connection history."""
    global previous_total_requests
    while True:
        try:
            # Get the NGINX stub_status page
            response = requests.get(nginx_status_url)
            if response.status_code == 200:
                # Parse the response from NGINX
                status_lines = response.text.splitlines()
                
                # Extract active connections
                active_connections = int(status_lines[0].split(": ")[1])

                # Extract requests handled (cumulative)
                current_total_requests = int(status_lines[2].split()[2])

                # Calculate requests per second (RPS)
                if previous_total_requests is not None:
                    rps = current_total_requests - previous_total_requests  # Calculate RPS as the difference
                else:
                    rps = 0  # On the first iteration, we don't have previous data

                # Update the previous total requests count
                previous_total_requests = current_total_requests

                # Append metrics to history, maintaining the last 15 minutes of data
                connection_history.append(active_connections)
                request_history.append(rps)

                # Keep only the last 900 seconds of data (15 minutes)
                if len(connection_history) > 900:
                    connection_history.pop(0)
                if len(request_history) > 900:
                    request_history.pop(0)

            time.sleep(1)  # Fetch every second

        except Exception as e:
            print(f"Error fetching NGINX status: {e}")
            time.sleep(5)  # Retry after 5 seconds on failure

# Start a background thread to continuously fetch NGINX status
threading.Thread(target=fetch_nginx_status, daemon=True).start()

@app.route('/metrics')
def metrics():
    """Return metrics as JSON for the last 15 minutes."""
    return jsonify({
        'rps_last_15min': request_history,
        'cps_last_15min': connection_history
    })

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
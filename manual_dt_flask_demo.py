"""
Simple Flask web API app demonstrating manual distributed tracing instrumentation with New Relic.
"""
import newrelic.agent
from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)

@app.route('/send', methods=['POST'])
@newrelic.agent.background_task(name='send_to_queue', group='Task')
def send_to_queue():
    # Simulate creating distributed tracing headers
    with newrelic.agent.ExternalTrace('downstream_via_queue', 'RabbitMQ', method='RabbitMQ'):
      headers = []
      newrelic.agent.insert_distributed_trace_headers(headers)
      print(f"👉 Sending this header over to consumer via RabbitMQ: {headers}")
      # Convert list of tuples to dict for JSON transport
      headers_dict = dict(headers)
      # since we don't have a real message broker, we'll just send the request via http
      response = requests.post('http://127.0.0.1:5000/process', json={'headers': headers_dict})
      return jsonify({'status': 'sent', 'process_response': response.json()})

@app.route('/process', methods=['POST'])
@newrelic.agent.background_task(name='process_from_queue', group='Task')
def process_from_queue():
    data = request.get_json()
    headers_dict = data.get('headers', {})
    print(f"👈 DT Headers received: {headers_dict}")
    # Convert dict back to list of tuples for New Relic API
    headers = list(headers_dict.items())
    newrelic.agent.accept_distributed_trace_headers(headers, transport_type='AMQP')
    time.sleep(0.5)
    return jsonify({'status': 'processed'})

if __name__ == "__main__":
    app.run(debug=True)

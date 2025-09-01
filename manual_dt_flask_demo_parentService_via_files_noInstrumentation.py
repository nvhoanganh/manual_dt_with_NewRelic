"""
Simple Flask web API app demonstrating manual distributed tracing instrumentation with New Relic.
"""
from flask import Flask, request, jsonify
import uuid
import json
import os

app = Flask(__name__)

@app.route('/send', methods=['POST'])
def send_via_files():
    # generate unique correlation ID
    correlation_id = request.args.get('correlationId')
    if not correlation_id:
        return jsonify({'error': 'Missing correlationId query parameter'}), 400

    # Prepare payload
    payload = {
        'correlationId': correlation_id,
        'request_payload': request.get_json(),
    }

    # Write payload to serviceA_{correlationId}.json and serviceB_{correlationId}.json in current directory
    filenameA = f"serviceA_{correlation_id}.json"
    with open(os.path.join(os.getcwd(), filenameA), "w") as fA:
        json.dump(payload, fA)

    return jsonify({
        'status': 'dropped',
        'correlationId': correlation_id,
        'files': [filenameA]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)

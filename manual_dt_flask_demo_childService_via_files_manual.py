
"""
Background service to monitor for new JSON files with prefix 'serviceA_' in the current directory and print their content.
"""
import os
import time
import json
import newrelic.agent

prefix = "serviceA"

newrelic.agent.initialize(f"{prefix}.ini")
application = newrelic.agent.register_application(timeout=10.0)
settings = newrelic.agent.application_settings()

def generate_traceparent_from_correlation_id(correlation_id: str) -> str:
    """
    Manually constructs a W3C traceparent header using a given correlation ID.
    Args:
        correlation_id (str): A 32-character hexadecimal GUID to be used for
                              generating the trace ID and parent ID.
    Returns:
        str: The W3C traceparent header string.
             Format: 00-{trace-id}-{parent-id}-{trace-flags}
    """
    # 1. Version: Always '00' for the current W3C Trace Context specification
    version = "00"
    # 2. Trace ID: Derived directly from the provided correlation ID (32 hex characters)
    trace_id = correlation_id.lower() # Ensure it's lowercase as per W3C spec
    # 3. Parent ID: First 16 characters from the correlation ID (8 bytes)
    parent_id = correlation_id[:16].lower() # Ensure lowercase and truncate
    # 4. Trace Flags: '01' indicates sampled
    trace_flags = "01"
    # Construct the full traceparent header
    traceparent_header = f"{version}-{trace_id}-{parent_id}-{trace_flags}"
    return traceparent_header

def generate_new_tracestate(correlation_id: str, account_id: str, app_id: str) -> str:
    """
    Generates a brand new New Relic tracestate header using the provided correlation ID, account ID, and app ID.
    Args:
        correlation_id (str): A 32-character hexadecimal GUID for trace context.
        account_id (str): New Relic account ID.
        app_id (str): New Relic application ID.
    Returns:
        str: The New Relic tracestate header string.
             Format: {account_id}@nr={version}-{error_flag}-{account_id}-{app_id}-{parent_id}-{trace_id_short}-{sampled_flag}-{priority}-{timestamp}
    """
    version = "0"  # Default version for NR tracestate
    error_flag = "0"  # No error
    parent_id = correlation_id[:16].lower()
    trace_id_short = correlation_id[:15].lower()
    sampled_flag = "1"  # Sampled
    priority = "1"  # Default priority
    timestamp_ms = str(int(time.time() * 1000))
    tracestate_value = f"{version}-{error_flag}-{account_id}-{app_id}-{parent_id}-{trace_id_short}-{sampled_flag}-{priority}-{timestamp_ms}"
    tracestate_header = f"{account_id}@nr={tracestate_value}"
    return tracestate_header

def monitor_service_files(prefix="serviceA", poll_interval=1):
    print(f"Monitoring for new '{prefix}_' JSON files...")
    while True:
        files = [f for f in os.listdir(os.getcwd()) if f.startswith(f"{prefix}_") and f.endswith(".json")]
        for filename in files:
            with newrelic.agent.BackgroundTask(application, 'Queue Consume'):
                try:
                    with open(filename, "r") as f:
                        data = json.load(f)

                    correlationId = data.get('correlationId', {})

                    # generate new DT to get the tracestate
                    headers = []
                    traceparent_header = generate_traceparent_from_correlation_id(correlationId)
                    tracestate_header = generate_new_tracestate(correlationId, settings.account_id, settings.primary_application_id)

                    headers.append(('traceparent', traceparent_header))
                    headers.append(('tracestate', tracestate_header))

                    print(f"Manually re-constructed W3C Tracing Headers for Service {prefix}: {headers}")
                    result = newrelic.agent.accept_distributed_trace_headers(headers, transport_type='AMQP')
                    print(f"accept_distributed_trace_headers result: {result}")

                    print(f"[{prefix} file processed] {filename}: {data}")

                    os.remove(filename)
                    print(f"Deleted file: {filename}")
                except Exception as e:
                    print(f"Error reading or deleting {filename}: {e}")
                # No need to track seen files; all matching files are processed and deleted each loop
        time.sleep(poll_interval)

if __name__ == "__main__":
    monitor_service_files(prefix)

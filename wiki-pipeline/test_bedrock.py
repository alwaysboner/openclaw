#!/usr/bin/env python3
import boto3
try:
    print("Attempting to create Bedrock client...")
    client = boto3.client("bedrock", region_name="us-west-2")
    print("Client created. Attempting to list foundation models...")
    response = client.list_foundation_models()
    model_count = len(response.get('modelSummaries', []))
    print(f"Success! Found {model_count} models.")
    if model_count > 0:
        print("Bedrock credentials are working.")
    else:
        print("Could connect, but no models found. Check permissions.")
except Exception as e:
    print(f"An error occurred: {e}")
    print("Bedrock credential test failed.")

import os
import json
import time
import boto3
import zipfile
import botocore
import subprocess

from pathlib import Path

# Environment variables to set on aws
ENV_VARIABLES = {
    'ES_SERVER_NAME' : os.environ['ES_SERVER_NAME'],
    'ES_PORT_NUMBER' : os.environ['ES_PORT_NUMBER'],
    'ES_EMAIL_USER_NAME' : os.environ['ES_EMAIL_USER_NAME'],
    'ES_EMAIL_PASSWORD' : os.environ['ES_EMAIL_PASSWORD']
}

with open(Path.home() / ".aws" / "config", 'r') as f_in:
    content = f_in.readlines()
    for line in content:
        if line.startswith("aws_access_key_id="):
            AWS_ACCESS_KEY_ID = line.split("aws_access_key_id=")[1].rstrip()
        elif line.startswith("aws_secret_access_key="):
            AWS_SECRET_ACCESS_KEY = line.split("aws_secret_access_key=")[1].rstrip()
        elif line.startswith("region="):
            AWS_REGION = line.split("region=")[1].rstrip()
        elif line.startswith("aws_role_arn="):
            AWS_ROLE_ARN = line.split("aws_role_arn=")[1].rstrip()
        elif line.startswith("aws_lambda_function_name="):
            LAMBDA_FUNCTION_NAME = line.split("aws_lambda_function_name=")[1].rstrip()
        elif line.startswith("aws_s3_bucket_name="):
            S3_BUCKET_NAME = line.split("aws_s3_bucket_name=")[1].rstrip()
        elif line.startswith("aws_project_name="):
            PROJECT_NAME = line.split("aws_project_name=")[1].rstrip()

# Create a zip file
def create_zip(update_requirements=False):
    if Path(f'{PROJECT_NAME}.zip').exists():
        os.remove(f'{PROJECT_NAME}.zip')
    
    if update_requirements:
        # Install requirements using pip  ( pip has to be 23.1.* or below!)
        subprocess.run(["pip", "install", "-r", "requirements.txt", "-t", "requirements"])
    
    # Folders/files to be zipped
    folders_to_zip = ['sample', 'data', 'config']
    files_to_zip = ['main.py', '__init__.py']

    with zipfile.ZipFile(f'{PROJECT_NAME}.zip', 'w') as zipf:
        for folder in folders_to_zip:
            for root, _, files in os.walk(folder):
                for file in files:
                    zipf.write(os.path.join(root, file))

        for file in files_to_zip:
            zipf.write(file)

        # Add requirements to the ZIP
        for root, _, files in os.walk('requirements'):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate the relative path inside the zip file
                relative_path = os.path.relpath(file_path, 'requirements')
                zipf.write(file_path, arcname=relative_path)
    print("finished creating zip")


# Upload the zip file to S3
def upload_to_s3():
    print("uploading to s3...")
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)
    s3.upload_file(f'{PROJECT_NAME}.zip', S3_BUCKET_NAME, f'{PROJECT_NAME}.zip')


# Update Lambda function configuration with environment variables
def update_lambda_environment():
    lambda_client = boto3.client('lambda', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)
    response = lambda_client.update_function_configuration(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Timeout=60*10,  # 10 minutes maximum timeout
        Environment={
            'Variables': ENV_VARIABLES
        }
    )
    print("Environment variables set for Lambda function:", response)


# Function to update Lambda function environment variables with retry
def update_lambda_environment_with_retries(max_retries=10, retry_delay=10):
    retries = 0
    while retries < max_retries:
        try:
            update_lambda_environment()
            return  # Successfully updated, exit the loop
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceConflictException':
                print(f"Conflict encountered, this is probably due to the fact that the zip is still uploading. Retrying in {retry_delay} seconds...")
                retries += 1
                time.sleep(retry_delay)
            else:
                raise  # Re-raise the exception if it's not a conflict
    print("Exceeded maximum retries, unable to update Lambda function environment")


# Create or update the Lambda function
def create_or_update_lambda_function(function_name):
    lambda_client = boto3.client('lambda', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)
    try:
        with open(f'{PROJECT_NAME}.zip', 'rb') as zip_file:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read(),
                Publish=True
            )
        print("Lambda function updated successfully")
    except lambda_client.exceptions.ResourceNotFoundException:
        with open(f'{PROJECT_NAME}.zip', 'rb') as zip_file:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.11',
                Role=AWS_ROLE_ARN,
                Handler='main.main',
                Code={
                    'ZipFile': zip_file.read()
                },
                Publish=True
            )
        print("Lambda function created successfully")


# Invoke the Lambda function
def invoke_lambda(lambda_function_name, s3_bucket, s3_key):
    lambda_client = boto3.client('lambda', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType='RequestResponse',
        LogType='Tail',
        Payload=json.dumps({'bucket': s3_bucket, 'key': s3_key})
    )
    print(response['Payload'].read().decode('utf-8'))
    

# Main function
def main():
    create_zip(False)
    upload_to_s3()
    create_or_update_lambda_function(LAMBDA_FUNCTION_NAME)
    update_lambda_environment_with_retries()
    invoke_lambda(LAMBDA_FUNCTION_NAME, S3_BUCKET_NAME, f'{PROJECT_NAME}.zip')
    print("Project zipped, uploaded to S3, and Lambda function invoked")



if __name__ == "__main__":
    main()
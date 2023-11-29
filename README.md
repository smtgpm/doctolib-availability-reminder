# Currently only runs locally, or at least not on AWS, as AWS seem to blacklist some doctolib URLs that are necessary.

# Doctolib availability reminder

Some practitioners have a waiting time of over 6 months before you can get an appointment...
This script will parse specific practitioners by profile, or around a given address and send you an email whenever a slot opens.

please refer to `config/config.yaml` for more details on funcitonalities

# how to run
- if deployment on AWS is needed, simply run `python aws_deploy.py`
- to test / run locally, run `python main.py`
- tuning and configuration is done in `config/config.yaml`

# pre-required

## aws automated deployment
To use aws_deploy.py, you need an AWS account set up and the CLI installed. refer to aws documentation.
Personnally, I have a file in .aws/config that has 
```
aws_access_key_id=<>
aws_secret_access_key=<>
region=<>
aws_role_arn=<>
aws_lambda_function_name=<>
aws_s3_bucket_name=<>
aws_project_name=<>
```

## automated email sending
You need an email address that supports SMTP. You can create a new account on [outlook](https://signup.live.com/) since it's free and supports it.
Once that is done, you can look into sample/EmailSender.py to set it up either via a connection file, or via envirnment variables. 
I have chosen environment variables as follow
```
ES_SERVER_NAME="<>"
ES_PORT_NUMBER="<>"
ES_EMAIL_USER_NAME="<>"
ES_EMAIL_PASSWORD="<>"
```

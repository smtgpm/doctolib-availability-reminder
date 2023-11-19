"""
Class that'll allow the email reminders. For now it only supports the smtp way.
TODO: improve credentials handeling
TODO: allow other type of email sending
TODO: Error management
"""
import os
import sys
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.insert(0, "sample")
import utils

CURR_FOLDER = Path(__file__).parent.resolve()


class EmailSender:
    def __init__(self, server_name, port_number, email_user_name, email_password):
        self.logger = utils.logger
        self.server_name = server_name
        self.port_number = port_number
        self.email_user_name = email_user_name
        self.email_password = email_password
        self.mime_message = MIMEMultipart()
    
    @classmethod
    def from_file(cls, json_file):
        """
        In case you have your credentials in a json file:
        keys: server_name, port_number, email_user_name, email_password
        :param json_file : path to json file
        """
        smtp_conf_data = utils.get_file_json_data(json_file)
        if smtp_conf_data:
            server_name = smtp_conf_data['server_name']
            port_number = smtp_conf_data['port_number']
            email_user_name = smtp_conf_data['email_user_name']
            email_password = smtp_conf_data['email_password']
            return cls(server_name, port_number, email_user_name, email_password)
        else:
            raise Exception(f"couldn't initialize with json file {json_file}")

    @classmethod
    def from_env(cls):
        """
        In case you have your credentials as environment variables:
        ES_SERVER_NAME, ES_PORT_NUMBER, ES_EMAIL_USER_NAME, ES_EMAIL_PASSWORD
        """
        server_name = os.environ['ES_SERVER_NAME']
        port_number = int(os.environ['ES_PORT_NUMBER'])
        email_user_name = os.environ['ES_EMAIL_USER_NAME']
        email_password = os.environ['ES_EMAIL_PASSWORD']
        return cls(server_name, port_number, email_user_name, email_password)

    def create_email_message(self, subject, message, recipients=None):
        """
        Will create the email message object. Recipients can be multiple, should be all in
        a single string separated by commas:'foo@bar.com, foo2@bar2.com'. If None, receipients
        will be taken from environment variable ES_RECEIPIENTS.
        """
        self.mime_message['From'] = self.email_user_name
        if recipients is None:
            try:
                recipients=os.environ['ES_RECIPIENTS']
            except Exception as e:
                self.logger.error("No reciepients were given to emailSender, and couldn't fetch any from ES_RECEIPIENTS's environment variable either.")
                return False
        self.mime_message['To'] = recipients
        self.mime_message['Subject'] = subject
        # Attach the message
        self.mime_message.attach(MIMEText(message, 'plain'))
        return True

    def send_email(self):
        try:
            self.server = smtplib.SMTP(self.server_name, self.port_number)
            self.server.starttls()
            self.server.login(self.email_user_name, self.email_password)
            self.server.sendmail(self.email_user_name, self.mime_message['To'], self.mime_message.as_string())
            self.server.quit()
            self.logger.info("Email sent successfully!")
            return True
        except Exception as e:
            self.logger.error(f"Error sending email reminder: {str(e)}")
            return False

if __name__ == "__main__":
    es = EmailSender.from_env()
    if es.create_email_message(subject="Test mail", message="Here is an email for you."):
        es.send_email()
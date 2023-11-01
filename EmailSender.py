import utils
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CURR_FOLDER = Path(__file__).parent.resolve()
SMTP_CONF_FILE = CURR_FOLDER/"conf"/"email_smtp_config.json"


class EmailSender:
    def __init__(self, server_name, port_number, email_user_name, email_password):
        self.server_name = server_name
        self.port_number = port_number
        self.email_user_name = email_user_name
        self.email_password = email_password
        self.mime_message = MIMEMultipart()
        self.error = ""
    
    @classmethod
    def from_file(cls, json_file=SMTP_CONF_FILE):
        smtp_conf_data = utils.get_json_data(json_file)
        if smtp_conf_data:
            server_name = smtp_conf_data['server_name']
            port_number = smtp_conf_data['port_number']
            email_user_name = smtp_conf_data['email_user_name']
            email_password = smtp_conf_data['email_password']
            return cls(server_name, port_number, email_user_name, email_password)
        else:
            raise Exception(f"couldn't initialize with json file {json_file}")

    def create_email_message(self, subject, message, recipients):
        """
        Will create the email message object. Recipients can be multiple, should be all in
        a single string separated by commas:'foo@bar.com, foo2@bar2.com'
        """
        self.mime_message['From'] = self.email_user_name
        self.mime_message['To'] = recipients
        self.mime_message['Subject'] = subject
        # Attach the message
        self.mime_message.attach(MIMEText(message, 'plain'))

    def send_email(self):
        try:
            self.server = smtplib.SMTP(self.server_name, self.port_number)
            self.server.starttls()
            self.server.login(self.email_user_name, self.email_password)
            self.server.sendmail(self.email_user_name, self.mime_message['To'], self.mime_message.as_string())
            self.server.quit()
            print("Email sent successfully!")
        except Exception as e:
            self.error = f"Error sending email reminder: {str(e)}"
            self.trigger_error()

    def trigger_error(self):
        """
        TODO: organize error behavior
        """
        print(self.error)
        self.error = None

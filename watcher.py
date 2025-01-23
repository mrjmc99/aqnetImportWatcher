import os
import time
import shutil
import psutil
import logging
import smtplib
import html
import textwrap
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont


# Get the absolute path of the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Set up logging
log_file_path = os.path.join(script_dir, "watcher.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

# Set env files to load
script_dotenv_path = os.path.join(os.path.dirname(__file__), 'watcher.env')

# Load env files
load_dotenv(script_dotenv_path)

# Email variables
smtp_server = os.getenv("SMTP_SERVER")
smtp_port = int(os.getenv("SMTP_PORT", 25))  # Default to port 25 if not specified
smtp_username = os.getenv("SMTP_USERNAME")
smtp_password = os.getenv("SMTP_PASSWORD")
smtp_from = f"{os.environ['COMPUTERNAME']}"
smtp_from_domain = os.getenv("SMTP_FROM_DOMAIN")
smtp_recipients = os.getenv("SMTP_RECIPIENTS", "").split(",")
node_name = f"{os.environ['COMPUTERNAME']}"

# Meme Variables
successful_restart_meme_path = os.path.join('memes', os.getenv("SUCCESSFUL_RESTART_MEME")
)
unsuccessful_restart_meme_path = os.path.join('memes', os.getenv("UNSUCCESSFUL_RESTART_MEME")
)
temp_meme_path = os.path.join(script_dir, os.path.dirname('memes'), 'temp_meme.jpg')




# Function to generate meme
def generate_meme(image_path, top_text, bottom_text, output_path):
    logging.info("Generating meme...")
    try:
        # Open the image
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        # Load the TrueType font
        max_width = img.width * 0.9  # Allow a 5% margin on either side
        max_font_size = img.height // 10  # Set a maximum font size based on image height

        font_size = max_font_size
        #font = ImageFont.truetype(font_name, font_size)
        font = ImageFont.load_default(font_size)

        # Reduce font size until text fits within max_width
        def fit_text_to_width(text, font):
            while draw.textbbox((0, 0), text, font=font)[2] > max_width and font_size > 10:
                font = ImageFont.load_default(font.size - 2)
            return font

        # Adjust top text font
        font = fit_text_to_width(top_text, font)
        wrapped_top_text = textwrap.fill(top_text, width=40)

        # Draw top text
        top_y_position = 10
        draw.multiline_text(
            ((img.width - draw.textbbox((0, 0), wrapped_top_text, font=font)[2]) / 2, top_y_position),
            wrapped_top_text, fill="white", font=font, align="center"
        )

        # Adjust bottom text font
        font = fit_text_to_width(bottom_text, font)
        wrapped_bottom_text = textwrap.fill(bottom_text, width=40)

        # Draw bottom text at the bottom with a bit of padding
        bottom_y_position = img.height - draw.textbbox((0, 0), wrapped_bottom_text, font=font)[3] - 20
        draw.multiline_text(
            ((img.width - draw.textbbox((0, 0), wrapped_bottom_text, font=font)[2]) / 2, bottom_y_position),
            wrapped_bottom_text, fill="white", font=font, align="center"
        )

        # Save the meme
        img.save(output_path)
        logging.info(f"Meme saved at {output_path}")
        return output_path

    except Exception as e:
        logging.error(f"Failed to generate meme: {e}")
        raise


def send_email(smtp_recipients, subject, body, node,smtp_from_domain,smtp_server, smtp_port, meme_path=None):
    smtp_from = f"{node}@{smtp_from_domain}"
    msg = construct_email_message(smtp_from, smtp_recipients, subject, body, meme_path)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.sendmail(smtp_from, smtp_recipients, msg.as_string())
        server.quit()
        logging.info(f"Email sent to {', '.join(smtp_recipients)}")
    except Exception as e:
        logging.error(f"Email sending failed to {', '.join(smtp_recipients)}: {e}")


# Function to construct email message with an embedded image
def construct_email_message(smtp_from, smtp_recipients, subject, body, meme_path=None):
    # Create a MIMEMultipart message to handle both HTML and image content
    msg = MIMEMultipart('related')
    msg["From"] = smtp_from
    msg["To"] = ", ".join(smtp_recipients)
    msg["Subject"] = subject

    # 1) Escape the body so that any < or > won't be interpreted as HTML tags.
    safe_body = html.escape(body)

    # 2) Convert newlines to <br> for nicer formatting in HTML emails.
    safe_body_html = safe_body.replace("\n", "<br>")

    # 3) Wrap it in some HTML. You can also use <pre> if you want to preserve spacing exactly.
    html_body = f"""
    <html>
        <body>
            <p>{safe_body_html}</p>
            {"<img src='cid:meme_image' alt='Meme'>" if meme_path else ""}
        </body>
    </html>
    """

    # Attach the HTML body to the email
    msg.attach(MIMEText(html_body, 'html'))

    # Attach the image if the meme_path is provided
    if meme_path:
        with open(meme_path, 'rb') as img_file:
            meme_data = img_file.read()
            image_part = MIMEImage(meme_data)
            image_part.add_header('Content-ID', '<meme_image>')
            image_part.add_header('Content-Disposition', 'inline', filename='meme.jpg')
            msg.attach(image_part)

    return msg


def is_service_running(service_name):
    """
    Checks if a Windows service is running using psutil.
    Returns True if service is running, False otherwise.
    """
    try:
        service = psutil.win_service_get(service_name)
        return service.status() == 'running'
    except psutil.NoSuchProcess:
        return False


def find_oldest_subfolder(folder_path):
    """
    Return the subfolder (full path) in `folder_path` with the oldest creation time,
    ignoring the folder named '_invalidFiles'. Returns None if no subfolders remain.
    """
    entries = [
        entry for entry in os.scandir(folder_path)
        if entry.is_dir() and entry.name != '_invalidFiles'
    ]
    if not entries:
        return None
    entries.sort(key=lambda e: e.stat().st_mtime)
    return entries[0].path


def find_oldest_dcm_file(folder_path):
    dcm_files = []
    with os.scandir(folder_path) as it:
        for entry in it:
            if entry.is_file() and entry.name.lower().endswith('.dcm'):
                dcm_files.append(entry)
    if not dcm_files:
        return None
    dcm_files.sort(key=lambda e: e.stat().st_mtime)
    return dcm_files[0].path


def main():
    root_folder = os.getenv("ROOT_FOLDER")  # e.g. E:\AQNetCache
    if not root_folder:
        logging.error("ROOT_FOLDER is not set in .env. Exiting.")
        return

    import_folder = os.path.join(root_folder, "AQNetImport")
    old_folder = os.path.join(root_folder, "AQNetImport_old")
    os.makedirs(old_folder, exist_ok=True)

    # Gather all subfolders (ignoring _invalidFiles)
    subfolders = []
    try:
        with os.scandir(import_folder) as entries:
            for entry in entries:
                if entry.is_dir() and entry.name != '_invalidFiles':
                    subfolders.append(entry)
    except FileNotFoundError:
        logging.error(f"Import folder not found: {import_folder}. Exiting.")
        return

    if not subfolders:
        logging.info("No subfolders found in AQNetImport. Exiting.")
        return

    # Sort subfolders by modification time (oldest first)
    subfolders.sort(key=lambda e: e.stat().st_mtime)

    # Now check each subfolder in ascending order
    for subfolder in subfolders:
        oldest_dcm = find_oldest_dcm_file(subfolder.path)
        if not oldest_dcm:
            logging.info(f"No .dcm files found in {subfolder.path}. Skipping.")
            continue

        logging.info(f"Found oldest .dcm file in {subfolder.path}: {oldest_dcm}")
        logging.info("Checking if file is processed; up to 60 seconds total.")
        file_got_processed = False
        for _ in range(60):
            time.sleep(1)
            if not os.path.exists(oldest_dcm):
                logging.info("File was processed or moved. Skipping further checks.")
                file_got_processed = True
                break

        if file_got_processed:
            break  # End script as processing is working normally

        if not os.path.exists(oldest_dcm):
            logging.info(f"The file {oldest_dcm} was processed or moved. Skipping.")
            continue

        logging.warning(
            f"The file {oldest_dcm} is still present after 30 seconds. "
            f"Checking service status before moving it."
        )

        service_name = os.getenv("SERVICE_NAME")
        if not is_service_running(service_name):
            # Service is not running: send "failed" email and stop checking further subfolders
            logging.warning(f"Service '{service_name}' is NOT running. Exiting.")
            subject = f"AQNET Import is Not Processing Dicom Images on {node_name} (Service Not Running)"
            body = (
                f"AQNET Import is Not Processing DCM files (Service Not Running)\n"
                f"File: {oldest_dcm} is still waiting to be processed\n"
                f"Service {service_name} is not Running. Please investigate."
            )
            try:
                generate_meme(
                    unsuccessful_restart_meme_path,
                    "ONE DOES NOT SIMPLY",
                    f"Resume Processing Dicom Files on {node_name}",
                    temp_meme_path
                )
                logging.info(f"Sending 'service not running' email to {smtp_recipients}")
                send_email(
                    smtp_recipients, subject, body,
                    node_name, smtp_from_domain, smtp_server, smtp_port,
                    temp_meme_path
                )
                if os.path.exists(temp_meme_path):
                    os.remove(temp_meme_path)
            except Exception as e:
                logging.error(f"Failed to generate or send meme/email: {e}")

            # Stop processing other subfolders
            return

        # Service is running; move stuck file
        file_name = os.path.basename(oldest_dcm)
        destination_path = os.path.join(old_folder, file_name)
        try:
            shutil.move(oldest_dcm, destination_path)
            logging.info(f"File moved to {destination_path}")
            subject = f"AQNET Import Dicom Image Processing Restored on {node_name}"
            body = (
                f"AQNET Import Dicom Image Processing Restored on {node_name}\n"
                f"File: {oldest_dcm} was moved to the AQNETImport_old folder."
            )
            generate_meme(
                successful_restart_meme_path,
                f"AQNET Import Dicom Image Processing Restored on {node_name}",
                "",
                temp_meme_path
            )
            logging.info(f"Sending 'stuck file moved' email to {smtp_recipients}")
            send_email(
                smtp_recipients, subject, body,
                node_name, smtp_from_domain, smtp_server, smtp_port,
                temp_meme_path
            )
            if os.path.exists(temp_meme_path):
                os.remove(temp_meme_path)

        except Exception as e:
            logging.error(f"Failed to move file. Error: {e}")

    # If we finish the loop without returning, we've processed all subfolders
    logging.info("Finished checking all subfolders.")


if __name__ == "__main__":
    main()
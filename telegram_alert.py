import requests

BOT_TOKEN = "7662243037:AAFnEVl8saspHl4QcaBWePSnhe8CLSXWlvY"
CHAT_ID = "3165866"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=data)
    if response.status_code != 200:
        print(f"❌ Error al enviar mensaje: {response.text}")
    else:
        print("✅ Mensaje enviado con éxito.")

def send_telegram_file(file_path, caption="Archivo adjunto"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {
            "chat_id": CHAT_ID,
            "caption": caption
        }
        response = requests.post(url, data=data, files=files)
        if response.status_code != 200:
            print(f"❌ Error al enviar archivo: {response.text}")
        else:
            print("✅ Archivo enviado con éxito.")
import requests

def send_image_telegram(token, chat_id, image_path, caption=""):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(image_path, 'rb') as img:
        files = {'photo': img}
        data = {'chat_id': chat_id, 'caption': caption}
        r = requests.post(url, files=files, data=data)
    if r.status_code == 200:
        print("Imagen enviada correctamente")
    else:
        print(f"Error al enviar imagen: {r.text}")

def send_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message}
    r = requests.post(url, data=data)
    if r.status_code == 200:
        print("Mensaje enviado correctamente")
    else:
        print(f"Error al enviar mensaje: {r.text}")
        
def send_file(token, chat_id, file_path):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        r = requests.post(url, files=files, data=data)
    if r.status_code == 200:
        print("Archivo enviado correctamente")
    else:
        print(f"Error al enviar archivo: {r.text}")
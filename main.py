import os
from flask import Flask, request, jsonify
import speech_recognition as sr
import logging
import io
from gtts import gTTS
from playsound import playsound
import pygame
from google.cloud import dialogflow
import uuid


app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/stt', methods=['POST'])
def transcribe_audio():
    app.logger.debug("Received a request with the following files: %s", request.files)
    if 'file' not in request.files:
        app.logger.error("No file part in the request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        app.logger.error("No file selected")
        return jsonify({"error": "No selected file"}), 400

    if file:
        recognizer = sr.Recognizer()
        try:
            audio_data = sr.AudioFile(io.BytesIO(file.read()))
            with audio_data as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language='ko-KR')
            return jsonify({"transcript": text})
        except sr.UnknownValueError:
            app.logger.error("Speech recognition could not understand audio")
            return jsonify({"error": "Google Speech Recognition could not understand audio"}), 400
        except sr.RequestError as e:
            app.logger.error("Could not request results from Google Speech Recognition service: %s", e)
            return jsonify({"error": f"Could not request results from Google Speech Recognition service; {e}"}), 500
        except Exception as e:
            app.logger.exception("An unexpected error occurred")
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@app.route('/tts', methods=['POST'])
def text_to_speech():
    data = request.json
    if 'text' not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data['text']
    try:
        tts = gTTS(text=text, lang='ko')
        filename = "output.mp3"
        tts.save(filename)

        if not os.path.exists(filename):
            return jsonify({"error": "File not found after saving"}), 500

        # Initialize pygame mixer
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # Wait for the audio to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Unload the music and delete the file
        pygame.mixer.music.unload()
        os.remove(filename)

        return jsonify({"message": "Text has been converted to speech and played"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/send-message', methods=['POST'])
def send_message():
    # Dialogflow 세션 클라이언트 설정
    session_client = dialogflow.SessionsClient()

    # 요청에서 메시지 추출
    message = request.json['message']

    # Dialogflow 세션 ID와 프로젝트 ID 설정
    project_id = 'kioskdialouge'
    # UUID를 생성하여 세션 ID로 사용
    session_id = str(uuid.uuid4())
    session = session_client.session_path(project_id, session_id)

    # 텍스트 입력 설정
    text_input = dialogflow.TextInput(text=message, language_code="ko-KR")
    query_input = dialogflow.QueryInput(text=text_input)

    # Dialogflow에 요청 보내기
    response = session_client.detect_intent(session=session, query_input=query_input)
    response_text = response.query_result.fulfillment_text

    return jsonify({'reply': response_text})

if __name__ == '__main__':
    app.run(debug=True)

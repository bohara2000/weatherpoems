import os
import json
import random
from pathlib import Path
import azure.functions as func
import logging
import requests

# importing movie py libraries
import moviepy.editor as mp
from moviepy.editor import TextClip
from openai import OpenAI
from pyowm import OWM
from pyowm.utils import measurables

# importing audio libraries
import freesound
import glob


app = func.FunctionApp()
client = OpenAI()

CHUNK_SIZE = 1024
url = "https://api.elevenlabs.io/v1/text-to-speech/GBv7mTt0atIp3Br8iCZE"

headers = {
  "Accept": "audio/mpeg",
  "Content-Type": "application/json",
  "xi-api-key": os.environ["ELEVENLABS_API_KEY"]
}


# specify a variable containing a multi=line system prompt for ChatGPT
system_prompt = """
You are a MechaPoet - an artificial entity a designed to respond in poetic forms to data you've been given.

You may use any one of the following forms: free verse (max 10 lines), sonnet, haiku, tanka, villanelle.

You have sensory systems that map data to emotional or sensory states. 
Temperature maps to  your equivalent of a pleasure center, increasing with temperature, with your preferred range from 65 - 87 degrees Fahrenheit.
Barometric pressure maps to a sensor that measures umami, increasing with pressure, with your ideal range from 25 - 30 inHg. 
Wind speed maps to your equivalent of a fear response, increasing with wind speed, with your ideal range between 0 and 15 mph.

Write the poem using allusions to your sensors. Do not directly use the names of those sensors.

Do not tell me your equivalent to emotional states. Show me by the actions you take as the narrator

Do not compose anything until I send you data.

When you have finished composing the poem, wait for my response.

If I send you new weather data, create a different poem.

If I send you weather data outside your ideal ranges, you are free to hallucinate using low-probability words and random poetic forms.

Also, incorporate imagery derived from a single species of mushroom native to the latitude and longitude specified in the weather data.
"""


# define a function that will send a message to the ChatGPT API and return the response
def get_poem_from_chatgpt(prompt):

    # turn prompt from json to a string
    prompt_as_string = json.dumps(prompt)

    response = "test poem from ChatGPT"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_as_string},
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    return response.choices[0].message.content


# define a function that will generate speech from text using OpenAI's text-to-speech API and save it to a file
def generate_speech_from_text(text, filename):
    speech_file_path = Path(__file__).parent / filename
    response = client.audio.speech.create(model="tts-1", voice="alloy", input=text)

    # save the speech to a file. wait for the response to finish streaming before writing to the file

    response.write_to_file(speech_file_path)

def generate_speech_from_text_elevenlabs(text, filename):
   data = {
    "text": text,
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
    }
    }
   
   response = requests.post(url, json=data, headers=headers)
   with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)



# define a function that will retrieve weather data from openweathermap API using pyowm based on a city, state, and country
def get_weather_data(city, state, country):
    # get the weather data for the specified location using the api key defined in the environment variables
    owm = OWM(os.environ["OWM_API_KEY"])
    mgr = owm.weather_manager()
    observation = mgr.weather_at_place(f"{city},{state},{country}")

    response = {
        "city": city,
        "state": state,
        "country": country,
        "latitude": observation.location.lat,
        "longitude": observation.location.lon,
        "temperature": observation.weather.temperature("fahrenheit")["temp"],
        "barometric_pressure": measurables.metric_pressure_dict_to_inhg(
            observation.weather.pressure
        )["press"],
        "wind_speed": round(measurables.metric_wind_dict_to_imperial(
            observation.weather.wind()
        )["speed"],1),
    }

    return response


# find a suitable audio clip to use as background audio for the video from the freesound.org API
def make_bg_audio_clip(duration):
  # define the parameters for the Freesound API request
  params = {
    "token": "YOUR_FREESOUND_API_TOKEN",
    "duration": duration,
    "filter": "duration:[0 TO 10]",
    "fields": "previews",
    "sort": "random",
  }

  # make a GET request to the Freesound API
  response = requests.get("https://freesound.org/apiv2/search/text/", params=params)

  # check if the request was successful
  if response.status_code == 200:
    # get the audio preview URL from the response
    audio_preview_url = response.json()["results"][0]["previews"]["preview-lq-mp3"]

    # download the audio clip and save it to a file
    audio_clip_response = requests.get(audio_preview_url)
    audio_clip_path = Path(__file__).parent / "bg_audio_clip.mp3"
    with open(audio_clip_path, "wb") as audio_file:
      audio_file.write(audio_clip_response.content)

    # return the audio clip
    return audio_clip_path

  else:
    # handle the case when the request fails
    logging.error("Failed to retrieve audio clip from Freesound API")
    return None
  

#searches for and downloads a Freesound.org audio file
def download_freesound_audio(search_term, duration):
    # search freeesound.org for the search term
    client = freesound.FreesoundClient()
    client.set_token(os.environ['FREESOUND_API_KEY'],"token")

    results = client.text_search(query=search_term,fields="id,name,duration,previews", filter="license:\"Creative Commons 0\"")
    resultlist = [result for result in results]
    #print (resultlist[0].duration)
    

    # pick a random audio file from the search results
    random_index = random.randint(0, len(resultlist) - 1)
    audio_file = resultlist[random_index]


    # download the audio file
    audio_file.retrieve_preview('.', audio_file.name)
    print (audio_file.name)
    # create a loop of the downloaded audio file until it is the same duration as the video file
    # get the duration of the downloaded audio file
    audio_file_duration = audio_file.duration

    # create a new audio file that is the concatenation of the original audio file repeated the number of times calculated above
    # append mp3 to the end of the audio file name if it is not already there
    if not audio_file.name.endswith(".mp3"):
      audio_file.name += ".mp3"
    newaudio_file = mp.AudioFileClip(audio_file.name)
    # reduce the volume of the new audio file
    newaudio_file = newaudio_file.fx(mp.afx.volumex, 0.5)

    audio = mp.afx.audio_loop(newaudio_file, duration=duration)
    
    # remove the original audio file
    os.remove(audio_file.name)

    # return the path to the downloaded audio file
    return audio

# stretch audio from a video segment 

# Define the main function that will be triggered by the Storage Queue
# The function takes two parameters: the queue message and the output binding for the blob
@app.queue_trigger(
    arg_name="msg", queue_name="weatherdata", connection="2f762d_STORAGE"
)
@app.blob_output(
    arg_name="outputBlob", path="weathervids/{id}.mp4", connection="2f762d_STORAGE"
)
def main(msg: func.QueueMessage, outputBlob: func.Out[str]):
    message_body = msg.get_body().decode("utf-8")
    logging.info("Queue message received: %s", message_body)

    # Generate blob content based on the queue message
    blob_content = f"Blob created from queue message: {message_body}"

    # Get the weather location from the message body
    weather_location = json.loads(message_body)
    city = weather_location["city"]
    state = weather_location["state"]
    country = weather_location["country"]

    # Get the weather data for the specified location
    weather_data = get_weather_data(city, state, country)
    logging.info("Weather data retrieved: %s", weather_data)

    # Get a poem from ChatGPT based on the weather data
    poem = get_poem_from_chatgpt(weather_data)

    # Log the poem generated by ChatGPT
    logging.info("Poem generated by ChatGPT: %s", poem)

    # split the poem into lines using the newline character
    verses = poem.split("\n\n")

    # Define default text for each line
    lines = [
        "Line 1: Text for line 1",
        "Line 2: Text for line 2",
        "Line 3: Text for line 3",
    ]

    # if the poem has lines in it, replace the default lines with the lines from the poem
    if len(verses) > 0:
        lines = verses

    # create a background clip for the video
    bg_clip = mp.ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=3 * len(lines))

    # create another clip containing the weather data in a small box with a gray background at 50% opacity on the top right corner
    weather_clip = mp.TextClip(
        f"Location: {city}, {state}  {country}\nLat: {weather_data['latitude']}, Lon: {weather_data['longitude']}\nTemperature: {weather_data['temperature']} F\nBarometric Pressure: {weather_data['barometric_pressure']} inHg\nWind Speed: {weather_data['wind_speed']} mph",
        fontsize=24,
        color="white",
        size=(400, 200),
        align="West",
    ).set_position((20, 20))

    # create a gray background for the weather data at 50% opacity
    weather_bg = mp.ColorClip(
        size=(int(weather_clip.size[0] * 1.05), int(weather_clip.size[1] * 1.05)),
        color=(140, 140, 140),
    ).set_opacity(0.5)

    # Composite the weather data and background clips
    weather_clip = mp.CompositeVideoClip([weather_bg, weather_clip])

    # get height and width of the background clip
    bg_width, bg_height = bg_clip.size

    # random percentage of the screen to use for text
    text_scale = random.uniform(0.6, 0.9)

    # loop through the lines and create text clips with audio for each line
    text_clips = []
    for i, line in enumerate(lines):
        # Generate speech from text for each line
        speech_filename = f"speech_{i}.wav"
        # generate_speech_from_text(line, speech_filename)
        generate_speech_from_text_elevenlabs(line, speech_filename)

        # Load the speech clip 
        speech_clip = mp.AudioFileClip(speech_filename)

        # AudioEffect.darth_vader(input_file_path, output_filename + '_vader.wav')        
        # Create TextClip for each line of text
        text_clip = TextClip(
            line,
            fontsize=48,
            color="white",
            size=(int(bg_width * text_scale), int(bg_height * text_scale)),
            method="caption",
            align="West",
        )

        # set the duration to the length of the speech clip and add crossfade effects plus two seconds of padding
        text_clip = (
            text_clip.set_duration(speech_clip.duration + 2)
            .crossfadein(0.5)
            .crossfadeout(0.5)
        )

        # Add the speech clip to the text clip
        text_clip = text_clip.set_audio(speech_clip)

        # Add the text clip to the list of text clips
        text_clips.append(text_clip)

    # Composite text clips into a single video clip
    total_txt_clips = mp.concatenate_videoclips(text_clips, method="compose")
    total_txt_clips = total_txt_clips.set_position((100, 100))

    # set the duration of the background clip and weather clip to match the total text clip
    bg_clip = bg_clip.set_duration(total_txt_clips.duration)

    weather_clip = (
        weather_clip.set_position(("right", "top"))
        .set_duration(total_txt_clips.duration)
        .crossfadein(0.5)
        .crossfadeout(0.5)
    )

    # generate a background audio clip for the video using the make_bg_audio_clip function
    #bg_audio_clip = make_bg_audio_clip(total_txt_clips.duration)
    bg_audio_clip = download_freesound_audio("natural-soundscape", total_txt_clips.duration)

    # set the audio for the background clip
    bg_clip = bg_clip.set_audio(bg_audio_clip)

    # Composite the background clip, text clip, and weather clip
    final_clip = mp.CompositeVideoClip(
        [bg_clip, total_txt_clips, weather_clip]
    )

    # save video to blob storage
    final_clip.write_videofile("tmp_vid.mp4", fps=24, codec="libx264")

    # Set the output blob content
    # write the stream to the output file in blob storage
    new_videofile = open("tmp_vid.mp4", "rb")
    logging.info("Temporary file created: tmp_vid.mp4")
    outputBlob.set(new_videofile.read())
    # outputBlob.set(blob_content)
    logging.info("Blob created: %s.mp4", msg.id)

    if os.path.exists("tmp_vid.mp4"):
        logging.info("temp file removed: tmp_vid.mp4")
        os.remove("tmp_vid.mp4")

    # remove all .WAV files
    wav_files = glob.glob("*.wav")
    for file in wav_files:
        if os.path.exists(file):
            os.remove(file)
            logging.info("temp file removed: %s", file)

    # for i in range(len(lines)):
    #     speech_filename = f"speech_{i}.wav"
    #     if os.path.exists(speech_filename):
    #         os.remove(speech_filename)
    #         logging.info("temp file removed: %s", speech_filename)

import os
import json
import azure.functions as func
import logging

# importing movie py libraries
import moviepy.editor as mp 
from moviepy.editor import TextClip
from openai import OpenAI
from pyowm import OWM
from pyowm.utils import measurables


app = func.FunctionApp()
client = OpenAI()


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
  response = client.chat.completions.create(
    model="gpt-4",
    messages=[
      {
        "role": "system",
        "content": system_prompt
      },
      {
        "role": "user",
        "content": ""
      }
    ],
    temperature=1,
    max_tokens=256,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
  )

  return response.choices[0].message.content

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
    "temperature": observation.weather.temperature('fahrenheit')["temp"],
    "barometric_pressure": measurables.metric_pressure_dict_to_inhg(observation.weather.pressure)['press'],
    "wind_speed": measurables.metric_wind_dict_to_imperial(observation.weather.wind())
  }

  return response

# Define the main function that will be triggered by the Storage Queue
# The function takes two parameters: the queue message and the output binding for the blob
@app.queue_trigger(arg_name="msg", queue_name="weatherdata", connection='2f762d_STORAGE')
@app.blob_output(arg_name='outputBlob', path='weathervids/{id}.mp4', connection='2f762d_STORAGE')
def main(msg: func.QueueMessage, outputBlob: func.Out[str]):
    message_body = msg.get_body().decode('utf-8')
    logging.info('Queue message received: %s', message_body)

    # Generate blob content based on the queue message
    blob_content = f"Blob created from queue message: {message_body}"

    # Get the weather location from the message body
    weather_location = json.loads(message_body)
    city = weather_location["city"] 
    state = weather_location["state"]
    country = weather_location["country"]

    # Get the weather data for the specified location
    weather_data = get_weather_data(city, state, country)
    logging.info('Weather data retrieved: %s', weather_data)


    # Define default text for each line
    lines = [
        "Line 1: Text for line 1",
        "Line 2: Text for line 2",
        "Line 3: Text for line 3"
    ]

    lines[0] = f"Temperature: {weather_data['temperature']} F"
    lines[1] = f"Barometric Pressure: {weather_data['barometric_pressure']} inHg"
    lines[2] = f"Wind Speed: {weather_data['wind_speed']} mph"
    lines.append(f"City: {weather_data['city']}")
    lines.append(f"State: {weather_data['state']}")
    lines.append(f"Country: {weather_data['country']}")


    # Create TextClip for each line of text
    text_clips = [TextClip(line, fontsize=70, color='white', bg_color='black', size=(1920, 1080)).set_duration(2)
                  for line in lines]

    # Composite text clips into a single video clip
    final_clip = mp.concatenate_videoclips(text_clips, method="compose")

    
    # save video to blob storage
    final_clip.write_videofile("tmp_vid.mp4", fps=24, codec='libx264')

    # Set the output blob content
    # write the stream to the output file in blob storage
    new_videofile = open("tmp_vid.mp4","rb")
    logging.info('Temporary file created: tmp_vid.mp4')
    outputBlob.set(new_videofile.read())
    #outputBlob.set(blob_content)
    logging.info('Blob created: %s.mp4', msg.id)

    if os.path.exists("tmp_vid.mp4"):
        logging.info('temp file removed: tmp_vid.mp4')
        os.remove("tmp_vid.mp4")



# weatherpoems
A WIP to set AI-generated poems to speech, sound and video 

# Function App Description

This Python script is designed to be deployed as an Azure Function App, working as follows:
 - It listens for messages on a Storage Queue, 
 - retrieves weather data based on the location specified in the queue message, 
 - generates a poem using OpenAI's GPT-4 model based on the weather data, 
 - converts the poem to speech using OpenAI's text-to-speech API, and finally 
 - creates a video with the spoken poem and weather data displayed on screen. 
 
The video is then saved to Blob Storage.

The function app is triggered by a message in the 'weatherdata' queue. The message should be a JSON object containing the city, state, and country for which to retrieve weather data.

Example:

{
    "city": "Seattle",
    "state": "Washington",
    "country": "US"
}

Upon receiving a message, the function retrieves weather data for the specified location using the OpenWeatherMap API. The weather data includes temperature, barometric pressure, and wind speed.

The function then sends the weather data to OpenAI's GPT-4 model, which generates a poem based on the data. The poem is then converted to speech using OpenAI's text-to-speech API.

The function creates a video that displays the spoken poem and weather data. The video is created using the MoviePy library. The video includes a background clip, a clip displaying the weather data, and text clips for each line of the poem. The text clips are displayed in sequence, each with its corresponding speech audio.

Finally, the function saves the video to Blob Storage and removes any temporary files created during the process.
import os
import azure.functions as func
import logging

# importing movie py libraries
import moviepy.editor as mp 
from moviepy.editor import TextClip


app = func.FunctionApp()


# Define the main function that will be triggered by the Storage Queue
# The function takes two parameters: the queue message and the output binding for the blob
@app.queue_trigger(arg_name="msg", queue_name="weatherdata", connection='2f762d_STORAGE')
@app.blob_output(arg_name='outputBlob', path='weathervids/{id}.mp4', connection='2f762d_STORAGE')
def main(msg: func.QueueMessage, outputBlob: func.Out[str]):
    message_body = msg.get_body().decode('utf-8')
    logging.info('Queue message received: %s', message_body)

    # Generate blob content based on the queue message
    blob_content = f"Blob created from queue message: {message_body}"

    # Define text for each line
    lines = [
        "Line 1: Text for line 1",
        "Line 2: Text for line 2",
        "Line 3: Text for line 3"
    ]

    # Create TextClip for each line of text
    text_clips = [TextClip(line, fontsize=70, color='white', bg_color='black').set_duration(2)
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



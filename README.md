# Full Stack AI Meme Generator

#### Allows you to automatically generate meme images from start to finish using AI. It will generate the text for the meme (optionally based on a user-provided concept), create a related image, and combine the two into a final image file.
----------------------
<p align="center"><img src="https://github.com/ThioJoe/Full-Stack-AI-Meme-Generator/assets/12518330/2d8ee7cc-a7d3-40ca-a894-64e10085db14" width=35%></p>

## Features

- Uses models hosted on [Replicate](https://replicate.com) to generate the meme text and images.
- Combines the generated text and image into a final meme
- Allows customization of the meme generation process through various settings.
- Generates memes with a user-provided subject or concept, or you can let the AI decide.
- Logs meme generation details for future reference.

## Usage

1. For Python Version Only: Clone the repository & Install the necessary packages.
2. Obtain a Replicate API token from <https://replicate.com/account>.
3. Edit the settings variables in the settings.ini file.
4. Run the script and enter a meme subject or concept when prompted (optional).

## Settings

Various settings for the meme generation process can be customized:

- Replicate model settings: Choose the text model and temperature for generating the meme text and image prompt.
- Image model settings: Choose the model on Replicate to generate the meme image.
- Basic Meme Instructions: You can tell the AI about the general style or qualities to apply to all memes, such as using dark humor, surreal humor, wholesome, etc. 
- Special Image Instructions: You can tell the AI how to generate the image itself (more specifically,  how to write the image prompt). You can specify a style such as being a photograph, drawing, etc, or something more specific such as always using cats in the pictures.

## Example Image Output With Log
<p align="center"><img src="https://github.com/ThioJoe/Full-Stack-AI-Meme-Generator/assets/12518330/6400c973-f7af-45ed-a6ad-c062c2be0b64" width="400"></p>

```
Meme File Name: meme_2023-07-13-15-34_ZYKCV.png
AI Basic Instructions: You will create funny memes.
AI Special Image Instructions: The images should be photographic.
User Prompt: 'cats'
Chat Bot Meme Text: "When you finally find the perfect napping spot... on the laptop."
Chat Bot Image Prompt: "A photograph of a cat laying down on an open laptop."
Image Generation Platform: clipdrop
```

## Optional Arguments
### You can also pass options into the program via command-line arguments whether using the python version or exe version.

#### • API Key Arguments: Not necessary if the key is already in api_keys.ini
`--replicatekey`: Replicate API token.

#### • Basic Meme Arguments

`--userprompt`: A meme subject or concept to send to the chat bot. If not specified, the user will be prompted to enter a subject or concept.

`--memecount`: The number of memes to create. If using arguments and not specified, the default is 1.

#### • Advanced Meme Settings Arguments

`--imagemodel`: The image model to use on Replicate. If not specified, the default is 'stability-ai/sdxl'.

`--temperature`: The temperature to use for the chat bot. If using arguments and not specified, the default is 1.0.

`--basicinstructions`: The basic instructions to use for the chat bot. If using arguments and not specified, the default is "You will create funny memes that are clever and original, and not cliche or lame.".

`--imagespecialinstructions`: The image special instructions to use for the chat bot. The default is "The images should be photographic.".

#### • Binary arguments: Just adding them activates them, no text needs to accompany them

`--nouserinput`: If specified, this will prevent any user input prompts, and will instead use default values or other arguments.

`--nofilesave`: If specified, the meme will not be saved to a file, and only returned as virtual file part of memeResultsDictsList.

## How to Build Exe Yourself
#### Note: To build the exe you have to set up the python environment anyway, so by that point you can just run the python version of the script. But if you want the build the exe yourself anyway here is how:
1. Ensure required packages are installed
2. Additionally, install PyInstaller: `pip install pyinstaller` (If using a virtual environment, install it into that)
3. Run this command in terminal from within the project directory: `python -m PyInstaller main.spec`


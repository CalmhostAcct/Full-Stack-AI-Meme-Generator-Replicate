#!/usr/bin/env python3
# AI Meme Generator
# Creates memes end-to-end using models hosted on Replicate to generate the meme text and image prompt. The image and text are then combined using Pillow.
# Author: ThioJoe
# Project Page: https://github.com/ThioJoe/Full-Stack-AI-Meme-Generator
version = "1.0.5"

# Import installed libraries
import replicate
from PIL import Image, ImageDraw, ImageFont
import requests

# Import standard libraries

import warnings
import re
from base64 import b64decode
from pkg_resources import parse_version
from collections import namedtuple
import io
from datetime import datetime
import glob
import string
import os
import textwrap
import sys
import argparse
import configparser
import platform
import shutil
import traceback

# =============================================== Argument Parser ================================================
# Parse the arguments at the start of the script
parser = argparse.ArgumentParser()
parser.add_argument("--replicatekey", help="Replicate API token")
parser.add_argument("--userprompt", help="A meme subject or concept to send to the chat bot. If not specified, the user will be prompted to enter a subject or concept.")
parser.add_argument("--memecount", help="The number of memes to create. If using arguments and not specified, the default is 1.")
parser.add_argument("--temperature", help="The temperature to use for the chat bot. If using arguments and not specified, the default is 1.0")
parser.add_argument("--basicinstructions", help=f"The basic instructions to use for the chat bot. If using arguments and not specified, default will be used.")
parser.add_argument("--imagespecialinstructions", help=f"The image special instructions to use for the chat bot. If using arguments and not specified, default will be used")
# These don't need to be specified as true/false, just specifying them will set them to true
parser.add_argument("--nouserinput", action='store_true', help="Will prevent any user input prompts, and will instead use default values or other arguments.")
parser.add_argument("--nofilesave", action='store_true', help="If specified, the meme will not be saved to a file, and only returned as virtual file part of memeResultsDictsList.")
args = parser.parse_args()

# Create a namedtuple classes
ApiKeysTupleClass = namedtuple('ApiKeysTupleClass', ['replicate_key'])

# Create custom exceptions
class NoFontFileError(Exception):
    def __init__(self, message, font_file):
        full_error_message = f'Font file "{font_file}" not found. Please add the font file to the same folder as this script. Or set the variable above to the name of a font file in the system font folder.'
        
        super().__init__(full_error_message)
        self.font_file = font_file
        self.simple_message = message
        
class MissingReplicateKeyError(Exception):
    def __init__(self, message):
        full_error_message = "No Replicate API token found. Please add your Replicate token to the api_keys.ini file."

        super().__init__(full_error_message)
        self.simple_message = message

# ==============================================================================================

# Construct the system prompt for the chat bot
def construct_system_prompt(basic_instructions, image_special_instructions):
    format_instructions = f'You are a meme generator with the following formatting instructions. Each meme will consist of text that will appear at the top, and an image to go along with it. The user will send you a message with a general theme or concept on which you will base the meme. The user may choose to send you a text saying something like "anything" or "whatever you want", or even no text at all, which you should not take literally, but take to mean they wish for you to come up with something yourself.  The memes don\'t necessarily need to start with "when", but they can. In any case, you will respond with two things: First, the text of the meme that will be displayed in the final meme. Second, some text that will be used as an image prompt for an AI image generator to generate an image to also be used as part of the meme. You must respond only in the format as described next, because your response will be parsed, so it is important it conforms to the format. The first line of your response should be: "Meme Text: " followed by the meme text. The second line of your response should be: "Image Prompt: " followed by the image prompt text.  --- Now here are additional instructions... '
    basicInstructionAppend = f'Next are instructions for the overall approach you should take to creating the memes. Interpret as best as possible: {basic_instructions} | '
    specialInstructionsAppend = f'Next are any special instructions for the image prompt. For example, if the instructions are "the images should be photographic style", your prompt may append ", photograph" at the end, or begin with "photograph of". It does not have to literally match the instruction but interpret as best as possible: {image_special_instructions}'
    systemPrompt = format_instructions + basicInstructionAppend + specialInstructionsAppend
    
    return systemPrompt

# =============================================== Run Checks and Import Configs  ===============================================

# Check for font file in current directory, then check for font file in Fonts folder, warn user and exit if not found
def check_font(font_file):
    # Check for font file in current directory
    if not os.path.isfile(font_file):
        if platform.system() == "Windows":
            # Check for font file in Fonts folder (Windows)
            font_file = os.path.join(os.environ['WINDIR'], 'Fonts', font_file)
        elif platform.system() == "Linux":
            # Check for font file in font directories (Linux)
            font_directories = ["/usr/share/fonts", "~/.fonts", "~/.local/share/fonts", "/usr/local/share/fonts"]
            found = False
            for dir in font_directories:
                dir = os.path.expanduser(dir)
                for root, dirs, files in os.walk(dir):
                    if font_file in files:
                        font_file = os.path.join(root, font_file)
                        found = True
                        break
                if found:
                    break
        elif platform.system() == "Darwin":  # Darwin is the underlying system for macOS
            # Check for font file in font directories (macOS)
            font_directories = ["/Library/Fonts", "~/Library/Fonts"]
            found = False
            for dir in font_directories:
                dir = os.path.expanduser(dir)
                for root, dirs, files in os.walk(dir):
                    if font_file in files:
                        font_file = os.path.join(root, font_file)
                        found = True
                        break
                if found:
                    break

        # Warn user and exit if not found
        if not os.path.isfile(font_file):
            raise NoFontFileError(f'Font file "{font_file}" not found.', font_file)
        
    # Return the font file path
    return font_file

def parseBool(string, silent=False):
    if type(string) == str:
        if string.lower() == 'true':
            return True
        elif string.lower() == 'false':
            return False
        else:
            if not silent:
                raise ValueError(f'Invalid value "{string}". Must be "True" or "False"')
            elif silent:
                return string
    elif type(string) == bool:
        if string == True:
            return True
        elif string == False:
            return False
    else:
        raise ValueError('Not a valid boolean string')

# Returns a dictionary of the config file
def get_config(config_file_path):
    config_raw = configparser.ConfigParser()
    config_raw.optionxform = lambda option: option  # This must be included otherwise the config file will be read in all lowercase
    config_raw.read(config_file_path, encoding='utf-8')

    # Go through ini config file and create dictionary of all settings
    config = {}
    for section in config_raw.sections():
        for key in config_raw[section]:
            settingValue = config_raw[section][key]
            # Remove quotes from string values
            settingValue = settingValue.strip("\"").strip("\'")
            # Check if it is boolean
            if type(parseBool(settingValue, silent=True)) == bool:
                settingValue = parseBool(settingValue)
            config[key] = settingValue  # Do not use parseConfigSetting() here or else it will convert all values to lowercase

    return config

def get_assets_file(fileName):
    if hasattr(sys, '_MEIPASS'): # If running as a pyinstaller bundle
        return os.path.join(sys._MEIPASS, fileName)
    return os.path.join(os.path.abspath("assets"), fileName) # If running as script, specifies resource folder as /assets


def get_settings(settings_filename="settings.ini"):
    default_settings_filename = "settings_default.ini"
    def check_settings_file():
        if not os.path.isfile(settings_filename):
            file_to_copy_path = get_assets_file(default_settings_filename)
            shutil.copyfile(file_to_copy_path, settings_filename)
            print("\nINFO: Settings file not found, so default 'settings.ini' file created. You can use it going forward to change more advanced settings if you want.")
            input("\nPress Enter to continue...")
    
    check_settings_file()
    # Try to get settings file, if fails, use default settings
    try:
        settings = get_config(settings_filename)
        pass
    except:
        settings = get_config(get_assets_file(default_settings_filename))
        print("\nERROR: Could not read settings file. Using default settings instead.")
        
    # If something went wrong and empty settings, will use default settings
    if settings == {}:
        settings = get_config(get_assets_file(default_settings_filename))
        print("\nERROR: Something went wrong reading the settings file. Using default settings instead.")
        
    return settings

# Get API key constants from config file or command line arguments
def get_api_keys(api_key_filename="api_keys.ini", args=None):
    default_api_key_filename = "api_keys_empty.ini"
    
    # Checks if api_keys.ini file exists, if not create empty one from default
    def check_api_key_file():
        if not os.path.isfile(api_key_filename):
            file_to_copy_path = get_assets_file(default_api_key_filename)
            # Copy default empty keys file from assets folder. Use absolute path
            shutil.copyfile(file_to_copy_path, api_key_filename)
            print(f'\n  INFO:  Because running for the first time, "{api_key_filename}" was created. Please add your API keys to the API Keys file.')
            input("\nPress Enter to exit...")
            sys.exit()

    # Run check for api_keys.ini file
    check_api_key_file()
    
    replicate_key = ''

    try:
        keys_dict = get_config(api_key_filename)
        replicate_key = keys_dict.get('Replicate', '')
    except FileNotFoundError:
        print("Config not found, checking for command line arguments.")

    if not all(value is None for value in vars(args).values()):
        replicate_key = args.replicatekey if args.replicatekey else replicate_key

    return ApiKeysTupleClass(replicate_key)

# ------------ VALIDATION ------------

def validate_api_keys(apiKeys):
    if not apiKeys.replicate_key:
        raise MissingReplicateKeyError("No Replicate API token found.")

def initialize_api_clients(apiKeys):
    replicate_client = replicate.Client(api_token=apiKeys.replicate_key) if apiKeys.replicate_key else replicate.Client()

    return replicate_client


# =============================================== Functions ================================================

# Sets the name and path of the file to be used
def set_file_path(baseName, outputFolder):
    def get_next_counter():
        # Check existing files in the directory
        existing_files = glob.glob(os.path.join(outputFolder, baseName + "_" + timestamp + "_*.png"))

        # Get the highest existing counter, if any
        max_counter = 0
        for file in existing_files:
            try:
                counter = int(os.path.basename(file).split('_')[-1].split('.')[0])
                max_counter = max(max_counter, counter)
            except ValueError:
                pass
        # Return the next available counter
        return max_counter + 1

    # Generate a timestamp string to append to the file name
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    
    # If the output folder does not exist, create it
    if not os.path.exists(outputFolder):
        os.makedirs(outputFolder)
    
    # Get the next counter number
    file_counter = get_next_counter()

    # Set the file name
    fileName = baseName + "_" + timestamp + "_" + str(file_counter) + ".png"
    filePath = os.path.join(outputFolder, fileName)
    
    return filePath, fileName

    
# Write or append log file containing the user user message, chat bot meme text, and chat bot image prompt for each meme
def write_log_file(userPrompt, AiMemeDict, filePath, logFolder, basic, special, platform):
    # Get file name from path
    memeFileName = os.path.basename(filePath)
    with open(os.path.join(logFolder, "log.txt"), "a", encoding='utf-8') as log_file:
        log_file.write(textwrap.dedent(f"""
                       Meme File Name: {memeFileName}
                       AI Basic Instructions: {basic}
                       AI Special Image Instructions: {special}
                       User Prompt: '{userPrompt}'
                       Chat Bot Meme Text: {AiMemeDict['meme_text']}
                       Chat Bot Image Prompt: {AiMemeDict['image_prompt']}
                       Image Generation Platform: {platform}
                       \n"""))
        
        
def check_for_update(currentVersion=version, updateReleaseChannel=None, silentCheck=False):
    isUpdateAvailable = False
    print("\nGetting info about latest updates...\n")

    try:
        if updateReleaseChannel.lower() == "stable":
            response = requests.get("https://api.github.com/repos/ThioJoe/Full-Stack-AI-Meme-Generator/releases/latest")
        elif updateReleaseChannel.lower() == "all":
            response = requests.get("https://api.github.com/repos/ThioJoe/Full-Stack-AI-Meme-Generator/releases")

        if response.status_code != 200:
            if response.status_code == 403:
                if silentCheck == False:
                    print(f"\nError [U-4]: Got an 403 (ratelimit_reached) when attempting to check for update.")
                    print(f"This means you have been rate limited by github.com. Please try again in a while.\n")
                else:
                    print(f"\nError [U-4]: Got an 403 (ratelimit_reached) when attempting to check for update.")
                return None

            else:
                if silentCheck == False:
                    print(f"Error [U-3]: Got non 200 status code (got: {response.status_code}) when attempting to check for update.\n")
                    print(f"If this keeps happening, you may want to report the issue here: https://github.com/ThioJoe/Full-Stack-AI-Meme-Generator/issues")
                else:
                    print(f"Error [U-3]: Got non 200 status code (got: {response.status_code}) when attempting to check for update.\n")
                return None

        else:
            # assume 200 response (good)
            if updateReleaseChannel.lower() == "stable":
                latestVersion = response.json()["name"]
                isBeta = False
            elif updateReleaseChannel.lower() == "all":
                latestVersion = response.json()[0]["name"]
                # check if latest version is a beta. 
                # if it is continue, else check for another beta with a higher version in the 10 newest releases 
                isBeta = response.json()[0]["prerelease"]
                if (isBeta == False): 
                    for i in range(9):
                        # add a "+ 1" to index to not count the first release (already checked)
                        latestVersion2 = response.json()[i + 1]["name"]
                        # make sure the version is higher than the current version
                        if parse_version(latestVersion2) > parse_version(latestVersion):
                            # update original latest version to the new version
                            latestVersion = latestVersion2
                            isBeta = response.json()[i + 1]["prerelease"]
                            # exit loop
                            break

    except OSError as ox:
        if "WinError 10013" in str(ox):
            print(f"WinError 10013: The OS blocked the connection to GitHub. Check your firewall settings.\n")
        else:
            print(f"Unknown OSError Error occurred while checking for updates\n")
        return None
    except Exception as e:
        if silentCheck == False:
            print(str(e) + "\n")
            print(f"Error [Code U-1]: Problem while checking for updates. See above error for more details.\n")
            print("If this keeps happening, you may want to report the issue here: https://github.com/ThioJoe/Full-Stack-AI-Meme-Generator/issues")
        elif silentCheck == True:
            print(f"Error [Code U-1]: Unknown problem while checking for updates. See above error for more details.\n")
        return None

    if parse_version(latestVersion) > parse_version(currentVersion):
        if isBeta == True:
            isUpdateAvailable = "beta"
        else:
            isUpdateAvailable = True

        if silentCheck == False:
            print("----------------------------- UPDATE AVAILABLE -------------------------------------------")
            if isBeta == True:
                print(f" A new beta version is available! To see what's new visit: https://github.com/ThioJoe/Full-Stack-AI-Meme-Generator/releases ")
            else:
                print(f" A new version is available! To see what's new visit: https://github.com/ThioJoe/Full-Stack-AI-Meme-Generator/releases ")
            print(f"     > Current Version: {currentVersion}")
            print(f"     > Latest Version: {latestVersion}")
            if isBeta == True:
                print("(To stop receiving beta releases, change the 'release_channel' setting in the config file)")
            print("------------------------------------------------------------------------------------------")
            
        elif silentCheck == True:
            return isUpdateAvailable

    elif parse_version(latestVersion) == parse_version(currentVersion):
        if silentCheck == False:
            #print(f"\nYou have the latest version: " + currentVersion)
            pass
        return False
    else:
        if silentCheck == False:
            #print("\nNo newer release available - Your Version: " + currentVersion + "    --    Latest Version: " + latestVersion)
            pass
        return False
    
    return isUpdateAvailable

# Gets the meme text and image prompt from the message sent by the chat bot
def parse_meme(message):
    # The regex pattern to match
    pattern = r'Meme Text: (\"(.*?)\"|(.*?))\n*\s*Image Prompt: (.*?)$'

    match = re.search(pattern, message, re.DOTALL)

    if match:
        # If meme text is enclosed in quotes it will be in group 2, otherwise, it will be in group 3.
        meme_text = match.group(2) if match.group(2) is not None else match.group(3)
        
        return {
            "meme_text": meme_text,
            "image_prompt": match.group(4)
        }
    else:
        return None
    
# Sends the user message to the chat bot and returns the chat bot's response
def send_and_receive_message(rep_client, text_model, userMessage, conversationTemp, temperature=0.5):
    conversationTemp.append({"role": "user", "content": userMessage})

    print("Sending request to write meme...")

    prompt = "\n".join([m["content"] for m in conversationTemp])
    output = rep_client.run(
        text_model,
        input={"prompt": prompt, "temperature": temperature}
    )

    if isinstance(output, str):
        chatResponseMessage = output
    else:
        chatResponseMessage = "".join([str(x) for x in output])

    return chatResponseMessage


def create_meme(image_path, top_text, filePath, fontFile, noFileSave=False, min_scale=0.05, buffer_scale=0.03, font_scale=1):
    print("Creating meme image...")
    
    # Load the image. Can be a path or a file-like object such as IO.BytesIO virtual file
    image = Image.open(image_path)

    # Calculate buffer size based on buffer_scale
    buffer_size = int(buffer_scale * image.width)

    # Get a drawing context
    d = ImageDraw.Draw(image)

    # Split the text into words
    words = top_text.split()

    # Initialize the font size and wrapped text
    font_size = int(font_scale * image.width)
    fnt = ImageFont.truetype(fontFile, font_size)
    wrapped_text = top_text

    # Try to fit the text on a single line by reducing the font size
    while d.textbbox((0,0), wrapped_text, font=fnt)[2] > image.width - 2 * buffer_size:
        font_size *= 0.9  # Reduce the font size by 10%
        if font_size < min_scale * image.width:
            # If the font size is less than the minimum scale, wrap the text
            lines = [words[0]]
            for word in words[1:]:
                new_line = (lines[-1] + ' ' + word).rstrip()
                if d.textbbox((0,0), new_line, font=fnt)[2] > image.width - 2 * buffer_size:
                    lines.append(word)
                else:
                    lines[-1] = new_line
            wrapped_text = '\n'.join(lines)
            break
        fnt = ImageFont.truetype(fontFile, int(font_size))

    # Calculate the bounding box of the text
    textbbox_val = d.multiline_textbbox((0,0), wrapped_text, font=fnt)

    # Create a white band for the top text, with a buffer equal to 10% of the font size
    band_height = textbbox_val[3] - textbbox_val[1] + int(font_size * 0.1) + 2 * buffer_size
    band = Image.new('RGBA', (image.width, band_height), (255,255,255,255))

    # Draw the text on the white band
    d = ImageDraw.Draw(band)

    # The midpoint of the width and height of the bounding box
    text_x = band.width // 2 
    text_y = band.height // 2

    d.multiline_text((text_x, text_y), wrapped_text, font=fnt, fill=(0,0,0,255), anchor="mm", align="center")

    # Create a new image and paste the band and original image onto it
    new_img = Image.new('RGBA', (image.width, image.height + band_height))
    new_img.paste(band, (0,0))
    new_img.paste(image, (0, band_height))

    if not noFileSave:
        # Save the result to a file
        new_img.save(filePath)
        
    # Return image as virtual file
    virtualMemeFile = io.BytesIO()
    new_img.save(virtualMemeFile, format="PNG")
    
    return virtualMemeFile

def image_generation_request(rep_client, image_model, image_prompt):
    output = rep_client.run(image_model, input={"prompt": image_prompt})
    file_output = output[0] if isinstance(output, list) else output
    virtual_image_file = io.BytesIO(file_output.read())
    return virtual_image_file
    


# ==================== RUN ====================

# Set default values for parameters to those at top of script, but can be overridden by command line arguments or by being set when called from another script
def generate(
    text_model="meta/meta-llama-3-70b-instruct",
    image_model="stability-ai/sdxl",
    temperature=1.0,
    basic_instructions=r'You will create funny memes that are clever and original, and not cliche or lame.',
    image_special_instructions=r'The images should be photographic.',
    user_entered_prompt="anything",
    meme_count=1,
    font_file="arial.ttf",
    base_file_name="meme",
    output_folder="Outputs",
    replicate_key=None,
    noUserInput=False,
    noFileSave=False,
    release_channel="all"
):
    
    # Load default settings from settings.ini file. Will be overridden by command line arguments, or ignored if Use_This_Config is set to False
    settings = get_settings()
    use_config = settings.get('Use_This_Config', False) # If set to False, will ignore the settings.ini file
    if use_config:
        text_model = settings.get('Text_Model', text_model)
        temperature = float(settings.get('Temperature', temperature))
        basic_instructions = settings.get('Basic_Instructions', basic_instructions)
        image_special_instructions = settings.get('Image_Special_Instructions', image_special_instructions)
        image_model = settings.get('Image_Model', image_model)
        font_file = settings.get('Font_File', font_file)
        base_file_name = settings.get('Base_File_Name', base_file_name)
        output_folder = settings.get('Output_Folder', output_folder)
        release_channel = settings.get('Release_Channel', release_channel)
    
    # Parse the arguments
    args = parser.parse_args()

    # If API token not provided as parameter, get from config file or command line arguments
    if not replicate_key:
        apiKeys = get_api_keys(args=args)
    else:
        apiKeys = ApiKeysTupleClass(replicate_key)

    validate_api_keys(apiKeys)
    replicate_client = initialize_api_clients(apiKeys)

    # Check if any settings arguments, and replace the default values with the args if so. To run automated from command line, specify at least 1 argument.
    if args.temperature:
        temperature = float(args.temperature)
    if args.basicinstructions:
        basic_instructions = args.basicinstructions
    if args.imagespecialinstructions:
        image_special_instructions = args.imagespecialinstructions
    if args.nofilesave:
        noFileSave=True
    if args.nouserinput:
        noUserInput=True

    systemPrompt = construct_system_prompt(basic_instructions, image_special_instructions)
    conversation = [{"role": "system", "content": systemPrompt}]

    # Get full path of font file from font file name
    try:
        font_file = check_font(font_file)
    except NoFontFileError as fx:
        print(f"\n  ERROR:  {fx}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
    
    # Check for updates
    if not noUserInput:
        if release_channel.lower() == "all" or release_channel.lower() == "stable":
            updateAvailable = check_for_update(version, release_channel, silentCheck=False)
            if updateAvailable:
                input("\nPress Enter to continue...")
                
    # Clear console
    os.system('cls' if os.name == 'nt' else 'clear')

    # ---------- Start User Input -----------
    # Display Header
    print(f"\n==================== AI Meme Generator - {version} ====================")

    if noUserInput:
        userEnteredPrompt = user_entered_prompt
        meme_count = meme_count # Use default set in function parameter (1)
    
    # If any arguments are being used (or set to true for store_true arguments), skip the user input and use the arguments or defaults
    else:
        # If no user prompt argument set, get user input for prompt
        if not args.userprompt:
            print("\nEnter a meme subject or concept (Or just hit enter to let the AI decide)")
            userEnteredPrompt = input(" >  ")
            if not userEnteredPrompt: # If user puts in nothing, set to "anything"
                userEnteredPrompt = "anything"
        else:
            userEnteredPrompt = args.userprompt
        
        # If no meme count argument set, get user input for meme count
        if not args.memecount:
            # Set the number of memes to create
            meme_count = 1 # Default will be none if nothing entered
            print("\nEnter the number of memes to create (Or just hit Enter for 1): ")
            userEnteredCount = input(" >  ")
            if userEnteredCount:
                meme_count = int(userEnteredCount)
        else:
            meme_count = int(args.memecount)
            
    # ----------------------------------------------------------------------------------------------------

    def single_meme_generation_loop():
        # Send request to chat bot to generate meme text and image prompt
        chatResponse = send_and_receive_message(replicate_client, text_model, userEnteredPrompt, conversation, temperature)

        # Take chat message and convert to dictionary with meme_text and image_prompt
        memeDict = parse_meme(chatResponse)
        image_prompt = memeDict['image_prompt']
        meme_text = memeDict['meme_text']

        # Print the meme text and image prompt
        print("\n   Meme Text:  " + meme_text)
        print("   Image Prompt:  " + image_prompt)

        # Send image prompt to image generator and get image back (Using DALL·E API)
        print("\nSending image creation request...")
        virtual_image_file = image_generation_request(replicate_client, image_model, image_prompt)

        # Combine the meme text and image into a meme
        filePath,fileName = set_file_path(base_file_name, output_folder)
        virtualMemeFile = create_meme(virtual_image_file, meme_text, filePath, noFileSave=noFileSave,fontFile=font_file)
        if not noFileSave:
            # Write the user message, meme text, and image prompt to a log file
            write_log_file(userEnteredPrompt, memeDict, filePath, output_folder, basic_instructions, image_special_instructions, image_model)
        
        absoluteFilePath = os.path.abspath(filePath)
        
        return {"meme_text": meme_text, "image_prompt": image_prompt, "file_path": absoluteFilePath, "virtual_meme_file": virtualMemeFile, "file_name": fileName}
    
    # ----------------------------------------------------------------------------------------------------

    # Create list of dictionaries to hold the results of each meme so that they can be returned by main() if called from command line
    memeResultsDictsList = []

    # CORE GENERATION LOOPS
    try:
        
        for i in range(meme_count):
            print("\n----------------------------------------------------------------------------------------------------")
            print(f"Generating meme {i+1} of {meme_count}...")
            memeInfoDict = single_meme_generation_loop()

            # Add meme info dict to list of meme results
            memeResultsDictsList.append(memeInfoDict)
            
        # Once finished, print output directory path and confirm exit
        print("\n\nFinished. Output directory: " + os.path.abspath(output_folder))
        if not noUserInput:
            input("\nPress Enter to exit...")
    
    except MissingReplicateKeyError as ox:
        print(f"\n  ERROR:  {ox}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()

    except replicate.exceptions.ModelError as mx:
        print(f"\n  ERROR:  {mx}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
    
    except Exception as ex:
        # Print traceback info
        traceback.print_exc()
        print(f"\n  ERROR:  An error occurred while generating the meme. Error: {ex}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
    
    # If called from command line, will return the list of meme results
    return memeResultsDictsList

if __name__ == "__main__":
    generate()

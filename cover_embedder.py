import os
import glob
import re

#ommand_template = 'eyed3.exe --add-image="{jpgfilename}:FRONT_COVER" "{audiofilename}"'            # this one only works for mp3s
command_template = 'call add-art-to-song "{jpgfilename}" "{audiofilename}"'                         # this one uses my BAT wrapper that looks at the extension and runs a diferent BAT for mp3s than for flacs

audio_files = glob.glob('*.mp3') + glob.glob('*.flac')                                              # Get a list of all audio files (mp3 and flac) in the current folder

def find_jpg(base_filename):
    jpg_regex = re.compile(fr'{re.escape(base_filename)}[AB]?\d*\.jpg', re.IGNORECASE)
    for jpg_file in glob.glob('*.jpg'):
        if jpg_regex.match(jpg_file):
            return jpg_file
    return None

with open('embed-art.bat', 'w') as bat_file:                                                        # Open the bat file for writing
    bat_file.write("@Echo OFF\n\n")
    for audio_file in audio_files:                                                                  # Iterate over audio files
        base_filename = os.path.splitext(audio_file)[0]                                             # Get the base filename without the extension
        jpg_filename = find_jpg(base_filename)                                                      # Search for a similarly named JPG
        if jpg_filename:                                                                            # Generate the command using the template and the filenames
            command = command_template.format(jpgfilename=jpg_filename, audiofilename=audio_file)
            bat_file.write(command + '\n')                                                          # Write the command to the bat file
        else:
            print(f"     - no companion jpg: {audio_file}")

print("* You may now run embed-art.bat -- which has been freshly created. It will embed all the art.")

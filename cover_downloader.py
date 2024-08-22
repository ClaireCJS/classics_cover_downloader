"""
TITLE: Dicscogs Classics Cover Collector (CoverDownloader.py)

PURPOSE: This downloads cover art for all the mp3/flac files in your folder.

SIMPLE INSTRUCTIONS: Run, then run "get-art", edit/delete JPGs, then run wedding-party, repeat at least once, then run CoverBmedder

NICHE PURPOSE: This was specifically written for early 1900s vinyl record releases with A and B sides
               and has a lot of logic related to detecting whether the song in queston is an A or B side of the vinyl

               Thus, it will sometimes download an A & B1 image. (And even possibly, but rarely, a B2, B3, etc.)
               But only if it thinks that the song is a b-side.

               Verrrrrrrrrrrrry vinyl-specific logic within this program.

               POSSIBLE BUG: I believe if this were run on modern music, this logic would result in you getting the artwork
                             of the back of the CD in cases where you would want the artwork on the front of the CD instead
                             But I'm hoping this works well for modern music too, in case you have a folder of random songs
                      BUUUT: It seems pretty good for what modern music I tested it on, actually! [but it wasn't very much]

CONTEXT:
    It is written for the "music situation" of having a folder of a lot of different songs by different artists, such as:
        Lee Morse - Dallas Blues (1925).mp3
        Fletcher Henderson & His Orch - I'll Take Her Back If She Wants To Come Back (1925).mp3
        Henry Burr - You Forgot To Remember (1925).mp3
        Paul Whiteman & His Orch - Charleston (1925).mp3

    The assumption is the filename format is:  {artist} - {title} ({year})

    It is still designed to work if year is missing.

USAGE:
    Before: set DISCOGS_TOKEN environment variable to be your Discogs API token from https://www.discogs.com/settings/developers
    Step 1: Run this program. It creates a log file and, typically, a BAT file to WGET all the artwork.
    Step 2: Run the generated get-art.bat file. It will download all the artwork. Enjoy!
    Step 3: Manually review downloaded art and delete the inappropriate ones, crop any that are badly cropped, other edits etc
            Many different artworks will be downloaded, specifically if song is detected as a B-side or if multiple releases are tied for our match
    Clean:  Run wedding-party.py to move all the files successfully "married" to their cover art into a "married" folder.
            This is handy if you want to separate the CoverDownloader.py successess from failures.

    Repeat: Dicogs API seems to return things inconsistently.  Running again seems to get more successes!
            Look for weirdness in the flenames and maybe fix it for an increased chance of locating artwork.
            In practice, i run it about 3 times before deciding enough is enough.

    Audit:  Manually review get-art.log file to check for logic errors and bugs and to see fuzzy matching process values and other debug values
    After:  Run CoverEmbedder.py to embed our final set of JPGs into our MP3/FLACs


LITTLE UNNOTICED FEATURES:
    * Caching of redundant API calls along with statkeeping so we know how much we saved.
      Basically, multiple songs by the same artist translate to an increased successful caching frequency.
    * The Discogs API is NOT straightforward!
        * Only 100 results per request, so pagination is used
        * Only 60 requests per hour, so headers are examined to monitor remaining requests allowed, with lots of throttling pauses
        * Thousands of calls are made, so caching is employed. It hits about 5-10% of the time depending on your input data.
        * Discog searches are wonky and only the most exact matches all the way through the process will find what we want, like 5% of the time.
          So we must employ fuzzier methods. We research our music approximately 10 ways:
                # Research 1:  Search by artist                                         (sometimes has thousands of results)
                # Research 2:  Search by artist and title                               (sometimes has        no    results)
                # Research 3:  Search by title  and year                                (sometimes has    dozens of results)
                # Research 4:  Search by title                                          (sometimes has  hundreds of results, mabye thousands)
                # Research 5:  Optional Search by artist truncated after "&" and year   (sometimes has thousands of results)
                # Research 6:  Optional Search by artist with "'s" changed to "& His"   (finds results where none would be found otherwise, often    )
                # Research 7:  Optional Search by artist with "'s" changed to "& Her"   (finds results where none would be found otherwise, sometimes)
                # Research 8:  Optional Search by artist with "'s" changed to "& Their" (finds results where none would be found otherwise, seldom   )
                # Research 9+: Additional queries generated at runtime to change any "&" to " and ", as well as vice versa
          ...And gather all the results from all of these and use fuzzy logic to look for the right release via a mathematically weighted scoring algorithm
             ...Research #5 is particularly interesting in that it checks on the artist name before the first ampersand
                     This is because composers exist in the filename next to artists in a lot of downloads of these old releases, and muddy the search results.
                     i.e. "Fletcher Henderson & Gershwin" often is a filename convention for Artist="Fletcher Henderson", Composer="Gershwin",
                           so we search for "Fletcher Henderson" without the "& Gershwin" after it
    * The script outputted to download the art is actually outputted in PowerShell, unix shell, or TCC shell, based on autodetect. (But was only tested under TCC.)
    * Transforms "Orch" to "Orchestra" and "Qt" to "Quartet" prior to searching, ignores "(v1)" version notations in filenames, ignores brackted and braced text in filenames
    * All output goes to screen and logfile separately, with screen colored via ANSI codes, which are stripped prior to going to logfile

POTENTIAL BUGS:
    Raelly only thoroughly tested under the TakeCommand command-line

"""

import os
import re
import sys
import time
import builtins
import requests
from fuzzywuzzy import fuzz
from unidecode import unidecode
from colorama import Fore, Style, init
init()

# Options that would rarely be changed
PAGE_LIMIT                     = 25        #THOROUGHNESS FACTOR! The number one constant that changes the effects and speed of this program.
                                           #100*this value will be the maximum number of queried releases to try to find what we're looking for.
                                           #This value is basically how many pages-of-100-results deep we do our searches
                                               #30: started with this value, but it definitely brought irrelevant downloads when compared to 15
                                               #20: used this value for awhile
                                               #15: seems to work fine, to be honest
MAX_TIED_RESULTS_TO_CHECK      = 10        #how many tied-score (rare) releases to grab images from in the event that a tie exists
THROTTLE_TIME_AFTER_CENSURE    = 15        #how long to wait if the API starts saying "stop hammering me!" [was 13 for a long time, then 10]
THROTTLE_TIME_BETWEEN_RESEARCH = 0.1       #how long to wait before investigating each release (which is several API calls) [was 0.5 for a long time]
THROTTLE_TIME_NO_RELEASE_FOUND = 8         #how long to wait if no release found on discogs -- this isn't about API rate limiting but letting the user notice the problem

# Options that probably shouldn't change
THROTTLE_MIN_REQ_TO_HAVE_READY = 7         #definitely seen it get down to 2 even when set to 5; There was a time where not every API call was throttled which increased paranoia.
MAXIMUM_RESEARCH_ATTEMPTS      = 5         #how many times to perform out full set of research, if things don't work out. In practice it should never actually happen more than once; this is just in case.
REQUEST_TIMEOUT                = 120       #how long to let a requests.get languish; without one, it can be a permanent hang
DOWNLOAD_INTERNALLY            = False     #set to true (at your own risk) to attempt download the art internally, but it's untested and not how this is meant to be run. besides, it may be preferable to create a BAT to downoad with WGET so that you aren't hammering Discogs.com so much at the same time. This will probably break the script but if someone wants to make that part work, be my guest!
PAGINATION_SUPPORT             = True      #keep as true, set to False to run faster at the expense of more mismatches

# Constants
DISCOGS_TOKEN   = os.getenv("DISCOGS_TOKEN")
DISCOGS_API_URL = "https://api.discogs.com/database/search"
HEADERS         = {"Authorization": f"Discogs token={DISCOGS_TOKEN}",
                   "User-Agent"   :  "Discogs Classics Cover Collector (CoverDownloader.py)/1.5 (ClioCJS@gmail.com)"}                   #official version number is here, fwiw
DOWNLOAD_SCRIPT = "get-art.bat"
LOGFILE         = "get-art.log"

# Globals: OS
IS_WINDOWS = True
IS_LINUX   = False
IS_MAC     = False
OUR_SHELL  = "Unknown"

# Globals: API
API_CALLS_MADE             = 0
API_CALLS_SAVED_BY_CACHING = 0
THROTTLE_API_CALLS_LEFT    = 999
API_CACHE                  = {}
CACHE_HITS                 = 0

# Globals: Download tracking
IMAGES_FOUND         = 0
RESULTS_FOUND        = 0
DOWNLOADED_URLS      = set()                    #to keep track of downloaded URLs      so we don't download from the same URL      more than once
DOWNLOADED_FILENAMES = set()                    #to keep track of downloaded filenames so we don't download to   the same filename more than once
file                 = None








##### Custom print "framework" that includes punishing me if I forget to use primt instead of print

def print_error(*args, called_from_primt=False, **kwargs):                                                                                                             #pylint: disable=W0613
    if not called_from_primt: raise Exception("A print statement was used in the code. Use primt instead, because we want everything to go to our logfile")            #pylint: disable=W0719

original_print = print                                      # Store the original print function before overriding
builtins.print = print_error                                # Override the built-in print function with the custom one

def primt(*args, **kwargs):     #custom_print "prim print" function to print, prim and proper, to screen & logfile at the same time
    global LOGFILE

    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_arg = unidecode(arg)
            new_args.append(new_arg)
        else:
            new_args.append(arg)
    output = " ".join(map(str, new_args))

    original_print(output, **kwargs)                                    # Call the original print function that we saved before
    with open(LOGFILE, "a", encoding='utf-8') as log_file:
        log_file.write(f"{strip_ansi_codes(output)}\n")

def strip_ansi_codes(text):
    if not hasattr(strip_ansi_codes, "ansi_escape"):                                            #recompiling this regex every darnded print...
        strip_ansi_codes.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')     #...statement would have been very inefficient
    return strip_ansi_codes.ansi_escape.sub('', text)

def remove_repeating_spaces(text):
    pattern = re.compile(r" {2,}")    # This regular expression matches two or more spaces
    return pattern.sub(' ',  text)    # re.sub replaces all occurrences of the pattern in the text with a single space




def get_platform_info():
    global IS_WINDOWS, IS_LINUX, IS_MAC, OUR_SHELL
    start_time = time.monotonic()
    platform = sys.platform
    if platform.startswith('win'):          # Windows platform
        IS_WINDOWS = True
        IS_LINUX   = False
        IS_MAC     = False
    else:
        IS_WINDOWS = False
        IS_LINUX   = 'linux'  in platform
        IS_MAC     = 'darwin' in platform

    comspec = os.environ.get('COMSPEC')     # Get the command shell
    if comspec:
        if 'powershell' in comspec.lower():
            OUR_SHELL = 'PowerShell'
        elif 'tcc' in comspec.lower():
            OUR_SHELL = 'TCC'
        else:
            OUR_SHELL = 'Command Prompt'
    else:
        OUR_SHELL = 'Unknown'

    primt(f"{Fore.CYAN}{Style.BRIGHT}* Platform info:")
    primt(f"{Fore.CYAN}{Style.NORMAL}- sys.platform: {sys.platform}")
    primt(f"- os.environ.get('COMSPEC'): {comspec}")
    primt(f"- Platform: {'Windows' if IS_WINDOWS else 'Non-Windows'}")
    primt(f"- Shell: {OUR_SHELL}\n\n{Style.NORMAL}{Fore.WHITE}")
    return start_time










def delete_files_from_prevous_run():
    global DOWNLOAD_SCRIPT, LOGFILE
    if os.path.exists(DOWNLOAD_SCRIPT): delete_file_with_backup(DOWNLOAD_SCRIPT)
    if os.path.exists(LOGFILE        ): delete_file_with_backup(LOGFILE        )





def file_exists_and_nonzero_size(file_path):
    if os.path.isfile(file_path) and os.stat(file_path).st_size > 0:
        return True
    return False









def parse_filename(filename):
    filename = re.sub  (r'\[[^\]].*[^\]]*\]'             ,          '', filename)   #remove all bracketed clauses from the filename, they are not what we want
    filename = re.sub  (r'\([^\)]*\boriginal\b.*[^\)]*\)',          '', filename)   #remove any "original" in parenthesis
    filename = re.sub  (r'\([^\)]*\bTODO\b.*[^\)]*\)'    ,          '', filename)   #remove any     "TODO" in parenthesis
    filename = re.sub  (r'\{[^\}]*\bTODO\b.*[^\}]*\}'    ,          '', filename)   #                ...or in braces
    matches  = re.match(r"^(.+) - (.+?)(?: \((\d{4})\))?\.(mp3|flac)$", filename)
    if matches:
        artist = matches.group(1)
        title  = matches.group(2)
        year   = matches.group(3)
        artist = re.sub(r"\bOrch\b"     , "Orchestra", artist)
        artist = re.sub(r"\bQt\b"       , "Quartet"  , artist)
        title  = re.sub(r"\s*\(\d{4}\)$", ""         , title )                      #year shouldn't also be in title - we could in theory check if no year has been parsed, and if a year is at the end of the title like this expression implies is possible, then set the year to that match. But frankly we're not seeing failures in our testing that would indicate that we need to be so thorough here, even though this comment is overly-thorough
        return artist, title, year
    return filename, filename, None                                                 #if we match nothing, at least give them something - but no year :)













def delete_file_with_backup(filename):
    bak_index = 0
    while True:
        bak_filename = f"{filename}.bak.{bak_index:03d}"
        if not os.path.exists(bak_filename):
            os.rename(filename, bak_filename)
            break
        bak_index += 1





def does_companion_exist_OLD_tried_and_true_for_a_year(filename):
    base_filename = os.path.splitext(filename)[0]
    image_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    possible_filenames = [f"{base_filename}{s}{image_extension}"
                          for s in ["", "A", "B"] + [f"B{i}" for i in range(1, 999)]
                          for image_extension in image_extensions]
    for possible_filename in possible_filenames:
        #primt("[CA] Checking " + possible_filename)
        if file_exists_and_nonzero_size(possible_filename):
            return True
    return False



def does_companion_exist(filename):                                 #new 2024/04/19 version of function to include truncated last character situation I've run into
    base_filename_1 = os.path.splitext(filename)[0]                 #with    last charcter
    base_filename_2 = os.path.splitext(filename)[:-1]               #without last charcter
    image_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    possible_filenames = [ f"{filename_to_use}{fname_range_sfx}{image_extension}"
                          for filename_to_use in [base_filename_1, base_filename_2]
                          for fname_range_sfx in ["", "A", "B", "C"] + [f"B{i}" for i in range(1, 999)]
                          for image_extension in image_extensions]
    #primt("[PF] possible_filenames: " + possible_filenames)
    for possible_filename in possible_filenames:
        #primt("[CA] Checking " + possible_filename)
        if file_exists_and_nonzero_size(possible_filename):
            return True
    return False







def initialize_download_script():
    global DOWNLOAD_SCRIPT
    global file
    with open(DOWNLOAD_SCRIPT, "a", encoding='utf-8') as file:
        file.write('@Echo OFF\n')
        file.write('\n\n:Start\n')
        file.write('unset /q DONE_ONCE\n')
        file.write('\n\n:Retry_Point\n')


















def process_all_music_files():
    global MAXIMUM_RESEARCH_ATTEMPTS, THROTTLE_TIME_NO_RELEASE_FOUND, THROTTLE_TIME_BETWEEN_RESEARCH, THROTTLE_TIME_AFTER_CENSURE

    for filename in os.listdir("."):
        if not (filename.endswith(".mp3") or filename.endswith(".flac")):
            continue

        if does_companion_exist(filename):                                              #skip if song already has a downloaded image
            primt(f"** Companion image file for {filename} already exists and is non-zero in size. Skipping processing.")
            continue

        primt(f"*** Processing {filename}...")                                          #parse the filename
        artist, title, year = parse_filename(filename)
        primt(f"   - artist={artist},title={title},year={year}...")
        if not artist or not title:
            primt(f"Failed to extract artist and title and year from {filename}\n")
            continue

        #do our research, but keep in mind the API might fail (the code is actually unlikely to ever throw an exception here, though):
        found = False
        cover_image_url = None
        for i in range(MAXIMUM_RESEARCH_ATTEMPTS):
            if not found:
                try:
                    found = True
                    cover_image_url = search_discogs(artist, title, year, filename)
                    time.sleep(THROTTLE_TIME_BETWEEN_RESEARCH)
                except requests.exceptions.HTTPError as exception:
                    found = False
                    primt(f"[QQ](Retry #{i}) An error occurred while searching Discogs: {exception}")
                    time.sleep(THROTTLE_TIME_AFTER_CENSURE)

        if not cover_image_url:
            primt(f"{Fore.RED}{Style.BRIGHT}Failed to find release on Discogs for artist={artist},title={title}\n{Fore.WHITE}{Style.NORMAL}")
            time.sleep(THROTTLE_TIME_NO_RELEASE_FOUND)
            continue

        cover_image_filename = f"{os.path.splitext(filename)[0]}.jpg"
        primt(f"{Fore.GREEN}* Located cover art for artist={artist},title={title},year={year} as {cover_image_filename}{Fore.WHITE}")












def sanitize_title(title):
    patterns_to_remove = [                                      # Remove patterns of things we don't want in our title
        r" *\(v\d+\)",                                                # matches (v1), (v2), etc.
        r" *\(original\)",                                            # matches (original)
        r"\{.*?\}",                                                   # matches {any text in braces like this}
        r" *\(hissy\)",                                               # matches (hissy)
        r" *\([a-z]+ hissy\)",                                        # matches (very hissy), (slightly hissy), etc.
    ]                                                           # Remove patterns of things we don't want in our title
    for pattern_to_remove in patterns_to_remove:                # Remove patterns of things we don't want in our title
        title = re.sub(pattern_to_remove, '', title)            # Remove patterns of things we don't want in our title

    if title.endswith('_'): title = title[:-1] + '?'            # Replace "_"  at  the  end  with "?"   because that's what that means in *our* music filenames
    title = re.sub(r"\s*--\s*", " / ", title)                   # Replace "--" between words with " / " because that's what that means in *our* music filenames

    return title


def maybe_get_year_from_title(year, title):
    if not year or year == "":                                                                      #fetch year from title if it is mistakenly in the title (which can happen due to Discogs data entry error)
        match = re.search(r"\s*\((\d{4})\) *$", title)
        if match:
            year = match.group(1)
            title = re.sub(r"\s*\(\d{4}\) *$", "", title)
    return year, title


def search_discogs(artist, title, year, filename, pass_num=1):
    global MAX_TIED_RESULTS_TO_CHECK
    results         = []
    response        = None
    cover_image_url = None

    ## preserve arguments for safer recursion
    original_artist   = artist
    original_title    = title
    original_year     = year
    original_filename = filename

    ## Titles require a bit of special logic, mostly related to the year accidentally creeping into our title
    year, title = maybe_get_year_from_title(year,title)
    title       = sanitize_title(title)                                                             # removes "(v1)" "(v2)"

    ## Ampersands require special logic so that they don't block a good match score
    artist_before_ampersand = artist.split('&')[0]                                                  # get artist segment before first "&" because sometimes those are composers or that artist has worked with multiple other artists, and this muddies the results
    artist_has_ands_or_amps = False                                                                 # get artist segment before first "&" because sometimes those are composers or that artist has worked with multiple other artists, and this muddies the results
    if artist_before_ampersand is None or artist_before_ampersand == "":                            # get artist segment before first "&" because sometimes those are composers or that artist has worked with multiple other artists, and this muddies the results
        artist_before_ampersand = artist.split(' and ')[0]                                          # get artist segment before first "&" because sometimes those are composers or that artist has worked with multiple other artists, and this muddies the results
        artist_has_ands_or_amps = True                                                              # get artist segment before first "&" because sometimes those are composers or that artist has worked with multiple other artists, and this muddies the results

    ## Apostrophe-s'es require special logic so that they don't block a potential 100% match score,
    ## because sometimes we need to expand "'s" to "& His", "& Her", or "& Their" to get a 100% match
    artist_has_apostrophe_s = False
    for apostrophe_s_pattern in [r"\bs'\b", r"\b's\b"]:
        match = re.search(apostrophe_s_pattern, artist)
        if match:
            artist_has_apostrophe_s = True
            artist_with_apostrophe_transform_m = re.sub(apostrophe_s_pattern, " & His"  , artist)
            artist_with_apostrophe_transform_f = re.sub(apostrophe_s_pattern, " & Her"  , artist)
            artist_with_apostrophe_transform_n = re.sub(apostrophe_s_pattern, " & Their", artist)

    ## Now that we know things, generate a proper set of research queries based on what we know.... #### First, our static queries:
    research_queries = [{"artist": artist                 },                                        # Research 1: Search by artist
                        {"artist": artist , "title": title},                                        # Research 2: Search by artist and title
                        {"title" : title  , "year" : year },                                        # Research 3: Search by title  and year
                        {"title" : title                  }]                                        # Research 4: Search by title
                                                                                                    #### Then, our dynamic queries:
    if artist_has_ands_or_amps: research_queries.append({"q":artist_before_ampersand           })   # Research 5: Search by artist truncated after "&" and year
    if artist_has_apostrophe_s: research_queries.append({"q":artist_with_apostrophe_transform_m})   # Research 6: Search by artist with "'s" changed to "& His"
    if artist_has_apostrophe_s: research_queries.append({"q":artist_with_apostrophe_transform_f})   # Research 7: Search by artist with "'s" changed to "& Her"
    if artist_has_apostrophe_s: research_queries.append({"q":artist_with_apostrophe_transform_n})   # Research 8: Search by artist with "'s" changed to "& Their"
                                                                                                    # Research 9+:generated at runtime below to change "&" to " and " and vice versa

    processed_queries = set()                                 #go through each of our queries and make sure "&" and "and" are properly cross-checked
    for query in research_queries:                            #go through each of our queries and make sure "&" and "and" are properly cross-checked
        for annnd in ["&", " and "]:                          #the spaces before/after and are very important if you don't want to match Ferdinand or Andy! Though it prevents the subtitution from working if "And" the first or last word, which is possibly a slight cost, but not a cost great enough to warrant fixing this with more complicated code. I think if a band starts with the word And they far less likely to use an ampersand there
            if annnd in query.get("artist", "") or annnd in query.get("title", "") or annnd in query.get("q", ""):
                query_with_and = {k: remove_repeating_spaces(v.replace(annnd, " and ")) if isinstance(v, str) else v for k, v in query.items()}
                query_with_amp = {k: remove_repeating_spaces(v.replace(annnd, " & "  )) if isinstance(v, str) else v for k, v in query.items()}
                response  =  get_api_results_unique(query_with_and, processed_queries, results, response)
                response  =  get_api_results_unique(query_with_amp, processed_queries, results, response)
            else:
                response  =  get_api_results_unique(query,          processed_queries, results, response)

    results = sort_results_with_fuzzy_logic(results,title,artist,year,artist_before_ampersand,filename,artist_has_ands_or_amps,pass_num=pass_num)          # sort results by many fuzzy sort crtieria
    if not results: return None

    # the old method was to just look at the topmost result:
    #cover_image_url = results[0].get("cover_image")                        # get cover image
    #primt(f"  [RRRR] results[0]   is {str(results[0])}")
    #primt(f"  [RRRR] len(results) is {len(results)}"   )
    highest_score = results[0]["score"]  # Assuming the "score" key stores the fuzzy match score

    # but the new method is to process the first N results with the same tied-highest score, because ties happen, and sometimes the artwork is only in one instance
    found_images = False
    for i, result in enumerate(results[:MAX_TIED_RESULTS_TO_CHECK]):
        primt(f"  {Fore.BLUE}[TIEDRESULT] results[{i}] is {str(results[i])}")
        if result["score"] != highest_score: break

        cover_image_url = result.get("cover_image")

        if cover_image_url:
            primt(f"  {Fore.CYAN}[TIEDRESULT] cover_image_url   found: {cover_image_url}")
            if cover_image_url.endswith(".gif"):
                cover_image_url = None                         # If the cover_image_url ends with ".gif", don't use it
            else:
                found_images = True

            #would make more sense actually: consider making this a list: cover_image_urls.append(cover_image_url)
        else:
            primt(f"  {Fore.RED}{Style.BRIGHT}[TIEDRESULT] cover_image_url not found!{Style.NORMAL}")

        cover_image_url_b = search_and_download_bside_images([result], filename, response)
        if cover_image_url_b: found_images = True
        primt(f"  {Fore.CYAN}[TIEDRESULT] cover_image_url_b found: {cover_image_url_b}")

        tmp_filename = filename
        if cover_image_url:
            #would make more sense actually: consider making this a list: cover_image_urls.append(cover_image_url)
            if cover_image_url_b: tmp_filename = modify_filename_with_letter(filename, "A")
            found_images = True
            download_image(cover_image_url, tmp_filename)

    if found_images: return cover_image_url    #would make more sense actually: consider making this a list: return cover_image_urls if cover_image_urls else None

    #if we ended up with no results (no cover_image_url) at this point, make a 2nd pass of consideration to use our 2nd-pass formula
    if pass_num == 2: return None
    primt(f"{Fore.YELLOW}{Style.BRIGHT}* Attempting 2nd pass at results...{Style.NORMAL}")
    return search_discogs(original_artist, original_title, original_year, original_filename, pass_num=2)









def get_api_results_unique(query, processed_queries, results, response):
    query_tuple = tuple(query.items())
    if query_tuple not in processed_queries:
        response = get_api_results(query, results, response)
        processed_queries.add(query_tuple)
    return response


def get_api_results(params, results, response, resource_url=None):
    global API_CACHE, API_CALLS_MADE, API_CALLS_SAVED_BY_CACHING, CACHE_HITS, PAGINATION_SUPPORT, THROTTLE_API_CALLS_LEFT, RESULTS_FOUND, PAGE_LIMIT

    primt(f"{Fore.RED}{Style.BRIGHT}    ...Making API call: params={str(params)}{Style.NORMAL}{Fore.WHITE}")

    url_to_call = ""
    paging_applicable = True
    cache_key = str(params) + str(resource_url)  # Generate a cache key
    api_calls_made_for_this_call = 0
    if cache_key not in API_CACHE:
        paging_applicable, url_to_call, params = handle_paging(paging_applicable,resource_url,url_to_call,params)

        page = 1
        has_more_pages = True  # not *really* necessarily true at this point
        while has_more_pages and page <= PAGE_LIMIT:
            if paging_applicable: params["page"] = page
            try:
                response = requests.get(url_to_call, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                API_CALLS_MADE += 1
                api_calls_made_for_this_call += 1
                throttle_api_request_rate_if_necessary(response)
                primt(f"       {Fore.GREEN}{Style.NORMAL}...Response is: params={str(response)}")
            except requests.exceptions.HTTPError as exception:
                primt(f"\n\n{Fore.RED}{Style.BRIGHT}** HTTP error occurred: {exception}")
                time.sleep(THROTTLE_TIME_AFTER_CENSURE*2)
                continue
            except Exception as e:
                primt(f"\n\n{Fore.RED}{Style.BRIGHT}** General exeption error occurred: {exception}")
                time.sleep(THROTTLE_TIME_AFTER_CENSURE*2)
                continue


            if response is None or "results" not in response.json(): return response
            json_data = response.json()
            current_results = json_data["results"]
            RESULTS_FOUND += len(current_results)
            results.extend(current_results)

            pagination   = json_data["pagination"]                                                     # ...Pagination logic because
            total_pages  = pagination["pages"]                                                         # Discogs API will only return
            current_page = pagination["page"]                                                          # a max of 100 results at a time
            has_more_pages = current_page < total_pages                                                # ...pagination logic
            page += 1                                                                                  # ...pagination logic
            if (page > 1 and not PAGINATION_SUPPORT) or (page >= PAGE_LIMIT): has_more_pages = False   # ...pagination logic
            throttle_api_request_rate_if_necessary(response,results,current_results)

        primt (f"{Fore.MAGENTA}* Storing call to API_CACHE[key={cache_key}] = (current_results, response.headers, api_calls_made_for_this_call={api_calls_made_for_this_call})")
        API_CACHE[cache_key] = (current_results, response.headers, api_calls_made_for_this_call)       # Cache the results & store how many API calls this cache will save for future statistical bragging rights

    else:
        current_results, _, api_calls_made_for_that_call = API_CACHE[cache_key]                        #don't end up needing/using response_headers
        results.extend(current_results)
        CACHE_HITS += 1
        if api_calls_made_for_that_call: API_CALLS_SAVED_BY_CACHING += api_calls_made_for_that_call
        else:                            API_CALLS_SAVED_BY_CACHING += 1
        primt(f"    {Fore.GREEN}{Style.BRIGHT}...Skipped because cached! (cache hit #{Fore.CYAN}{CACHE_HITS}{Fore.GREEN}, saving {Fore.CYAN}"
            + f"{api_calls_made_for_that_call}{Fore.GREEN} API calls, total saved now={Fore.CYAN}{Style.BRIGHT}{API_CALLS_SAVED_BY_CACHING}"
            + f"{Fore.GREEN}{Style.NORMAL})")
        time.sleep(1)                                                                                  #give us a second to bask in the good feeling the successful cache hit message

    return response


def handle_paging(paging_applicable,resource_url,url_to_call,params):
    paging_applicable = True
    if resource_url is None:
        url_to_call = DISCOGS_API_URL
        params["per_page"] = 100                           #no reason to ever have this less than the maximum allowable value of 100
        paging_applicable = True
    else:
        paging_applicable = False
        url_to_call = resource_url
        if "per_page" in params: del params["per_page"]
        if "page" in params: del params["page"]
    return paging_applicable, url_to_call, params




def throttle_api_request_rate_if_necessary(response,results=["{unpassed}"],current_results=["{unpassed}"]):                             # pylint: disable=W0102
    #response is the only actionable/truly required parameter, others are for cosmetics & will be substituted with dummy parameters if none are passed
    global THROTTLE_API#_CALLS_LEFT, THROTTLE_MIN_REQ_TO_HAVE_READY

    primt(f"{Fore.BLUE   }          ...Response to API call #{Style.BRIGHT}{API_CALLS_MADE}{Style.NORMAL}:   response={str(response.headers)}")
    if current_results != ["{unpassed}"]: primt(f"{Fore.CYAN   }           ...Results to API call #{Style.BRIGHT}{API_CALLS_MADE}{Style.NORMAL}: {len(current_results)} current_results={str(current_results)}")
    if         results != ["{unpassed}"]: primt(f"{Fore.MAGENTA}          ...Total results now: {Style.BRIGHT}{len( results )}{Style.NORMAL}")
    ratelimit_perminute     = response.headers.get('X-Discogs-Ratelimit'          )
    ratelimit_used          = response.headers.get('X-Discogs-Ratelimit-Used'     )
    THROTTLE_API_CALLS_LEFT = response.headers.get('X-Discogs-Ratelimit-Remaining')
    if THROTTLE_API_CALLS_LEFT:
        primt(f"       {Fore.BLUE}{Style.BRIGHT}...Remaining API calls: {Fore.GREEN}{Style.BRIGHT}{ratelimit_used}"
                   + f"{Fore.BLUE}{Style.BRIGHT} used in last minute, {Fore.YELLOW}{THROTTLE_API_CALLS_LEFT} "
                   + f"{Fore.BLUE}{Style.BRIGHT}remaining [{ratelimit_perminute}pm] [total made={Fore.CYAN}{Style.BRIGHT}{API_CALLS_MADE}"
                   + f"{Fore.BLUE}{Style.BRIGHT}] [total saved via caching={Style.BRIGHT}{Fore.CYAN}{API_CALLS_SAVED_BY_CACHING}"
                   + f"{Fore.BLUE}{Style.BRIGHT}] {Fore.WHITE}")
        if int(THROTTLE_API_CALLS_LEFT) <= THROTTLE_MIN_REQ_TO_HAVE_READY: time.sleep(THROTTLE_TIME_AFTER_CENSURE)
    else:
        primt(f"{Fore.RED}{Style.BRIGHT} *** ERROR: Not getting response from Discogs stating how many API calls are left.")
        time.sleep(THROTTLE_TIME_AFTER_CENSURE*2)


















def sort_results_with_fuzzy_logic(results, title, artist, year, artist_before_ampersand, filename, artist_has_ands_or_amps, pass_num=1):                                        #pylint: disable=R0912,R0913
    #original_results = results
    primt(f"\t{Fore.MAGENTA}- Called: sort_results_with_fuzzy_logic(results, title={title}, artist={artist}, year={year}, artist_before_ampersand={artist_before_ampersand}, filename={filename}, artist_has_ands_or_amps={artist_has_ands_or_amps}, pass_num={pass_num})")
    if not results:
        primt(f"\t{Fore.YELLOW}- Hmm. Calling sort_results_with_fuzzy_logic had a quick return due to null results.")
        return results
    #else:
        #DEBUG: primt(f"\n{Fore.MAGENTA}{len(results)} Current incoming results "  )
        #DEBUG: display_results(results)

    for result in results:
        #DEBUG: primt(f"\n\t{Fore.GREEN}dealing with results: {str(result)} "  )

        if "artisttitle" not in result: result["artisttitle"] = ""                # Assign an empty string to 'artisttitle' if it does not exist

        #swap the current title into a field called artisttitle that is more accurately named to represents what it is, but don't do it
        #if it's already been done, since we may be recursing into here a 2nd time and dealing with a previously-massaged data structure
        if result["title"] != "":
            result["artisttitle"] = result["title"]                               #"Metallica - One / The Prince" #this field is actually "artist - title" because of the sloppy way Discogs does it, so we store it back into the data structure just to make things less ambiguous internally
            result["title"]       = ""                                            #leave this in so we know our results are processed ;)

        #extract our values for parsed_artist and parsed_title
        if " - " in result["artisttitle"]:                                        #separate "artist - title" into artist & title if there's a hyphen
            split_artist_title = result["artisttitle"].split(" - ")
            parsed_artist =            split_artist_title[0 ] .strip()
            parsed_title  = ' - '.join(split_artist_title[1:]).strip()
        else:
            parsed_artist = result["artisttitle"].strip()                         #if there is not a hyphen (which shouldn't happen), just do our best
            parsed_title  = result["artisttitle"].strip()

        if parsed_artist.endswith("*"): parsed_artist = parsed_artist[:-1]        #remove the last character if it's an apostrophe, because Discogs returns them that way sometimes
        title_before_slash = parsed_title
        title_after_slash  = parsed_title

        #deal with splitting slashes for b sides such as "Song 1 / song 2 / with / slashes / in / it" - we do it on the last slash but it really shoudln't have more than one
        is_b_side = False                                                         #DEBUG: primt(f"[RT1] parsed_artist/title is {parsed_artist} and {parsed_title}")
        before_slash_score, after_slash_score = -1, -1
        split_title = set()
        if " / " in parsed_title:
            split_title = parsed_title.split(" / ")                               #"One", "The Prince"
            title_before_slash = ' / '.join(split_title[:-1]).strip()
            title_after_slash  =            split_title[ -1] .strip()
            if title.lower() in title_after_slash.lower():                        # this match fails when the song title is not exact
                is_b_side = True
                before_slash_score, after_slash_score = 0, 100                    # it turns out that when the year is missing, the best thing to do is to set the match to 100 and not ding any match points for the missing year

        #start to calculate our fuzzy matching scores, starting with the most basic ones:
        before_slash_score = fuzz.token_set_ratio(title, title_before_slash)
        after_slash_score  = fuzz.token_set_ratio(title, title_after_slash )
        is_b_side = after_slash_score > before_slash_score and after_slash_score > 55

        #Get a title-match score for our title, versus this result's varoius sub-titles:
        #       (1) the discogs full title
        #       (2) the before-slash section of a slashed title
        #       (3) the  after-slash section of a slashed title
        #Then take the highest match score out of all of those, and use that as our title match score.
        #GOATGOATGOATGOATGOATUPDATEDOCUMENTATIONABOUTRESEARCHTPESDONE
        title_scores = [fuzz.token_set_ratio(title, t) for t in [parsed_title, title_before_slash, title_after_slash]]              #parsed_title was originally result["title"] which is really result["artisttitle"] which is "artist - title", but now parsed_title attempts to just be the title
        title_score = max(title_scores)

        #Get a artist-match for this result's artist vs:
        #       (1) the artist we are looking for
        #       (2) the artist we are looking for, but only the part before any ampersand
        #       (3) the artist we are looking with ampersand substituted for and        \____ possibly the same thing
        #       (4) the artist we are looking with and substituted for ampersand        /
        #GOATGOATGOATGOATGOATUPDATEDOCUMENTATIONABOUTRESEARCHTPESDONE
        artist_score_og  = fuzz.token_set_ratio(artist, parsed_artist)                                         #1                   #parsed_artist was result["title"] is really result["artisttitle"] which is "artist - title", parsed_artist attempts to just be the artist
        if artist_has_ands_or_amps:
            artist_score_ba  = fuzz.UWRatio        (artist, artist_before_ampersand)                           #2                   #UWRatio combines all the different types of fuzzy comparisons into one weighted average that works better in general
            artist_score_amp = fuzz.token_set_ratio(artist, artist.replace(" and ", " & "))                    #3
            artist_score_and = fuzz.token_set_ratio(artist, artist.replace(  "&"  , "and"))                    #4
            artist_scores    = [artist_score_og, artist_score_ba, artist_score_and, artist_score_amp]
            artist_score     = max(artist_scores)
        else:
            artist_score_ba  = -1
            artist_score_and = -1
            artist_score_amp = -1
            artist_scores    = []
            artist_score     = artist_score_og

        #Year result should not be character-by-character as the way the library would compute by default, because then 1924 would be considered 75% match to 1925
        #We declare that 1924 should be considered a 99% match to 1925.  Our frame of reference being 1 year = 1%, this means we'd have to be 100 yrs off for 0% match.
        #Perhaps in retrospect that is too generous, but due to the way this score is weighted and dealt with in subsequent code and how much testing has been done,
        #we dare not change this.
        tmp_year = result.get("year", "N/A")
        if tmp_year in ("N/A", "", None) or year in ("N/A", "", None):
            if artist_score > 55: year_score = 100                                             #if artist is close enough, don't ding for the year missing
            else:                 year_score = ((title_score * 1) + (artist_score *  3))/4     #otherwise just make the year score be a weighted average of the other scores which matches the weighting of our master weighting formula below
        else:
            year_score = year_similarity_score(year,tmp_year)

        #It's hard to really have a right answer for this formula without spending ages developing a lot of test suites
        #This formula:
        #otal_score = (title_score * 1) + (artist_score * 3) + (year_score * 2)                                                          #master weighting formula
        #...worked really well and was based on the fact that the artist was way more important than the title.                          #master weighting formula
        #However, when dealing with artists like Ted Lewis And His Orchestra we also search "Ted Lewis" and that                         #master weighting formula
        #give a lower match to the artist score which bumps some songs' scores down too low.                                             #master weighting formula
        total_score_pass_1 = (title_score * 1 ) + (artist_score * 3 ) + (year_score * 2)                                                 #master weighting formula
        total_score_pass_2 = (title_score * 10) + (artist_score * 30)                                                                    #2nd pass formula for if our 1st pass finds nothing.  We found a case where everything was right but the year was 25 yrs later but it was the sole art on Discogs, which made us realize we need a 2nd pass of consideration if the 1st pass fails
        #DEBUG: primt(f"\t  {Fore.YELLOW}...[pass={pass_num}] title_score: {title_score}, artist_score: {artist_score}, total_score_pass_1: {total_score_pass_1}, total_score_pass_2: {total_score_pass_2}")

        result.update(
            filename                =          filename        ,
            is_b_side               =          is_b_side       ,
            tmp_year                =           tmp_year       ,                              #for debugging purposes
            score_year              =         year_score       ,
            score                   =        total_score_pass_1,
            score_2                 =        total_score_pass_2,
            score_artist            =       artist_score       ,
            score_artist_og         =       artist_score_og    ,
            score_artist_ba         =       artist_score_ba    ,
            score_artist_and        =       artist_score_and   ,
            score_artist_amp        =       artist_score_amp   ,
            score_title             =        title_score       ,
            score_slash_before      = before_slash_score       ,
            score_slash_after       =  after_slash_score       ,
            original_artist         =             artist       ,
            parsed_artist           =      parsed_artist       ,
            original_title          =              title       ,
            parsed_title            =       parsed_title       ,
            title_before_slash      = title_before_slash       ,
            title_after_slash       =  title_after_slash       ,
            artist_has_ands_or_amps =   artist_has_ands_or_amps,
            artist_before_ampersand =   artist_before_ampersand,
        )

    if pass_num==1: sortKey = "score"
    if pass_num==2: sortKey = "score_2"
    #esults.sort(key=lambda r: r["score"], reverse=True)                                   #sort the results with fuzzy logic
    results.sort(key=lambda r: r[sortKey], reverse=True)                                   #sort the results with fuzzy logic
    display_results(results)

    return results


def year_similarity_score(year1, year2):
    #primt(f"            ..[YSS]year_similarity_score(year1={year1},year2={year2})")
    max_difference = 100                                                                   #set to match same value as our fuzzy match library

    int_year1 = int(year1)
    int_year2 = int(year2)

    difference = abs(int_year1 - int_year2)
    score = (1 - (difference / max_difference)) * 100
    return score










def display_results(results):
    primt(f"\n\n    {Fore.BLUE}** sorted results[DR] are (raw first, then pretty):{str(results)}\n\n\n\n   {Fore.CYAN}** {len(results)} clean sorted results [DR]:")
    for result in results:
        primt(f"\n\t*         Filename: {result.get('filename'               , 'N/A')}")
        primt(  f"\t   Original_Artist: {result.get('original_artist'        , 'N/A')}")
        primt(  f"\t    Has Ands or &s: {result.get('artist_has_ands_or_amps', 'N/A')}")
        primt(  f"\t   Artist Before &: {result.get('artist_before_ampersand', 'N/A')}")
        primt(  f"\tOrignl ArtistTitle: {result.get('original_title'         , 'N/A')}")
        primt(  f"\tDicogs ArtistTitle: {result.get('artisttitle'            , 'N/A')}")
        primt(  f"\t     Parsed Artist: {result.get('parsed_artist'          , 'N/A')}")
        primt(  f"\t     Parsed  Title: {result.get('parsed_title'           , 'N/A')}")
        primt(  f"\t              Year: {result.get('year'                   , 'N/A')}")
        primt(  f"\t                id: {result.get('id'                     , 'N/A')}")
        primt(  f"\t     Title Befor /: {result.get('title_before_slash'     , 'N/A')}")
        primt(  f"\t     Title After /: {result.get('title_after_slash'      , 'N/A')}")
        #rimt(  f"\t         master_id: {result.get('master_id'              , 'N/A')}")                                                  #master_id not defined in this situation
        primt(  f"\t        is B-side?: {result.get('is_b_side'              , 'N/A')} (bef={result.get('score_slash_before','N/A')},aft={result.get('score_slash_after','N/A')})")
        primt(  f"\t        our scores: {result.get('score'                  , 'N/A')} " +
                f"(a={result.get('score_artist', 'N/A')}[og={result.get('score_artist_og','N/A')}/ba={result.get('score_artist_ba','N/A')}/" +
                f"and={result.get('score_artist_and','N/A')}/amp={result.get('score_artist_amp','N/A')}],t={result.get('score_title', 'N/A')}," +
                f"y={result.get('score_year', 'N/A')})")
        primt(  f"\t    2nd-pass score: {result.get('score_2'                , 'N/A')} ")



















def search_and_download_bside_images(results, filename, response):
    is_b_side    = results[0].get("is_b_side")
    resource_url = results[0].get("resource_url")

    if not is_b_side:    return None
    if not resource_url: return None

    primt(f"\n        {Fore.YELLOW}{Style.NORMAL}*[R1D] search_and_download_bside_images(results, filename={filename}, response){Fore.WHITE}")
    primt(  f"        *[R1D] calling fetch_release_data on resource URL of {resource_url}")
    response = fetch_release_data(resource_url)
    primt(f"        {Fore.CYAN}{Style.NORMAL}*[R1D] bside response is {str(response)}{Fore.WHITE}")
    release_data = response.json()

    if release_data is None: return None

    primt(f"\n{Fore.BLUE}{Style.BRIGHT}        * [BSRD]B-Side Release data:   {str(release_data)}")
    primt(  f"{Fore.CYAN}{Style.NORMAL}        * [BSRD]Len(release_data): {str(len(release_data))}\n")

    image_found = False
    image_number = 0

    release_data_images = release_data.get("images", [])
    primt(f"{Fore.WHITE}        * release_data_images = {str(release_data_images)}")
    for image in release_data_images:
        primt(f"{Fore.GREEN}        ...found image of type {image.get('type')} at URL={image.get('uri',None)}{Fore.WHITE}\n")
        if image.get("type") == "secondary":
            image_number += 1
            cover_image_url_b = image.get("uri",None)
            tmp_filename = filename
            tmp_filename = modify_filename_with_letter(filename, "B" + str(image_number))
            download_image(cover_image_url_b, tmp_filename)
            image_found = True
            ### we stopped doing this so that we could gather ALL the b-side potential images instead of just the first:
            #return cover_image_url_b

    if image_found: return cover_image_url_b            #this return value is really only checked to see if it's not None
    return None




def fetch_release_data(resource_url):
    global THROTTLE_API_CALLS_LEFT, API_CALLS_MADE
    while True:
        try:
            response = requests.get(resource_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            API_CALLS_MADE += 1
            throttle_api_request_rate_if_necessary(response)
            return response
        except requests.exceptions.HTTPError as exception:
            if response.status_code == 429:
                time.sleep(THROTTLE_TIME_AFTER_CENSURE)
            else:
                raise exception







#def get_cover_image_url(cover_image_url):
#    response = requests.get(cover_image_url, timeout=REQUEST_TIMEOUT)
#    primt(f"{Fore.WHITE}{Style.NORMAL}response is {str(response)}")
#    response.raise_for_status()
#    API_CALLS_MADE += 1
#    throttle_api_request_rate_if_necessary(response)
#    data = response.json()
#    if "cover_image" in data: return data["cover_image"]
#    return None
#this is no longer used anywhere!




def modify_filename_with_letter(filename, letter):
    base, extension = os.path.splitext(filename)
    #f letter == 'A' or letter[0] == 'B' :
    if letter == 'A' or letter[0] == 'B' or letter[0] == 'C':
        pattern = re.compile(r'[A-Z][0-9]*$', re.IGNORECASE)
        primt(f'        rem base for filename {filename} is {base}, extension is {extension}\n')       #2024/05
        base = pattern.sub('', base)  # Remove the existing suffix, if present
        primt(f'                                 rem is now {base}, extension is {extension}\n\n')     #2024/05
        #TODO: BUG: something is wrong here. "Cherries.jpg" becoming "CherrieB9.jpg instead of "CherriesB9.jpg". Will have to look into it.
    return f"{base}{letter}{extension}"



def download_image(url, input_filename):
    global DOWNLOADED_URLS, DOWNLOADED_FILENAMES, IMAGES_FOUND, DOWNLOAD_SCRIPT, API_CALLS_MADE

    # don't download the cover art if we've already downloaded it
    if url in DOWNLOADED_URLS: return input_filename

    # create the filename for the artwork to be downloaded to -- the same name as the song, but with the correct image extension
    file_extension  = os.path.splitext(url)[-1]
    output_filename = os.path.splitext(input_filename)[0] + file_extension

    # clean our filename of things like ".jpeg" and ".gif.gif" and ".png.png"
    output_filename = output_filename.replace(".jpeg",".jpg")                                                # stop that 'jpeg' nonsense
    pattern = re.compile(r'(\.(jpg|png|gif))(?=\.(jpg|png|gif))+', re.IGNORECASE)                            # pattern that matches to double extensions so we can fix .jpg.jpg type situations.
    cleaned_output_filename = pattern.sub('', output_filename)                                               # remove double extensions using the pattern match

    # don't download to the same filename twice
    #primt(f"DEBUG: output_filename = {output_filename}, cleaned_output_filename = {cleaned_output_filename}")
    #primt(f"DEBUG: cleaned_output_filename with A = {modify_filename_with_letter(cleaned_output_filename, 'A')}")
    #primt(f"DEBUG: DOWNLOADED_FILENAMES = {DOWNLOADED_FILENAMES}")
    if cleaned_output_filename in DOWNLOADED_FILENAMES:
        suffix = "B1"
        while modify_filename_with_letter(cleaned_output_filename, suffix) in DOWNLOADED_FILENAMES:
            #primt(f"DEBUG: cleaned_output_filename with suffix {suffix} = {modify_filename_with_letter(cleaned_output_filename, suffix)}")
            suffix_number = int(suffix[1:]) + 1
            suffix = f"B{suffix_number}"
        cleaned_output_filename = modify_filename_with_letter(cleaned_output_filename, suffix)
    #primt(f"DEBUG: output_filename = {output_filename}, cleaned_output_filename = {cleaned_output_filename}")
    #primt(f"DEBUG: cleaned_output_filename with A = {modify_filename_with_letter(cleaned_output_filename, 'A')}")

    # only actually download the file if we are configured to do so (and this is untested anyway!)
    if DOWNLOAD_INTERNALLY:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        API_CALLS_MADE += 1
        throttle_api_request_rate_if_necessary(response)
        with open(cleaned_output_filename, "wb") as file: file.write(response.content)

    # add the new cover art download to our download script
    with open(DOWNLOAD_SCRIPT, "a", encoding='utf-8') as file:
        # Discogs is strict about their "60 requests a minute" rule. In theory, we wait 1 second in between each download
        # But in practice, this doesn't quite cut it. Therefore we must bump it up to 1.5 - 2.0 seconds at a minimum.
        if OUR_SHELL == "TCC": file.write(f'if not exist "{cleaned_output_filename}" delay /m 1500\n')       # on my own computer I use TCC and want 1.5 second delays between downloads. Not 1. Not 2. Sleep seems to only accept integers, but TCC has an internal delay command that accepts milliseconds, to give me what I want
        else:                  file.write(f'if not exist "{cleaned_output_filename}" sleep 2\n')             # but for other people, they'll just have to suffer with 2.0 second pauses instead of 1.5 second pauses 🤣

        # track what we're downloading
        IMAGES_FOUND += 1
        DOWNLOADED_FILENAMES.add(cleaned_output_filename)
        DOWNLOADED_URLS     .add(url)

        # add the download to our download script
        file.write(f'if not exist "{cleaned_output_filename}" wget -O "{cleaned_output_filename}" "{url}"\n')

    return cleaned_output_filename












def clean_up_zero_byte_downloads():                                                                                                 #clean up zero-byte downloads, which is something wget can create, especially if request throttling is not enabled
    #There is some attempt to make this output a script that works under bash/unix/WSL, CMD.exe, and TCC.EXE, but I personally use TCC.EXE so it's mostly untested
    global DOWNLOAD_SCRIPT
    with open(DOWNLOAD_SCRIPT, "a", encoding='utf-8') as file:
        file.write('\n\n:Do_It_Twice\n')
        file.write('if "%DONE_ONCE%" ne "1" (set DONE_ONCE=1 %+ goto :Retry_Point)\n')
        file.write('\n\n:CleanUp\n')
        file.write('\n:CleanUp_Zero_Byte_Images_Execute\n')
        if IS_WINDOWS and OUR_SHELL.lower() != "bash":
            file.write('set FMASK_IMAGE=*.jpg;*.jpeg;*.gif;*.png;*.bmp;*.webp;*.ico;*.tif;*.tiff;*.pcx;*.art;*.dcm;*.jfif;*.jpg_large;*.png_large\n')
            if OUR_SHELL == "TCC": file.write('call delete-zero-byte-files %FMASK_IMAGE%\n\n')                                      #i have my own script for this purpose so i call that one too just to be double-thorough, however that script needs to be passed a list of extensions or it ends up deleting other 0-byte files that are unrelated to this task
            if OUR_SHELL == "TCC": file.write('for  %A in  (%FMASK_IMAGE%)  do ( if %@FILESIZE["%A"] == 0 (*del /p   "%A") )\n\n')
            else:                  file.write('for %%A in ("%FMASK_IMAGE%") do (if %%~zA            equ 0 ( del /p "%%~A") )\n\n')  #untested
        else:
            file.write('export FMASK_IMAGE="*.jpg;*.jpeg;*.gif;*.png;*.bmp;*.webp;*.ico;*.tif;*.tiff;*.pcx;*.art;*.dcm;*.jfif;*.jpg_large;*.png_large"\n')
            file.write('find . -name "$FMASK_IMAGE" -size 0 -delete\n\n')                                                           #untested
        file.write('%COLOR_SUCCESS%')
        file.write('\n\necho **** Time to manually review the images, deleting the incorrect ones, and cropping those that need cropping.....and then run CoverEmbedder.py! ****')










def final_report(start_time):
    global API_CALLS_MADE, API_CALLS_SAVED_BY_CACHING, IMAGES_FOUND, RESULTS_FOUND, THROTTLE_API_CALLS_LEFT, CACHE_HITS
    end_time = time.monotonic()
    elapsed_seconds = end_time - start_time
    elapsed_minutes = elapsed_seconds / 60
    if elapsed_minutes == 0:
        images_located_per_minute = IMAGES_FOUND
    else:
        images_located_per_minute = IMAGES_FOUND / elapsed_minutes
    primt(f"{Fore.GREEN}{Style.BRIGHT}\n\n\n\n\n********** ALL DONE! **********{Style.NORMAL}")
    primt(f"\n{IMAGES_FOUND} artworks located in {int(elapsed_seconds)} seconds ({elapsed_minutes:.2f} minutes) at a rate of {images_located_per_minute:.2f} per minute\n")
    primt(f"{API_CALLS_MADE} API calls made, finding {RESULTS_FOUND} results.\n")
    if (API_CALLS_MADE+API_CALLS_SAVED_BY_CACHING) != 0:
        primt(f"{API_CALLS_SAVED_BY_CACHING} API calls were saved via {CACHE_HITS} cache hits ({round((API_CALLS_SAVED_BY_CACHING/(API_CALLS_MADE+API_CALLS_SAVED_BY_CACHING))*100)}% savings).")
    primt(f"{Fore.BLUE}{THROTTLE_API_CALLS_LEFT} API calls were remaining at the moment of the very last request.")
    primt(f"\n{Style.BRIGHT}{Fore.RED}——————————————————————> Time to run get-art.bat !!!!!!!!!!!!!!!!!!!!!!!!!!!!")







def main():
    start_time = get_platform_info()                    # setup computer, start timer
    delete_files_from_prevous_run()                     # setup logfile, roll previously-generated logfiles & scripts
    initialize_download_script()                        # setup output script which will download cover art
    process_all_music_files()                           # research every music file, locate cover art, add to download script
    clean_up_zero_byte_downloads()                      # close output script, clean up failed 0-byte downloads
    final_report(start_time)                            # report stats, artwork downloaded, cache hits, time elapsed, etc





if __name__ == "__main__":
    main()

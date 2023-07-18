# classics_cover_downloader

classics_cover_downloader is a thorough cover art downloader for music, optimized for early 1900s vinyl singles with "A" and "B" sides.





It's specifically made for songs in the "artist - title (year).mp3" filename format.

It should work in other situations too, just not as well.

It uses the Discogs API and Discogs.com exclusively.  





## What makes it different from any other?

1. **Its thoroughness** with matching and downloading. This is made for a THOROUGH person.

2. **Its early-1900s vinyl-single specificity.** 
   This was specifically written for early 1900s vinyl record releases with A and B sides and has a lot of logic related to detecting whether the song in queston is an A or B side of the vinyl. Thus, it will sometimes download multiple images to get the back image of the record, in the event that a song is a B-side. Due to release structures implementation minutiae with Discogs.com, B-sides songs may end up causing the download of several images. The strategy is to get a few wrong images in order to ensure we get the right image. You, the user, willl have to delete any wrong images. This is about saving search time, and it's much faster to delete the wrong images than it is to search for the correct ones. But it's not possible, programatically, to always get the correct one for B-sides. The intersection of "vinyl logic" and "Discogs API logic" is a special hellscape.



## What situation is this for?

It is written for the "music situation" of having a folder of a lot of different songs by different artists, such as:
  Lee Morse - Dallas Blues (1925).mp3
  Fletcher Henderson & His Orch - I'll Take Her Back If She Wants To Come Back (1925).mp3
  Henry Burr - You Forgot To Remember (1925).mp3
  Paul Whiteman & His Orch - Charleston (1925).mp3

The assumption is the filename format is:  {artist} - {title} ({year})

It is still designed to work if year is missing, and can still work in other situations too. Try it and see what happens. Can't hurt.




## How to use?

- Install the appropriate packages:  ```pip install -r requirements.txt```

- Get a DISCOGS API token from https://www.discogs.com/settings/developers

- set environment variable ```DISCOGS_TOKEN={your Discogs API token}```

- A ```workflow.bat``` is included, which guides us through the steps of searching, downloading, and embedding the proper cover artwork. The steps are:

    1. Run ```cover_downloader.py``` (generates download script, and huge log file)

    2. Run the generated get-art.bat file. It will download all the artwork. Enjoy!

    3. Manually review downloaded art and delete the inappropriate ones, crop any that are badly cropped, and make any other subjective edits.
       Many different artworks will be downloaded, specifically if song is detected as a B-side or if multiple releases have a tied score for our fuzzy match algorithm
    
    4. Optionally run wedding_party.py to separate the successes from the failures. Handy if you want to retry the failures again. Discogs API isn't always consistent and somtimes a retry gives more results.
    
    5. Run CoverEmbedder.py to embed our final set of JPGs into our MP3/FLACs







## What is this thoroughness in search you speak of? What other unnoticed features are there?


* Caching of redundant API calls along with statkeeping so we know how much we saved.
Basically, multiple songs by the same artist translate to an increased successful caching frequency.
* Transforms "Orch" to "Orchestra" and "Qt" to "Quartet" prior to searching
* ignores "(v1)" version notations in filenames
* ignores bracketed and braced text in filenames
* The script outputted to download the art is actually outputted in PowerShell, unix shell, or TCC shell, based on autodetect. (But was only tested under TCC.)
* All output goes to screen and logfile separately, with screen colored via ANSI codes, which are stripped prior to going to logfile
* The Discogs API is NOT straightforward!
	* Only 100 results per request, so pagination is used
	* Only 60 requests per minutes, so headers are examined to monitor remaining requests allowed, with lots of throttling pauses
	* Thousands of calls can be made for a large folder, so caching is employed. It hits about 5-10% of the time depending on your input data.
	* Discog searches are wonky and only the most exact matches find what we want. We were getting a mere 5% success rate without fuzzy matching.
	* So fuzzy matching is used on a basket of amalgamated search results
	* We research our music approximately 10 ways:
		# Research 1:  Search by artist                                         (sometimes has thousands of results)
		# Research 2:  Search by artist and title                               (sometimes has        no    results)
		# Research 3:  Search by title  and year                                (sometimes has    dozens of results)
		# Research 4:  Search by title                                          (sometimes has  hundreds of results, mabye thousands)
		# Research 5:  Optional Search by artist truncated after "&" and year   (sometimes has thousands of results)
		# Research 6:  Optional Search by artist with "'s" changed to "& His"   (finds results where none would be found otherwise, often    )
		# Research 7:  Optional Search by artist with "'s" changed to "& Her"   (finds results where none would be found otherwise, sometimes)
		# Research 8:  Optional Search by artist with "'s" changed to "& Their" (finds results where none would be found otherwise, seldom   )
		# Research 9+: Additional queries generated at runtime to change any "&" to " and ", as well as vice versa
	* ...And gather all the results from all of these and use fuzzy logic to look for the right release via a mathematically weighted scoring algorithm
	* ...Research #5 is particularly interesting in that it checks on the artist name before the first ampersand
	     This is because composers exist in the filename next to artists in a lot of downloads of these old releases, and muddy the search results.
	     i.e. "Fletcher Henderson & Gershwin" often is a filename convention for Artist="Fletcher Henderson", Composer="Gershwin",
		   so we search for "Fletcher Henderson" without the "& Gershwin" after it








## Testing/Bugs

Really only thoroughly tested under the TakeCommand command-line, but that probably shouldn't matter.



## Contributing: Modification

Feel free to make your own version with neato changes, if you are so inspired.


## License

[The Unlicense](https://choosealicense.com/licenses/unlicense/)






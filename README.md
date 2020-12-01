# convert.py

Conversion tool for PerlPress static website generator to Nikola static
website generator.

##Introduction

This tool supports the conversion of website articles from PerlPress to
Nikola for my personal website http://www.jan-grosser.de.

The website articles from PerlPress are stored in a SQlite database. With the
conversion tool, selected articles can be extracted to input files for Nikola.
The format of the Nikola input files are selected to be HTML, because also in
the database the articles are stored in HTML. The articles to be converted are
referenced by the unique article ID of PerlPress. These IDs are provided via
the command line

The tool can also be provided with a source directory, containing auxilliary
files for the articles like images or download files. The conversion tool scans
the articles for those files, copies the files to a specific output folder and
adapt the links/references in the outputted articles as needed for Nikola.

##Command

    ./convert.py [-s src-dir] [-o out-dir] database-file art-id-0 \
        [art-id-1 art-id-2 ...]

    -s src-dir      Source directory holding "auxilliary" files (images,
                    download files, ...) for the articles
                    Default is ./source
    -o out-dir      Output directory for articles files and aux files. If not
                    present, it will created with following sub diretories:
                        ./output/posts
                        ./output/images
    database-file   SQLite database file.
                    See: https://github.com/rzbrk/jan-grosser.de/blob/master/db/jan-grosser.sqlite
    art-id-*        Article IDs from those articles to be converted, separated
                    by spaces. If this IDs are stored in a text file (e.g.
                    art_ids.txt), they can be provided to the conversion tool
                    via command line by $(cat art_ids.txt).

##Examples

    ./convert.py -s ./source -o ./output jan-grosser.sqlite 1 2 3 4
    ./convert.py -s ./source -o ./output jan-grosser.sqlite $(cat art_ids.txt)

##Dependencies

The following dependencies apply:
* Python 3
* argparse
* os
* shutil
* sys
* sqlite3
* re
* bs4


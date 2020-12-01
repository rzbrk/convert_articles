#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
import sqlite3
import re
#import textwrap
from bs4 import BeautifulSoup

# Main routine
def main(args):
    # Open database file
    dbc = open_db(args.dbfile)

    # Ensure, source directory exists
    args.srcdir = source_dir(args.srcdir)

    # Ensure, output directory exists
    args.outdir = output_dir(args.outdir)

    # Loop over all article ids given in the arguments
    for id in args.artids:
        print("Processing ID", id, ". . .")

        # Retrieve article data from database
        art_data = get_art_data(dbc, id)

        # Print some information
        if art_data['status'] != "non-existing":
            print("  Title:", art_data['title'])
            print("  Categories:", art_data['category'])
            print("  Tags:", art_data['tag'])
            print("  Length:", len(art_data['text']), "characters")

            # Search and replace youtube shortcodes
            art_data['text'] = youtube(art_data['text'])

            # Insert css in <div class="terminal">
            art_data['text'] = div_terminal(art_data['text'])

            # Insert css in <div class="code">
            art_data['text'] = div_code(art_data['text'])

            # Search for internal article links
            art_data['text'] = int_links(dbc, art_data['text'])

            # Search for img shortcodes
            art_data['text'] = img(art_data['text'], args.srcdir, args.outdir)

            # Create output file for article
            write_article(art_data, args.outdir)

            print("\n")
        else:
            print("  Article not found\n")

###############################################################################

#------------------------------------------------------------------------------
def source_dir(srcdir):
    # Ensure, srcdir ends with character "/"
    if not re.match(".*\/$", srcdir):
        srcdir = srcdir + "/"

    if (not os.path.isdir(srcdir)) or (not os.path.exists(srcdir)):
        print("ERROR: Source directory doesn't exist. Quitting!")
        sys.exit()

    return srcdir

#------------------------------------------------------------------------------
# Check if output directory exists. If not, create it
def output_dir(outdir):
    # Ensure, outdir ends with character "/"
    if not re.match(".*\/$", outdir):
        outdir = outdir + "/"

    if (not os.path.isdir(outdir)) or (not os.path.exists(outdir)):
        os.mkdir(outdir)

    # The output diretory shall contain the following subfolders
    if (not os.path.isdir(outdir + "images/")) or (not os.path.exists(outdir + "images/")):
        os.mkdir(outdir + "images/")
    if (not os.path.isdir(outdir + "posts/")) or (not os.path.exists(outdir + "posts/")):
        os.mkdir(outdir + "posts/")

    return outdir

#------------------------------------------------------------------------------
# Check if database file exists. If yes, open database and return
# database cursor
def open_db(dbfile):
    if not os.path.isfile(dbfile):
        print("Error: database file doesn't exist. Quitting!")
        sys.exit()
    db = sqlite3.connect(dbfile)
    dbc = db.cursor()
    return dbc

#------------------------------------------------------------------------------
# Retrieving article data from database
def get_art_data(dbc, art_id):
    # Initialize dictionary for article data
    art_data = {
            'art_id': art_id,
            'slug': "",
            'title': "",
            'created': "",
            'text': "",
            'status': "non-existing",
            'category': [],
            'tag': [],
            }

    # Count all atricles with matching article id. Because the article id is
    # unique, the return value is either 1 if the article exists or 0 if
    # there is no article in the database with matching article id
    n = dbc.execute("select count(*) from articles where art_id=?",
        (art_id,)).fetchone()[0]

    # Only proceed if n == 1
    if n == 1:
        # Basic article data from table articles
        retval = dbc.execute("select filename, title, created, intr_text, full_text, status from articles where art_id=?", (art_id,)).fetchone()
        art_data['slug'] = retval[0].replace(".html", "")
        art_data['title'] = retval[1]
        art_data['created'] = retval[2]
        intr_text = retval[3]
        full_text = retval[4]
        art_data['status'] = retval[5]

        # Concatenate intr_text and full_text if full_text is not empty
        if len(full_text) > 0:
            art_data['text'] = intr_text + "\n\n <!-- TEASER_END -->\n\n" + full_text + "\n"
        else:
            art_data['text'] = intr_text + "\n"

        # Extract categories and tags the article is linked to
        cats = dbc.execute("select alias from categories inner join art_cat on categories.cat_id=art_cat.cat_id where art_cat.art_id=?", (art_id,)).fetchall()
        for c in cats:
            art_data['category'].append(c[0])
        tags = dbc.execute("select alias from tags inner join art_tag on tags.tag_id=art_tag.tag_id where art_tag.art_id=?", (art_id,)).fetchall()
        for t in tags:
            art_data['tag'].append(t[0])

    return art_data

#------------------------------------------------------------------------------
# Write article to file in output directory
def write_article(art_data, outdir):
    filename = outdir + "posts/" + art_data['slug'] + ".html"
    print("  Write to file:", filename)
    fh = open(filename, 'w')

    fh.write("<!--\n")
    fh.write(".. title: " + art_data['title'] + "\n")
    fh.write(".. slug: " + art_data['slug'] + "\n")
    fh.write(".. date: " + art_data['created'] + "\n")
    fh.write(".. tags: " + ', '.join(art_data['tag']) + "\n")
    fh.write(".. category: " + art_data['category'][0] + "\n")
    fh.write(".. link: " + "\n")
    fh.write(".. description: " + "\n")
    fh.write(".. type: text" + "\n")
    fh.write("-->\n\n")

    # No line wrapping, because is can "destroy" hyperlinks
    #for line in (textwrap.wrap(art_data['text'], width = 80)):
    #    fh.write(line + "\n")

    soup = BeautifulSoup(art_data['text'], "html.parser")
    fh.write(soup.prettify())
    fh.write("\n\n")
    fh.close

#------------------------------------------------------------------------------
# Replace youtube shortlink
def youtube(text):
    print("  Searching for YouTube short codes . . .")
    # Format of youtube short link is:
    # {youtube}A1bCd_ef-G4{/youtube}
    # It should be replaced with the following html code:
    # <div id="video">
    #   <iframe width="560" height="315"
    #     src="http://www.youtube.com/embed/_8EybE2ejEQ"
    #     frameborder="0" allowfullscreen>
    #   </iframe>
    # </div>

    # Regular expression for youtube shortlink
    regexp = "\{youtube\}[a-zA-Z0-9_-]*\{\/youtube\}"

    # html code for replacement
    html_before = "<div class=\"video\"><iframe width=\"560\" height=\"315\" src=\"https://www.youtube.com/embed/"
    html_after = "\" frameborder=\"0\" allowfullscreen></iframe></div>"

    # Apply regexp search on article text and loop over all instances
    # found
    youtubes = re.finditer(regexp, text)
    for y in youtubes:
        print("    ", y.group())
        # Extract video id
        video_id = re.sub("\{[\/]*youtube\}", "", y.group())

        # Perform replacement
        text = re.sub(y.group(), html_before + video_id + html_after, text)

    return text

#------------------------------------------------------------------------------
# Insert css code for <div class="terminal"> ... </div>
def div_terminal(text):
    print("  Searching for occurences of <div class=\"terminal\"> . . .")

    # Regular expression
    regexp = "\<div\s+class\s*=\s*\"terminal\"\s*\>"

    # css code to be inserted
    div_with_css = "<div class=\"terminal\" style=\"font-family: mono,monospace; background-color: black; border: 3px solid green; border-radius: 10px; color: green; margin-top: 10px; margin-left: 50px; margin-right: 50px; padding-top: 10px; padding-bottom: 10px; padding-left: 20px; padding-right: 20px\">"

    # Apply regexp search on article text and loop over all instances
    # found
    divs = re.finditer(regexp, text)
    for d in divs:
        print("    <div class=\"terminal\"> found . . .")

        # Perform replacement
        text = re.sub(d.group(), div_with_css, text)

    return text

#------------------------------------------------------------------------------
# Insert css code for <div class="code"> ... </div>
def div_code(text):
    print("  Searching for occurences of <div class=\"code\"> . . .")

    # Regular expression
    regexp = "\<div\s+class\s*=\s*\"code\"\s*\>"

    # css code to be inserted
    div_with_css = "<div class=\"terminal\" style=\"font-family: mono,monospace; background-color: white; border: 3px solid orange; color: black; margin-top: 10px; margin-left: 50px; margin-right: 50px; padding-top: 10px; padding-bottom: 10px; padding-left: 20px; padding-right: 20px\">"

    # Apply regexp search on article text and loop over all instances
    # found
    divs = re.finditer(regexp, text)
    for d in divs:
        print("    <div class=\"code\"> found . . .")

        # Perform replacement
        text = re.sub(d.group(), div_with_css, text)

    return text

#------------------------------------------------------------------------------
# Reformat internal article links
def int_links(dbc, text):
    print("  Searching for internal article links . . .")
    # Format of internal article links is:
    # {article id="123"}link text{/article}
    # It should be replaced by Nikola's "magic links":
    # <a href="link://slug/slug_of_article_with_id_123

    # Regular expression
    regexp = "\{article\s+id=\"([0-9]+)\"\}(.*)\{\/article\}"

    # Apply regexp search on article text and loop over all instances
    # found
    links = re.finditer(regexp, text)
    for l in links:
        # Reapply regexp to matched pattern to retrieve article id and link
        # text
        link_props = re.match(regexp, l.group())
        art_id = link_props.groups()[0]
        link_text = link_props.groups()[1]

        print("    Found link to article", art_id)

        # Now, that we know the article id we can ask the database for the
        # article infomation, especially the slug to build the magic link.
        art_data = get_art_data(dbc, art_id)

        # Theoretically, the article can be non-existing in the database. In
        # this case art_data['status'] is "non-existing". If the article is
        # existing, it is "published". If the article does not exist, create
        # an empty link.
        if art_data['status'] != "published":
            new_link = "<a href=\"#\">" + link_text + "</a>"
        else:
            new_link = "<a href=\"link://slug/" + art_data['slug'] + "\">" + link_text + "</a>"

        # Now, replace the link shortcode with new_link:
        text = re.sub(l.group(), new_link, text)

    return text

#------------------------------------------------------------------------------
# Replace {img} ... {/img} shortcode
def img(text, srcdir, outdir):
    print("  Searching for image shortcodes . . .")
    # Format of the shortlink is:
    # {img}filename.jpg{/img}
    # This is replaced by an actual working link. In addition, the image file
    # is picked from the source directory and copied to the output diretory.

    regexp = "\{img}(.*)\{\/img\}"

    imgs = re.finditer(regexp, text)
    for i in imgs:
        img_file = re.sub("\{[\/]*img\}", "", i.group())

        # Now search for the image file in the source diretory. If present,
        # copy this file to the output directory, subdiretory "images/". If
        # not present, leave link as is (dead link) and output warning
        # message.
        if os.path.exists(srcdir + img_file):
            print("    Found", img_file)
            shutil.copyfile(srcdir + img_file, outdir + "images/" + img_file)
            new_img_link = "/images/" + img_file

            # Perform replacement in article text
            text = re.sub(i.group(), new_img_link, text)
        else:
            print("    WARNING:", img_file, "not found!")

    return text

###############################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dbfile", help="SQLite database file")
    parser.add_argument("artids", type=int, nargs="+", help="Article IDs")
    parser.add_argument("-s", "--source", action="store",
            default="./source", dest="srcdir")
    parser.add_argument("-o", "--output", action="store",
            default="./output", dest="outdir")
    args = parser.parse_args()
    main(args)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2011-2016 WikiTeam developers
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Documentation for users: https://github.com/WikiTeam/wikiteam/wiki
# Documentation for developers: http://wikiteam.readthedocs.com

import argparse
import datetime
import http.cookiejar as cookielib
import json
import os
import pickle as cPickle
import random
import re
import sys
import time
import urllib

__version__ = "0.3.1"

"""
Stuff to check if works properly or re-add if needed:
* fixBOM
* sessions
"""

def avoidWikimediaProjects(config={}):
    """ Skip Wikimedia projects and redirect to the dumps website """

    # notice about wikipedia dumps
    if re.findall(r'(?i)(wikipedia|wikisource|wiktionary|wikibooks|wikiversity|wikimedia|wikispecies|wikiquote|wikinews|wikidata|wikivoyage)\.org', config['wiki']):
        sys.stderr.write('PLEASE, DO NOT USE THIS SCRIPT TO DOWNLOAD WIKIMEDIA PROJECTS!\n')
        sys.stderr.write('Download Wikimedia dumps from https://dumps.wikimedia.org\n')
        """if not other['force']:
            sys.stderr.write('Thanks!')
            sys.exit()"""

def bye():
    """ Print closing message """
    
    message = """
---> Congratulations! Your dump is complete <---
If you found any bug, report a new issue here: https://github.com/WikiTeam/wikiteam/issues
If this is a public wiki, please consider publishing this dump. Do it yourself as explained in https://github.com/WikiTeam/wikiteam/wiki/Tutorial#Publishing_the_dump or contact us at https://github.com/WikiTeam/wikiteam
Good luck! Bye!"""
    sys.stderr.write(message)

def createNewDump(config={}):
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        mediawiki.mwCreateNewDump(config=config)
    elif config['wikiengine'] == 'wikispaces':
        import wikispaces
        wikispaces.wsCreateNewDump(config=config)
    else:
        sys.stderr.write("Wikiengine %s not supported. Exiting.\n" % (config['wikiengine']))

def createDumpPath(config={}):
    # creating path or resuming if desired
    c = 2
    # to avoid concat blabla-2, blabla-2-3, and so on...
    originalpath = config['path']
    # do not enter if resume is requested from begining
    while not config['other']['resume'] and os.path.isdir(config['path']):
        sys.stderr.write('\nWarning!: "%s" path exists\n' % (config['path']))
        reply = ''
        while reply.lower() not in ['yes', 'y', 'no', 'n']:
            reply = input(
                'There is a dump in "%s", probably incomplete.\nIf you choose resume, to avoid conflicts, the parameters you have chosen in the current session will be ignored\nand the parameters available in "%s/%s" will be loaded.\nDo you want to resume ([yes, y], [no, n])? ' %
                (config['path'],
                 config['path'],
                    config['other']['configfilename']))
        if reply.lower() in ['yes', 'y']:
            if not os.path.isfile('%s/%s' % (config['path'], config['other']['configfilename'])):
                sys.stderr.write('No config file found. I can\'t resume. Aborting.\n')
                sys.exit()
            sys.stderr.write('You have selected: YES\n')
            config['other']['resume'] = True
            break
        elif reply.lower() in ['no', 'n']:
            sys.stderr.write('You have selected: NO\n')
            config['other']['resume'] = False
        config['path'] = '%s-%d' % (originalpath, c)
        sys.stderr.write('Trying to use path "%s"...\n' % (config['path']))
        c += 1
    return config

def delay(config={}):
    """ Add a delay if configured for that """
    if config['delay'] > 0:
        sys.stderr.write('Sleeping... %d seconds...\n' % (config['delay']))
        time.sleep(config['delay'])

def domain2prefix(config={}):
    """ Convert domain name to a valid prefix filename. """

    domain = ''
    if config['wiki']:
        domain = config['wiki']
    domain = domain.lower()
    domain = re.sub(r'(https?://|www\.|/index\.php|/api\.php)', '', domain)
    domain = re.sub(r'/', '_', domain)
    domain = re.sub(r'\.', '', domain)
    domain = re.sub(r'[^A-Za-z0-9]', '_', domain)
    domain = domain.strip('_')
    return domain

def getAPI(config={}):
    """ Returns API for a wiki, if available """
    
    api = ''
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        api = mediawiki.mwGetAPI(config=config)
    
    return api

def getImageNames(config={}):
    """ Returns list of image names for this wiki """
    
    imagenames = []
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        imagenames = mediawiki.mwGetImageNames(config=config)
    
    return imagenames

def getIndex(config={}):
    """ Returns Index.php for a wiki, if available """
    
    index = ''
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        index = mediawiki.mwGetIndex(config=config)
    
    return index

def getJSON(request):
    """Strip Unicode BOM"""
    """if request.text.startswith(u'\ufeff'):
        request.encoding = 'utf-8-sig'
    return request.json()"""
    return json.loads(request)

def getNamespaces(config={}):
    """ Returns list of namespaces for this wiki """
    
    namespaces = []
    namespacenames = []
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        namespaces, namespacenames = mediawiki.mwGetNamespaces(config=config)
    
    return namespacenames

def getPageTitles(config={}):
    """ Returns page titles for this wiki """
    
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        for pagetitle in mediawiki.mwGetPageTitles(config=config):
            yield pagetitle

def getParameters(params=[]):
    """ Import parameters into variable """
    
    if not params:
        params = sys.argv
    
    config = {}
    parser = argparse.ArgumentParser(description='Tools for downloading and preserving wikis.')

    # General params
    parser.add_argument(
        '-v', '--version', action='version', version=getVersion())
    parser.add_argument(
        '--cookies', metavar="cookies.txt", help="Path to a cookies.txt file.")
    parser.add_argument(
        '--delay',
        metavar=5,
        default=0,
        type=float,
        help="Adds a delay (in seconds).")
    parser.add_argument(
        '--retries',
        metavar=5,
        default=5,
        help="Maximum number of retries.")
    parser.add_argument('--path', help='Path to store wiki dump at.')
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resumes previous incomplete dump (requires --path).')
    parser.add_argument('--force', action='store_true', help='')
    parser.add_argument(
        '--user', help='Username if authentication is required.')
    parser.add_argument(
        '--pass',
        dest='password',
        help='Password if authentication is required.')

    # URL params
    # This script should work with any general URL, finding out
    # API, index.php or whatever by itself when necessary
    groupWiki = parser.add_argument_group()
    groupWiki.add_argument(
        'wiki',
        default='',
        nargs='?',
        help="URL to wiki (e.g. http://wiki.domain.org).")
    # URL params for MediaWiki
    groupWiki.add_argument(
        '--mwapi',
        help="URL to MediaWiki API (e.g. http://wiki.domain.org/w/api.php).")
    groupWiki.add_argument(
        '--mwindex',
        help="URL to MediaWiki index.php (e.g. http://wiki.domain.org/w/index.php).")

    # Download params
    groupDownload = parser.add_argument_group(
        'Data to download',
        'What info download from the wiki')
    groupDownload.add_argument(
        '--pages',
        action='store_true',
        help="Generates a dump of pages (--pages --curonly for current revisions only).")
    groupDownload.add_argument('--curonly', action='store_true',
                               help='Store only the current version of pages.')
    groupDownload.add_argument(
        '--images', action='store_true', help="Generates an image dump.")
    groupDownload.add_argument(
        '--namespaces',
        metavar="1,2,3",
        help='Comma-separated value of namespaces to include (all by default).')
    groupDownload.add_argument(
        '--exnamespaces',
        metavar="1,2,3",
        help='Comma-separated value of namespaces to exclude.')

    # Meta info params
    groupMeta = parser.add_argument_group(
        'Meta info',
        'What meta info to retrieve from the wiki')
    groupMeta.add_argument(
        '--get-api',
        action='store_true',
        help="Returns wiki API when available.")
    groupMeta.add_argument(
        '--get-index',
        action='store_true',
        help="Returns wiki Index.php when available.")
    groupMeta.add_argument(
        '--get-page-titles',
        action='store_true',
        help="Returns wiki page titles.")
    groupMeta.add_argument(
        '--get-image-names',
        action='store_true',
        help="Returns wiki image names.")
    groupMeta.add_argument(
        '--get-namespaces',
        action='store_true',
        help="Returns wiki namespaces.")
    groupMeta.add_argument(
        '--get-wiki-engine',
        action='store_true',
        help="Returns wiki engine.")

    args = parser.parse_args()
    #sys.stderr.write(args)
    
    # Not wiki? Exit
    if not args.wiki:
        sys.stderr.write('ERROR: Provide a URL to a wiki\n')
        parser.print_help()
        sys.exit(1)
    
    # Don't mix download params and meta info params
    if (args.pages or args.images) and \
       (args.get_api or args.get_index or args.get_page_titles or args.get_image_names or args.get_namespaces or args.get_wiki_engine):
        sys.stderr.write('ERROR: Don\'t mix download params and meta info params\n')
        parser.print_help()
        sys.exit(1)

    # No download params and no meta info params? Exit
    if (not args.pages and not args.images) and \
       (not args.get_api and not args.get_index and not args.get_page_titles and not args.get_image_names and not args.get_namespaces and not args.get_wiki_engine):
        sys.stderr.write('ERROR: Use at least one download param or meta info param\n')
        parser.print_help()
        sys.exit(1)

    # Load cookies
    cj = cookielib.MozillaCookieJar()
    if args.cookies:
        cj.load(args.cookies)
        sys.stderr.write('Using cookies from %s\n' % args.cookies)

    # check user and pass (one requires both)
    if (args.user and not args.password) or (args.password and not args.user):
        sys.stderr.write('ERROR: Both --user and --pass are required for authentication.\n')
        parser.print_help()
        sys.exit(1)
    
    session = None
    if args.user and args.password:
        import requests
        session = requests.Session()
        session.cookies = cj
        session.headers.update({'User-Agent': getUserAgent()})
        session.auth = (args.user, args.password)
        #session.mount(args.mw_api.split('/api.php')[0], HTTPAdapter(max_retries=max_ret)) Mediawiki-centric, be careful

    # check URLs
    for url in [args.mwapi, args.mwindex, args.wiki]:
        if url and (not url.startswith('http://') and not url.startswith('https://')):
            sys.stderr.write(url)
            sys.stderr.write('ERROR: URLs must start with http:// or https://\n')
            parser.print_help()
            sys.exit(1)
    
    # Meta info params
    metainfo = '' # only one allowed, so we don't mix output
    if args.get_api:
        metainfo = 'get_api'
    elif args.get_index:
        metainfo = 'get_index'
    elif args.get_page_titles:
        metainfo = 'get_page_titles'
    elif args.get_image_names:
        metainfo = 'get_image_names'
    elif args.get_namespaces:
        metainfo = 'get_namespaces'
    elif args.get_wiki_engine:
        metainfo = 'get_wiki_engine'

    namespaces = ['all']
    exnamespaces = []
    # Process namespace inclusions
    if args.namespaces:
        # fix, why - ?  and... --namespaces= all with a space works?
        if re.search(
                r'[^\d, \-]',
                args.namespaces) and args.namespaces.lower() != 'all':
            sys.stderr.write("Invalid namespace values.\nValid format is integer(s) separated by commas\n")
            sys.exit()
        else:
            ns = re.sub(' ', '', args.namespaces)
            if ns.lower() == 'all':
                namespaces = ['all']
            else:
                namespaces = [int(i) for i in ns.split(',')]

    # Process namespace exclusions
    if args.exnamespaces:
        if re.search(r'[^\d, \-]', args.exnamespaces):
            sys.stderr.write("Invalid namespace values.\nValid format is integer(s) separated by commas\n")
            sys.exit(1)
        else:
            ns = re.sub(' ', '', args.exnamespaces)
            if ns.lower() == 'all':
                sys.stderr.write('You cannot exclude all namespaces.\n')
                sys.exit(1)
            else:
                exnamespaces = [int(i) for i in ns.split(',')]

    # --curonly requires --xml
    if args.curonly and not args.pages:
        sys.stderr.write("--curonly requires --pages\n")
        parser.print_help()
        sys.exit(1)
    
    config = {
        'cookies': args.cookies or '', 
        'curonly': args.curonly, 
        'date': datetime.datetime.now().strftime('%Y%m%d'), 
        'delay': args.delay, 
        'exnamespaces': exnamespaces, 
        'images': args.images, 
        'logs': False, 
        'metainfo': metainfo, 
        'namespaces': namespaces, 
        'pages': args.pages, 
        'path': args.path and os.path.normpath(args.path) or '', 
        'retries': int(args.retries), 
        'wiki': args.wiki, 
        'wikicanonical': '', 
        'wikiengine': getWikiEngine(args.wiki), 
        'other': {
            'configfilename': 'config.txt', 
            'filenamelimit': 100,  # do not change
            'force': args.force, 
            'resume': args.resume, 
            'session': session, 
        }
    }
    
    # Get ready special variables (API for MediWiki, etc)
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        config['mwexport'] = 'Special:Export'
        if not args.mwapi:
            config['mwapi'] = mediawiki.mwGetAPI(config=config)
            if not config['mwapi']:
                sys.stderr.write('ERROR: Provide a URL to API\n')
                sys.exit(1)
            else:
                data={
                    'action': 'query',
                    'meta': 'siteinfo',
                    'siprop': 'namespaces',
                    'format': 'json'}
                r = getURL(config['mwapi'], data=data)
                config['mwexport'] = getJSON(r)['query']['namespaces']['-1']['*'] \
                    + ':Export'
        if not args.mwindex:
            config['mwindex'] = mediawiki.mwGetIndex(config=config)
            if not config['mwindex']:
                sys.stderr.write('ERROR: Provide a URL to Index.php\n')
                sys.exit(1)
    elif wikiengine == 'wikispaces':
        import wikispaces
        # use wikicanonical for base url for Wikispaces?
    
    # calculating path, if not defined by user with --path=
    if not config['path']:
        config['path'] = './%s-%s-wikidump' % (domain2prefix(config=config), config['date'])

    return config

def getURL(url='', data=None):
    # fix quizas pasandole el config pueda saber si esta definido el campo session y usarlo si interesa con un if
    html = ''
    try:
        req = urllib.request.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' })
        if data:
            data = urllib.parse.urlencode(data).encode()
            html = urllib.request.urlopen(req, data=data).read().decode().strip()
        else:
            html = urllib.request.urlopen(req).read().decode().strip()
    except:
        sys.stderr.write("Error while retrieving URL: %s\n" % url)
        if data:
            sys.stderr.write("Data sent: %s\n" % data)
        sys.exit()
    return html

def getUserAgent():
    """ Return a cool user-agent to hide Python user-agent """
    
    useragents = [
        'Mozilla/5.0', 
    ]
    return random.choice(useragents)

def getVersion():
    return __version__

def getWikiEngine(url=''):
    """ Returns wiki engine of a URL, if known """
    
    wikiengine = 'unknown'
    if url:
        html = getURL(url=url)
    else:
        return wikiengine.lower()
    
    if re.search(
            r'(?im)(<meta name="generator" content="DokuWiki)|dokuwiki__site',
            html):
        wikiengine = 'dokuwiki'
    elif re.search(r'(?im)(alt="Powered by MediaWiki"|<meta name="generator" content="MediaWiki)', html):
        wikiengine = 'mediawiki'
    elif re.search(r'(?im)(>MoinMoin Powered</a>|<option value="LocalSiteMap">)', html):
        wikiengine = 'moinmoin'
    elif re.search(r'(?im)(twikiCurrentTopicLink|twikiCurrentWebHomeLink|twikiLink)', html):
        wikiengine = 'twiki'
    elif re.search(r'(?im)(<!--PageHeaderFmt-->)', html):
        wikiengine = 'pmwiki'
    elif re.search(r'(?im)(<meta name="generator" content="PhpWiki|<meta name="PHPWIKI_VERSION)', html):
        wikiengine = 'phpwiki'
    elif re.search(r'(?im)(<meta name="generator" content="Tiki Wiki|Powered by <a href="http://(www\.)?tiki\.org"| id="tiki-(top|main)")', html):
        wikiengine = 'tikiwiki'
    elif re.search(r'(?im)(foswikiNoJs|<meta name="foswiki\.|foswikiTable|foswikiContentFooter)', html):
        wikiengine = 'foswiki'
    elif re.search(r'(?im)(<meta http-equiv="powered by" content="MojoMojo)', html):
        wikiengine = 'mojomojo'
    elif re.search(r'(?im)(id="xwiki(content|nav_footer|platformversion|docinfo|maincontainer|data)|/resources/js/xwiki/xwiki|XWiki\.webapppath)', html):
        wikiengine = 'xwiki'
    elif re.search(r'(?im)(<meta id="confluence-(base-url|context-path)")', html):
        wikiengine = 'confluence'
    elif re.search(r'(?im)(<meta name="generator" content="Banana Dance)', html):
        wikiengine = 'bananadance'
    elif re.search(r'(?im)(Wheeled by <a class="external-link" href="http://www\.wagn\.org">|<body id="wagn">)', html):
        wikiengine = 'wagn'
    elif re.search(r'(?im)(<meta name="generator" content="MindTouch)', html):
        wikiengine = 'mindtouch'  # formerly DekiWiki
    elif re.search(r'(?im)(<div class="wikiversion">\s*(<p>)?JSPWiki|xmlns:jspwiki="http://www\.jspwiki\.org")', html):
        wikiengine = 'jspwiki'
    elif re.search(r'(?im)(Powered by:?\s*(<br ?/>)?\s*<a href="http://kwiki\.org">|\bKwikiNavigation\b)', html):
        wikiengine = 'kwiki'
    elif re.search(r'(?im)(Powered by <a href="http://www\.anwiki\.com")', html):
        wikiengine = 'anwiki'
    elif re.search(r'(?im)(<meta name="generator" content="Aneuch|is powered by <em>Aneuch</em>|<!-- start of Aneuch markup -->)', html):
        wikiengine = 'aneuch'
    elif re.search(r'(?im)(<meta name="generator" content="bitweaver)', html):
        wikiengine = 'bitweaver'
    elif re.search(r'(?im)(powered by <a href="[^"]*\bzwiki.org(/[^"]*)?">)', html):
        wikiengine = 'zwiki'
    # WakkaWiki forks
    elif re.search(r'(?im)(<meta name="generator" content="WikkaWiki|<a class="ext" href="(http://wikka\.jsnx\.com/|http://wikkawiki\.org/)">)', html):
        wikiengine = 'wikkawiki'  # formerly WikkaWakkaWiki
    elif re.search(r'(?im)(<meta name="generator" content="CoMa Wiki)', html):
        wikiengine = 'comawiki'
    elif re.search(r'(?im)(Fonctionne avec <a href="http://www\.wikini\.net)', html):
        wikiengine = 'wikini'
    elif re.search(r'(?im)(Powered by <a href="[^"]*CitiWiki">CitiWiki</a>)', html):
        wikiengine = 'citiwiki'
    elif re.search(r'(?im)(Powered by <a href="http://wackowiki\.com/|title="WackoWiki")', html):
        wikiengine = 'wackowiki'
    elif re.search(r'(?im)(Powered by <a href="http://www\.wakkawiki\.com)', html):
        # This may not work for heavily modded/themed installations, e.g.
        # http://operawiki.info/
        wikiengine = 'wakkawiki'
    # Custom wikis used by wiki farms
    elif re.search(r'(?im)(var wikispaces_page|<div class="WikispacesContent)', html):
        wikiengine = 'wikispaces'
    elif re.search(r'(?im)(Powered by <a href="http://www\.wikidot\.com">|wikidot-privacy-button-hovertip|javascript:WIKIDOT\.page)', html):
        wikiengine = 'wikidot'
    elif re.search(r'(?im)(IS_WETPAINT_USER|wetpaintLoad|WPC-bodyContentContainer)', html):
        wikiengine = 'wetpaint'
    elif re.search(r'(?im)(<div id="footer-pbwiki">|ws-nav-search|PBinfo *= *{)', html):
        # formerly PBwiki
        wikiengine = 'pbworks'
    # if wikiengine == 'Unknown': sys.stderr.write(html)

    return wikiengine.lower()

def fixBOM(r):
    """Strip Unicode BOM"""
    if request.text.startswith(u'\ufeff'):
        request.encoding = 'utf-8-sig'
    return request.text

def handleStatusCode(response):
    statuscode = response.status_code
    if statuscode >= 200 and statuscode < 300:
        return

    sys.stderr.write("HTTP Error %d.\n" % statuscode)
    if statuscode >= 300 and statuscode < 400:
        sys.stderr.write("Redirect should happen automatically: please report this as a bug.\n")
        sys.stderr.write('%s\n' % response.url)

    elif statuscode == 400:
        sys.stderr.write("Bad Request: The wiki may be malfunctioning.\n")
        sys.stderr.write("Please try again later.\n")
        sys.stderr.write('%s\n' % response.url)
        sys.exit(1)

    elif statuscode == 401 or statuscode == 403:
        sys.stderr.write("Authentication required.\n")
        sys.stderr.write("Please use --userpass.\n")
        sys.stderr.write('%s\n' % response.url)

    elif statuscode == 404:
        sys.stderr.write("Not found. Is Special:Export enabled for this wiki?\n")
        sys.stderr.write('%s\n' % response.url)
        sys.exit(1)

    elif statuscode == 429 or (statuscode >= 500 and statuscode < 600):
        sys.stderr.write("Server error, max retries exceeded.\n")
        sys.stderr.write("Please resume the dump later.\n")
        sys.stderr.write('%s\n' % response.url)
        sys.exit(1)

def printImageNames(config={}):
    """ Print list of page titles for this wiki """
    
    for imagename in getImageNames(config=config):
        sys.stdout.write('%s\n' % (imagename))
        
def printNamespaces(config={}):
    """ Print list of namespaces for this wiki """
    
    namespacenames = getNamespaces(config=config)
    for namespaceid, namespacename in namespacenames.items():
        sys.stdout.write('%s %s\n' % (namespaceid, namespacename))
        
def printPageTitles(config={}):
    """ Print list of page titles for this wiki """
    
    for pagetitle in getPageTitles(config=config):
        sys.stdout.write('%s\n' % (pagetitle))

def resumePreviousDump(config={}):
    if config['wikiengine'] == 'mediawiki':
        import mediawiki
        mediawiki.mwResumePreviousDump(config=config)
    elif config['wikiengine'] == 'wikispaces':
        import wikispaces
        wikispaces.wsResumePreviousDump(config=config)
    else:
        sys.stderr.write("Wikiengine %s not supported. Exiting.\n" % (config['wikiengine']))

def reverseReadline(filename, buf_size=8192, truncate=False):
    """a generator that returns the lines of a file in reverse order"""
    # Original code by srohde, abdus_salam: cc by-sa 3.0
    # http://stackoverflow.com/a/23646049/718903
    with open(filename, 'r+') as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        total_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(total_size, offset + buf_size)
            fh.seek(-offset, os.SEEK_END)
            buffer = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split('\n')
            # the first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # if the previous chunk starts right from the beginning of line
                # do not concat the segment to the last line of new chunk
                # instead, yield the segment first 
                if buffer[-1] is not '\n':
                    lines[-1] += segment
                else:
                    if truncate and '</page>' in segment:
                        pages = buffer.split('</page>')
                        fh.seek(-offset+buf_size-len(pages[-1]), os.SEEK_END)
                        fh.truncate
                        raise StopIteration
                    else:
                        yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if truncate and '</page>' in segment:
                    pages = buffer.split('</page>')
                    fh.seek(-offset-len(pages[-1]), os.SEEK_END)
                    fh.truncate
                    raise StopIteration
                else:
                    yield lines[index]
        yield segment

def saveConfig(config={}):
    """ Save config file """
    
    # Do not save config['other'] as it has session info and other stuff
    config2 = config.copy()
    config2['other'] = {}
    with open('%s/%s' % (config['path'], config['other']['configfilename']), 'w') as outfile:
        sys.stderr.write('Saving config file...\n')
        try: #str
            cPickle.dump(config2, outfile)
        except: #bytes
            with open('%s/%s' % (config['path'], config['other']['configfilename']), 'wb') as outfile:
                cPickle.dump(config2, outfile)

def saveImageNames(config={}, imagenames=[]):
    """ Save image list in a file, including filename, url and uploader """

    imagesfilename = '%s-%s-images.txt' % (
        domain2prefix(config=config), config['date'])
    imagesfile = open('%s/%s' % (config['path'], imagesfilename), 'w')
    imagesfile.write('\n'.join(['%s\t%s\t%s' % (filename, url, uploader) for filename, url, uploader in imagenames]))
    imagesfile.write('\n--END--')
    imagesfile.close()
    sys.stderr.write('Image filenames and URLs saved at... %s ' % imagesfilename)

def savePageTitles(config={}, pagetitles=None):
    pagetitlesfilename = '%s-%s-titles.txt' % (
        domain2prefix(config=config), config['date'])
    with open('%s/%s' % (config['path'], pagetitlesfilename), 'wt') as f:
        for pagetitle in pagetitles:
            output = '%s\n' % (pagetitle)
            f.write(output)

        # TODO: Sort to remove dupes? In CZ, Widget:AddThis appears two times:
        # main namespace and widget namespace.
        # We can use sort -u in UNIX, but is it worth it?
        f.write('--END--\n')
        f.close()
    sys.stderr.write('Page titles saved at... %s\n' % (pagetitlesfilename))

def undoHTMLEntities(text=''):
    """ Undo some HTML codes """

    # i guess only < > & " ' need conversion
    # http://www.w3schools.com/html/html_entities.asp
    text = re.sub('&lt;', '<', text)
    text = re.sub('&gt;', '>', text)
    text = re.sub('&amp;', '&', text)
    text = re.sub('&quot;', '"', text)
    text = re.sub('&#039;', '\'', text)

    return text

def welcome():
    """ Print opening message """
    
    message = """
#########################################################################
# Welcome to WikiTeam's tools v%s (GPL v3)                           #
# Tools for downloading and preserving wikis                            #
# More info at: https://github.com/WikiTeam/wikiteam                    #
#########################################################################

#########################################################################
# Copyright (C) 2011-2016 WikiTeam                                      #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program.  If not, see <http://www.gnu.org/licenses/>. #
#########################################################################
""" % (getVersion())
    sys.stderr.write(message)

def loadConfig(config={}):
    """ Load config file """
    
    try:
        with open('%s/%s' % (config['path'], config['other']['configfilename']), 'r') as infile:
            sys.stderr.write('Loading config file...\n')
            config = cPickle.load(infile)
    except:
        sys.stderr.write('ERROR: There is no config file. we can\'t resume. Start a new dump.\n')
        sys.exit()

    return config

def main(params=[]):
    """ Main function """
    
    config = getParameters(params=params)    
    avoidWikimediaProjects(config=config)
    config = createDumpPath(config=config)
    if config['other']['resume']:
        # Resume dump
        welcome()
        config = loadConfig(config=config)
        resumePreviousDump(config=config)
    elif config['pages'] or config['images'] or config['logs']:
        # New dump
        welcome()
        os.mkdir(config['path'])
        saveConfig(config=config)
        createNewDump(config=config)
    elif config['metainfo']:
        # No dumps. Print meta info params
        if config['metainfo'] == 'get_api':
            print(getAPI(config=config))
        elif config['metainfo'] == 'get_index':
            print(getIndex(config=config))
        elif config['metainfo'] == 'get_page_titles':
            printPageTitles(config=config)
        elif config['metainfo'] == 'get_image_names':
            printImageNames(config=config)
        elif config['metainfo'] == 'get_namespaces':
            printNamespaces(config=config)
        elif config['metainfo'] == 'get_wiki_engine':
            print(config['wikiengine'])
        sys.exit()
            
    bye()

if __name__ == "__main__":
    main()

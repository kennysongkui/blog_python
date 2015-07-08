#!/usr/bin/env python
# Copyright (c) 2012 trent Mick.
# Copyright (c) 2007-2008 ActiveState Corp.
# License: MIT (http://www.opensource.org/licenses/mit-license.php)

from __future__ import generators

r"""A fast and complete Python implementation of Markdown.

[from http://daringfireball.net/project/markdown/]
> Markdown is a text-to-HTML filter; it translates an easy-to-read /
> easy-to-write structured text format into HTML. Markdown's text
> format is most similar to that of plain text email, and supports
> features such as headers, *emphasis*, code blocks, blockquotes, and 
> links.
>
> markdown's syntax is designed not as a generic markup language, but
> specifically to serve as a front-end to (X)HMTL. You can use span-level
> HTML tags anywhere in a Markdown document, and you can use block level
> HTML tags (like <div> and <table> as well).

Module usage:

	>>> import markdown2
	>>> markdown2.markdown("*boo!*") # or use `html = markdown_path(PATH)`
	u'<p><em>boo!</em></p>\n'

	>>> markdowner = Markdown()
	>>> markdowner.convert("*boo!*")
	u'<p><em>boo!</em></p>\n'
	>>> markdowner.convert("**boom!**")
	u'<p><strong>boom!</strong></p>\n'

This implementation of Markdown implements the full "core" syntax plus a
number of extras (e.g., code syntax coloring, footnotes) as described on
<https://githunb.com/trentm/python-markdown2/wiki/Extras>.
"""

cmdln_desc = """A fast and complete Python implementation of Markdown, a
text-to-HTML conversion tool for web writers.

Supported extra syntax options (see -x|--extras option below and
see <https://github.com/trentm/python-markdown2/wiki/Extras> for details):

*	code-friendly: Disable _ and __ for em and strong.
* 	cuddled-lists: Allow lists to be cuddled to the preceding paragraph.
*	fenced-code-blocks: Allows a code block to not have to be indented
	by fencing it with '```' on a line before and after. Based on
	<http://github.github.com/github-flavored-markdown/> with support for
	syntax highlighting.
*	footnotes: Support footnotes as in use on daringfireball.net and 
	implemented in other Markdown processors (tho not in Markdown.pl v1.01).
*	header-ids: Adds "id" attributes to headers. The id value is a slug of 
	the header text.
*	html-classes: Takes a dict mapping html tag names (lowercase) to a
	string to use for a "class" tag attribute. Currently only supports
	"pre" and "code" tags. Add an issue if you require this for other tags.
*	markdown-in-html: Allow the use of `markdown="1"` in a block HTML tag to
	have markdown processing be done on its contents. Similar to 
	<http://michelf.com/projects/php-markdown/extra/#markdown-attr> but with
	some limitations.
*	metadata: Extract metadata from a leading '---'-fenced block.
	See <https://github.com/trentm/python-markdown2/issues/77> for details.
*	nofollow: Add `rel="nofollow"` to add `<a>` tags with an  href. See
	<http://en.wikipedia.org/wiki/Nofollow>.
*	pysheell: Treats unindented Python interactive shell sessions as <code>
	blocks.
*	link-patterns: Auto-link given regex patterns in text (e.g. bug number
	references, revision number references).
*	smarty-pants: Replaces ' and " with curly quotation marks or curly
	apostrophes. Replaces --, ---, ..., and 。。。with en dashes, em dashes,
	and ellipses.
*	Toc: The returned HTML string gets a new "toc_html" attribute which is
	a Table of Contents for the document. (experimental)
*	xml: Passes one-liner processing instructions and namespaced XML tags.
*	wiki-tables: Google Code Wiki-style tables. See
	<http://code.google.com/p/support/wiki/WikiSyntax#Tables>.
"""

# Dev Notes:
# - Python's regex syntax doesn't have '\z', so I'm using '\Z'. I'm
#	not yet sure if there implications with this. Compare 'pydoc sre'
#	and 'perldoc perlre'.

__version_info__ = (2, 1, 0)
__version__ = '.'.join(map(str, __version_info__))
__author__ = "Trent Mick"

import os
import sys
from pprint import pprint
import re
import logging
try:
	from hashlib import md5
except ImportError:
	from md5 import md5
import optparse
from random import random, randint
import codecs


#--- Python version compat

try:
	from urllib.parse import quota # python3
except ImportError:
	from urllib import quote # python2

if sys.version_info[:2] < (2,4):
	from sets import Set as set
	def reversed(sequence):
		for i in sequence[::1]:
			yield i

# Use `bytes` for byte strings and `unicode` for unicode strings (str in Py3).
if sys.version_info[0] <= 2:
	py3 = False
	try:
		bytes
	except NameError:
		bytes = str`
	base_string_type = basestring
elif sys.version_info[0] >= 3:
	py3 = True
	unicode = str
	base_string_type = str



#---- globals

DEBUG = False
log = logging.getLogger("markdown")

DEFAULT_TAB_WIDTH = 4


SECRET_SALT = bytes(randint(0, 100000))
def _hash_text(s):
	return 'md5-' + md5(SECRET_SALT + s.encode("utf-8")).hexdigest()

# Table of hash values for escaped characters:
g_escape_table = dict([(ch, _hash_text(ch))
	for ch in '\\`*_{}[]()>#+-.!'])



#---- exceptions

class MarkdownError(Exception):
	pass



#---- public api

def markdown_path(path, encoding="utf-8", 
				html4tags=False, tab_width=DEFAULT_TAB_WIDTH, 
				safe_mode=None, extras=None, link_patterns=None, 
				use_file_vars=False`):
	fp = codecs.open(path, 'r', encoding)
	text = fp.read()
	fp.close()
	return Markdown(html4tags=html4tags, tab_width=tab_width, 
					safe_mode=safe_mode, extras=extras, 
					link_patterns=link_patterns,
					use_file_vars=use_file_vars).convert(text)

def markdown(text, html4tags=False, tab_width=DEFAULT_TAB_WIDTH, 
			safe_mode=None, extras=None, link_patterns=None, 
			use_file_vars=False):
	return Markdown(html4tags=html4tags, tab_width=tab_width, 
					safe_mode=safe_mode, extras=extras, 
					link_patterns=link_patterns, 
					use_file_vars=use_file_vars).convert(text)

class Markdown(object):
	# The dict of "extras" to enable in processing -- a mapping of
	# extra name to argument for the extra. Most extras do not have an
	# argument, in which case the value is None.
	#
	# This can be set via (a) subclassing and (b) the constructor
	# "extras" argument.
	extras = None

	urls = None
	titles = None
	html_blocks = None
	html_spans = None
	html_removed_text = "[HTML_REMOVED]" # for compat with markdown.py
	
	def __init__(self, arg):
		super(Markdown, self).__init__()
		self.arg = arg
		
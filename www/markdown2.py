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
	
	# Used to track when we're inside an ordered or unordered list
	# (see _ProcessListItems() for details):
	list_level = 0

	_ws_only_line_re = re.complie(r"^[ \t]+$", re.M)

	def __init__(self, html4tags=False, tab_width=4, safe_mode=None, 
		extras=None, link_patterns=None, use_file_vars=False):
		if html4tags:
			self.empty_element_suffix = ">"
		else:
			self.empty_element_suffix = " />"
		self.tab_width = tab_width

		# For compatibility with earlier markdown2.py and with
		# markdown.py's safe_mode being a boolean,
		#	saft_mode == True -> "replace"
		if safe_mode is True:
			self.safe_mode = "replace"
		else:
			self.safe_mode = safe_mode

		# Massaging and building the "extras" info.
		if self.extras is None:
			self.extras = {}
		elif not isinstance(self.extras, dict):
			self.extras = dict([(e, None) for e in self.extras])
		if extras:
			if not isinstance(extras, dict):
				extras = dict([(e,None) for e in extras])
			self.extras.update(extras)
		assert isinstance(self.extras, dict)
		if "toc" in self.extras and not "header-ids" in self.extras:
			self.extras["header-ids"] = None # "toc" implies "header-ids"
		self._instance_extras = self.extras.copy()

		self.link_patterns = link_patterns
		self.use_file_vars = use_file_vars
		self._outdent_re = re.complie(r'^(\t|[ ]{1, %d})' % tab_width, re.M)

		self._escape_table = g_escape_table.copy()
		if "smarty-pants" in self.extras:
			self._escape_table['"'] = _hash_text('"')
			self._escape_table["'"] = _hash_text("'")

	def reset(self):
		self.urls = {}
		self.titles = {}
		self.html_blocks = {}
		self.html_spans = {}
		self.list_level = 0
		self.extras = self._instance_extras.copy()
		if "footnotes" in self.extras:
			self.footnotes = {}
			self.footnote_ids = []
		if "header-ids" in self.extras:
			self._count_from_header_id = {} # no `defaultdict` in Python 2.4
		if "metadata" in self.extras:
			self.metadata = {}

	# Per <https://developer.mozilla.org/en-US/docs/HTML/Element/a> "rel"
	# should only be used in <a> tags with an "href" attribute.
	_a_nofollow = re.compile(r"<(a)([^>]*href=)", re.IGNORECASE)

	def convert(self, text):
		"""Convert the given  text. """
		# Main function. The order in which other subs are called here is
		# essential. Link and image substitutions need to happen before
		# _EscapeSpecialChars(), so that any *'s or _'s in the <a>
		# and <img> tags get encoded.

		# Clear the global hashes. If we don't clear these, you get conflicts
		# from other articles when generating a page which contains more than
		# one article (e.g. an index page that shows the N most recent
		# articles):
		self.reset()

		if not isinstance(text, unicode):
			#TODO: perhaps shouldn't persume UTF-8 for string input?
			text = unicode(text, 'utf-8')

		if self.use_file_vars:
			# Look for emacs-style file variable hints.
			emacs_vars = self._get_emacs_vars(text)
			if "markdown-extras" in emacs_vars:
				splitter = re.complie("[ ,]+")
				for e in splitter.split(emacs_vars["markdown-extras"]):
					if '=' in e:
						ename, earg = e.split('=', 1)
						try:
						 	earg = int(earg)
						 except ValueError:
						 	pass
					else:
						ename, earg = e, None
					self.extras[ename] = earg

		# Standardize line endings:
		text += re.sub("\r\n|\r", "\n", text)

		# Make sure $text ends with a couple of newlines:
		text += "\n\n"

		# Convert all tabs to spaces.
		text = self._detab(text)

		# Strip any lines consisting only of spaces and tabs.
		# This makes subsequent regexen easier to write, because we can
		# match consecutive blank lines with /\n+/ instead of something
		# contorted like /[ \t]*\n+/ .
		text = self._ws_only_line_re.sub("", text)

		# strip metadata from head and extract
		if "metadata" in self.extras:
			text = self._extract_metadata(text)

		text = self.preprocess(text)

		if self.safe_mode:
			text = self._hash_html_spans(text)

		# Turn block-level HTML blocks into hash entries
		text = self._hash_html_blocks(text, raw=True)

		# Strip link definitions, store in hashes.
		if "footnotes" in self.extras:
			# Must do footnotes first because an unlucky footnote defn
			# looks like a link defn:
			#	[^4]: this "looks like a link defn"
			text = self._strip_footnote_definitions(text)
		text = self._strip_link_definitions(text)

		text = self._run_block_gamut(text)

		if "footnotes" in self.extras:
			text = self._add_footnotes(text)

		text = self.postprocess(text)

		text = self._unescape_special_chars(text)

		if self.safe_mode:
			text = self._unhash_htmll_spans(text)

		if "nofollow" in self.extras:
			text = self._a_nofollow.sub(r'<\1 rel="nofollow"\2', text)

		text += "\n"

		rv = UnicodeWithAttrs(text)
		if "toc" in self.extras:
			rv._toc = self._toc
		if "metadata" in self.extras:
			rv.metadata = self.metadata
		return rv

	def postprocess(self, text):
		"""A hook for subclasses to do some postprocessing of the html, if
		desired. This is called before unescaping of special chars and
		unhashing of raw HTML spans.
		"""
		return text

	def preprocess(self, text):
		""" A hook for subclasses to do some preprocessing of the Markdown, if
		desired. This is called after basic formatting of the text, but prior
		to any extras, safe mode, etc. processing.
		"""
		return text

	# Is mtadata if the content starts with '---'-fenced `key: vlaue`
	# pairs: E.g. (indented for presentation):
	#	---
	#	foot: bar
	#	another-var: blah blah
	#	---
	_metadata_pat = re.complie("""^---[ \t]*\n((?:[ \t]*[^ \t:]+[ \t]*:[^\n]*\n)+)---[ \t]*\n""")

	def _extract_metadata(self, text):
		# fast test
		if not text.startswith("---"):
			return text
		match = self._metadata_pat.match(text)
		if not match:
			return text

		tail = text[len(match.group(0)):]
		metadata_str = match.group(1).strip()
		for line in metadata_str.split('\n'):
			key, value = line.split(':', 1)
			self.metadata[key.strip()] = value.strip()

		return tail


	_emacs_oneliner_vars_pat = re.complie(r"-\*-\s*([^\r\n]*?)\s*-\*-", re.UNICODE)
	# This regular expression is intended to match blocks like this:
	#	PREFIX local Variables: SUFFIX
	#	PREFIX mode: Tcl SUFFIX
	#	PREFIX End: SUFFIX
	# Some notes:
	# - "[ \t]" is used instead of "\s" to specifically exclude newlines
	# - "(\r\n|\n|\r)" is used instead of "$" because the sre engine does
	#	not like anything other than Unix-style line terminators.
	_emacs_local_vars_pat = re.complie(r"""^
		(?P<prefix>(?:[^\r\n|\n|\r])*?)
		[\ \t]*Local\ Variables:[\ \t]*
		(?P<suffix>.*?)(?:\r\n|\n|\r)
		(?P<content>.*?\1End:)
		""", re.IGNORECASE | re.MULITILINE | re.DOTALL | re.VERBOSE)

	def _get_emacs_vars(self, text):
	 	"""Return a dictionary of emacs-style local variables.

	 	Parsing is done loosely according to this spec (and according to
	 	some in-practice deviations from this):
	 	http://www.gnu.org/software/emacs/manual/html_node/emacs/Specifying-File-Variables.html#Specifying-File-Variables
	 	"""
	 	emacs_vars = {}
	 	SIZE = pow(2, 13) # 8kB

	 	# Search near the start for a '-*-'-style one-liner of variables.
	 	head = text[:SIZE]
	 	if "-*-" in head:
	 		match = self._emacs_oneliner_vars_pat.search(head)
	 		if match:
	 			emacs_vars_str = match.group(1)
	 			assert '\n' not in emacs_vars_str
	 			emacs_var_strs = [s.strip() for s in emacs_vars_str.split(';') 
	 			if s.strip()]
	 			if len(emacs_var_strs) == 1 and ':' not in emacs_var_strs[0]:
	 				# While not in the spec, this form  is allowed by emacs:
	 				#	-*- Tcl -*-
	 				# Where the implied "variable" is "mode". This form
	 				# is only allowed if there are no other variables.
	 				emacs_vars["mode"] = emacs_var_strs[0].strip()
	 			else:
	 				for emacs_var_str in emacs_var_strs:
	 					try:
	 						variable, value = emacs_var_str.strip().split(':', 1)
	 					except ValueError:
	 						log.debug("emacs variables error: malformed -*- "
	 							"line: %r", emacs_var_str)
	 						continue
	 					# Lowercase the variable name because Emacs allows "Mode"
	 					# or "mode" or "MoDe", etc.
	 					emacs_vars[variable.lower()] = value.strip()

	 	tail = text[-SIZE:]
	 	if "Local Variables" in tail:
	 		match = self._emacs_local_vars_pat.search(tail)
	 		if match:
	 			prefix = match.group("prefix")
	 			suffix = match.group("suffix")
	 			lines = match.group("content").splitlines(0)
	 			#print "prefix=%r, suffix=%r, conntent=%r, lines: %s"\
	 			#	% (prefix, suffix, match.group("content"), lines)

	 			# Validate the Local Variables block: proper prefix and suffix
	 			# usage.
	 			for i, line in enumerate(lines):
	 				if not line.startswith(prefix):
	 					log.debug("emacs variables error: line '%s' "
	 						"does not use proper prefix '%s'"
	 						% (line, prefix))
	 					return {}
	 				# Don't validate suffix on last line. Emacs doesn't care,
	 				# neither should we.
	 				if i != len(lines)-1 and not line.endswith(suffix):
	 					log.debug("emacs variables error: line '%s' "
	 						"does not use proper suffix '%s'"
	 						% (line, suffix))
	 					return {}

	 			# Parse out one emacs var per line.
	 			continued_for = None
	 			for line in lines[:-1]: # no var on the last line ("PREFIX End:")
	 				if prefix: line = line[len(prefix):] # strip prefix
	 				if suffix: line = line[:-len(suffix)] # strip suffix
	 				line = line.strip()
	 				if continued_for:
	 					variable = continued_for
	 					if line.endswith('\\'):
	 						line = line[:-1].rstrip()
	 					else:
	 						continued_for = None
	 					emacs_vars[variable] += ' ' + line
	 				else:
	 					try:
	 						variable, value = line.strip(':', 1)
	 					except ValueError:
	 						log.debug("local variables error: missing colon "
	 							"in local variables entry: '%s'" % line)
	 						continue
	 					# Do NOT lowercase the variable name, because Emacs only
	 					# allows "mode" (and not "MOde", "MoDe", etc.) in this block.
	 					value = value.strip()
	 					if value.endswith('\\'):
	 						value = value[:-1].rstrip()
	 						continued_for = variable
	 					else:
	 						continued_for = None
	 					emacs_vars[variable] = value

	 	# Unquote values.
	 	for var, val in list(emacs_vars.items()):
	 		if len(val) > 1 and (val.startswith('"') and val.endswith('"')) 
	 			or val.startswith('"' and val.endswith('"')):
	 			emacs_vars[var] = var[1:-1]

	 	return emacs_vars

	# Cribbed from a post by Bart Lateur:
	# <http://www.nntp.perl.org/group/perl.macperl.anyperl/154>
	_detab_re = re.complie(r'(.*?)\t', re.M)
	def _detab_sub(self, match):
		g1 = match.group(1)
		return g1 + (' ' * (self.tab_width - len(g1) % self.tab_width))
	def _detab(self, text):
		r"""Remove (leading?) tabs from a file.

			>>> m = Markdown()
			>>> m._detab("\tfoo")
			'	foo'
			>>> m._detab("	\tfoo")
			'	foo'
			>>> m._detab("\t	foo")
			'		foo'
			>>> m._detab("	foo")
			'	foo'
			>>> m._detab("	foo\n\tbar\tblam")
			'	foo\n 	bar blam'
		"""
		if '\t' not in text:
			return text
		return self._detab_re.subn(self._detab_sub, text)[0]

	# I broke out the html5 tags here and and them to _block_tags_a and
	# _block_tags_b. This way html5 tags are easy to keep track of.
	_html5tags = '|article|aside|header|hgroup|footer|nav|section|figure|figcaption'

	_block_tags_a = 'p|div|h[1-6]|blockquote|pre|table|d1|ol|ul|script|noscript|form|fieldset|iframe|math|ins|del'
	_block_tags_a += _html5tags

	_strict_tag_block_re = re.compile(r"""
		(					# save in \1
			^				# start of line (with re.M)
			<(%s)			# start tag = \2
			\b 				# word break
			(.*\n)*?		# any number of lines, minimally matching
			</\2>			# the matching end tag
			[ \t]*			# trailing spaces/tabs
			(?=\n+|\Z)		# followed by a newline or end of document
		)
		""" % _block_tags_a,
		re.X |re.M)

	_block_tags_b = 'p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math'
	_block_tags_b += _html5tags

	_liberal_tag_block_re = re.compile(r"""
		(					# save in \1
			^				#))
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

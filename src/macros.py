# vim: set tw=0 fileencoding=utf-8:

import binascii
from datetime import datetime
import mimetypes
import os.path
import re
from xml.sax.saxutils import escape
import urllib
import urlparse
import sys

# Base for sitemap and RSS, where absolute URLs are used.
BASE_URL = 'http://www.the-pulsar.com'

page = { 'title': 'untitled page' }

# Заголовки меток
tagtitles = {
    'podcast': u'подкасты',
}

def get_post_labels(post):
    if not post.has_key('labels'):
        labels = []
    else:
        labels = [l.strip() for l in post['labels'].split(',')]
    if post.has_key('file') and 'podcast' not in labels:
        labels.append('podcast')
    if post.url.startswith('blog.') and post.url != 'blog.html' and 'blog' not in labels:
        labels.append('blog')
    return sorted(labels)

def get_label_url(label):
    return '/' + label.strip().replace(' ', '_') + '.html'


def get_label_text(label):
    if tagtitles.has_key(label):
        return tagtitles[label]
    return label


def get_label_stats(posts):
    labels = {}
    for post in posts:
        for label in get_post_labels(post):
            if not labels.has_key(label):
                labels[label] = 1
            else:
                labels[label] += 1
    # Удаляем метки, для которых нет страниц.
    for label in labels.keys():
        if not os.path.exists('./input' + os.path.splitext(get_label_url(label))[0] + '.md'):
            del labels[label]
    return labels

def get_tag_cloud(posts):
    labels = get_label_stats(posts)
    output = '<ul id="tcloud">'
    for label in sorted(labels.keys()):
        output += '<li><a href="%s">%s</a> (%u)</li>' % (get_label_url(label), label, labels[label])
    output += '</ul>'
    return output

def page_classes(page):
    """
    Возвращает строку с классами CSS для поста.
    """
    classes = [label for label in get_post_labels(page)]
    if classes:
        return u' class="%s"' % u' '.join(classes)
    return u''

def pagelist(pages, limit=5, label=None, show_dates=True):
    output = u''
    pages = [page for page in pages if 'date' in page]
    if label is not None:
        pages = [page for page in pages if page.has_key('labels') and label in get_post_labels(page)]
    else:
        pages = [page for page in pages if page.url.startswith('blog.')]
    pages.sort(key=lambda p: p.get('date'), reverse=True)
    if limit is not None:
        pages = pages[:limit]
    for page in pages:
        output += u'  * '
        if limit is None and show_dates:
            date = datetime.strptime(page.date, '%Y-%m-%d').strftime('%d.%m.%Y')
            output += u'<span>%s</span> : ' % date
        output += u'[%s](%s)\n' % (page.get('post', page.get('title')), page.get('url'))
    if output:
        return output
    return u'Ничего нет.'


def page_title(page, h='h2'):
    """Выводит заголовок страницы, если он есть."""
    title = page.get('post', page.get('title'))
    if title:
        return u'<%s>%s</%s>' % (h, page.get('post', page.get('title')), h)
    return u''


def page_meta(page):
    parts = []
    if 'date' in page:
        parts.append(datetime.strptime(page['date'], '%Y-%m-%d').strftime('%Y.%m.%d'))
    if 'file' in page:
        parts.append(u'<a href="%s">скачать</a>' % page['file'])
    labels = get_post_labels(page)
    if len(labels):
        parts.append(u', '.join([u'<a class="tag" href="%s">%s</a>' % (get_label_url(tag), get_label_text(tag)) for tag in labels]))
    if parts:
        return u'<p class="meta">%s</p>' % u'; '.join(parts)
    return u''


def youtube(video_id):
    # высота: 300 + 35 на контролы
    return u'<iframe class="youtube-player" type="text/html" ' + \
        u'width="540" height="335" ' + \
        u'src="http://www.youtube.com/embed/' + unicode(video_id) + \
        u'" frameborder="0"></iframe>'

_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
%s
</urlset>
"""

_SITEMAP_URL = """
<url>
    <loc>%s</loc>
    <lastmod>%s</lastmod>
    <changefreq>%s</changefreq>
    <priority>%s</priority>
</url>
"""

def once_sitemap():
    """Generate Google sitemap.xml file."""
    date = datetime.strftime(datetime.now(), "%Y-%m-%d")
    urls = []
    for p in pages:
        url = p.url
        if '://' not in url:
            url = BASE_URL + '/' + url
            urls.append(_SITEMAP_URL % (url, date,
                p.get("changefreq", "monthly"), p.get("priority", "0.8")))
    fname = os.path.join(options.project, "output", "sitemap.xml")
    fp = open(fname, 'w')
    fp.write(_SITEMAP % "".join(urls))
    fp.close()

# -----------------------------------------------------------------------------
# generate rss feed
# -----------------------------------------------------------------------------

import email.utils
import time

_RSS = u"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>%s</title>
<link>%s</link>
<description>%s</description>
<language>ru-RU</language>
<pubDate>%s</pubDate>
<lastBuildDate>%s</lastBuildDate>
<docs>http://blogs.law.harvard.edu/tech/rss</docs>
<generator>Poole</generator>
%s
</channel>
</rss>
"""

def write_rss(pages, title, description, label=None):
    base = BASE_URL

    xml = u'<?xml version="1.0"?>\n'
    xml += u'<rss version="2.0">\n'
    xml += u'<channel>\n'
    xml += u'<language>ru-RU</language>\n'
    xml += u'<docs>http://blogs.law.harvard.edu/tech/rss</docs>\n'
    xml += u'<generator>Poole</generator>\n'
    xml += u'<title>%s</title>\n' % escape(title)
    if label is None:
        xml += u'<link>%s/</link>\n' % base
    else:
        xml += u'<link>%s%s</link>\n' % (base, get_label_url(label))
    date = email.utils.formatdate()
    xml += u'<pubDate>%s</pubDate>\n' % date
    xml += u'<lastBuildDate>%s</lastBuildDate>\n' % date

    # leave only blog posts
    pages = [p for p in pages if p.has_key('post') and p.has_key('date') and '://' not in p.url]
    # filter by label
    if label is not None:
        pages = [p for p in pages if label in get_post_labels(p)]
    # sort by date
    pages.sort(key=lambda p: p.date, reverse=True)
    # process first 10 items
    for p in pages[0:10]:
        xml += u'<item>\n'
        xml += u'\t<title>%s</title>\n' % escape(p.post)
        link = u"%s/%s" % (BASE_URL, p.url)
        xml += u'\t<link>%s</link>\n' % link
        xml += u'\t<description>%s</description>\n' % escape(p.html)
        date = time.mktime(time.strptime("%s 12" % p.date, "%Y-%m-%d %H"))
        xml += u'\t<pubDate>%s</pubDate>\n' % email.utils.formatdate(date)
        xml += u'\t<guid>%s</guid>\n' % link
        if p.has_key('file'):
            mime_type = mimetypes.guess_type(urlparse.urlparse(p.file).path)[0]
            xml += u'\t<enclosure url="%s" type="%s"/>\n' % (p.file, mime_type)
        for l in get_post_labels(p):
            xml += u'\t<category>%s</category>\n' % l
        xml += u'</item>\n'

    xml += u'</channel>\n'
    xml += u'</rss>\n'

    if label is None:
        filename = 'rss.xml'
    else:
        filename = label.replace(' ', '_') + '.xml'
    print "info   : writing %s" % filename
    fp = open(os.path.join(output, filename), 'w')
    fp.write(xml.encode('utf-8'))
    fp.close()

def hook_postconvert_fix_toc():
    """
    Добавление оглавлений.
    """
    #for idx in range(0, len(pages)):
    #    pages[idx].html = mktoc(pages[idx].html)
    for page in pages:
        page.html = mktoc(page.html)

def mktoc(text):
    toc = ''
    r = re.compile('<h\d>(.*)</h\d>')
    m = r.search(text)
    while m:
        ref = '%08x' % (binascii.crc32(m.group(1).encode('utf-8')) & 0xffffffff)
        toc += '<li><a href="#%s">%s</a></li>' % (ref, m.group(1))
        text = text.replace(m.group(0), u'<h3 class="section_header" id="%s">%s <a name="%s" href="#%s" class="section_anchor">¶</a></h3>' % (ref, m.group(1), ref, ref))
        m = r.search(text)
    if len(toc):
        text = text.replace('[TOC]', '<ul id="toc">%s</ul>' % toc)
    return text

def hook_postconvert_rss():
    write_rss(pages, u'Urban Monkey', u'Personal home page updates.')
    for label in get_label_stats(pages).keys():
        write_rss(pages, u'Urban Monkey: ' + label, u'Записи из блога Urban Monkey с пометкой «%s».' % label, label)
	# FeedBurner сообщает о двух подписчиках, пусть полежит.
    os.symlink("rss.xml", os.path.join(output, "rss"))

def embed(page):
    if 'file' in page and page.file.endswith('.mp3'):
        furl = urllib.quote(page.file)
        return '<audio src="'+ page.file +'" controls="controls"><object type="application/x-shockwave-flash" width="300" height="20" data="/player.swf?file=' + furl + '&amp;width=300&amp;height=20&amp;controlbar=bottom"><param name="movie" value="' + furl + '" /><param name="wmode" value="window" /></object></audio>'
    return ''

def comments(page):
    if page.get('url').startswith('blog.'):
        settings = ''
        if page.has_key('disqus_url'):
            settings += 'var disqus_url = "'+ page['disqus_url'] +'";'
        else:
            settings += 'var disqus_identifier = "'+ page.url +'";'
        return '<div id="disqus_thread"></div><script type="text/javascript">if (window.location.href.indexOf("http://localhost:") == 0) var disqus_developer = 1;'+ settings +' (function() { var dsq = document.createElement(\'script\'); dsq.type = \'text/javascript\'; dsq.async = true; dsq.src = \'http://umonkeynet.disqus.com/embed.js\'; (document.getElementsByTagName(\'head\')[0] || document.getElementsByTagName(\'body\')[0]).appendChild(dsq); })();</script><noscript>Please enable JavaScript to view the <a href="http://disqus.com/?ref_noscript=umonkeynet">comments powered by Disqus.</a></noscript><a href="http://disqus.com" class="dsq-brlink">blog comments powered by <span class="logo-disqus">Disqus</span></a>'
    return ''

def title(page):
    t = 'Urban Monkey Workfare'
    if 'post' in page and 'file' in page:
        t = '<a href="/podcast.html">' + t + ' podcast</a>'
    elif 'post' in page:
        t = '<a href="/blog.html">' + t + ' blog</a>'
    elif page.url != 'index.html':
        t = '<a href="/index.html">' + t + '</a>'
    return t


def menu(page):
    items = {
        'ru': [
            ('news', 'News'),
            ('band', 'Band'),
            ('live', 'Live'),
            ('disco', 'Media'),
            ('shop', 'Shop'),
            ('contact', 'Contact'),
            ('links', 'Links'),
        ],
        'en': [
            ('news', 'News'),
            ('band', 'Band'),
            ('live', 'Live'),
            ('disco', 'Media'),
            ('shop', 'Shop'),
            ('contact', 'Contact'),
            ('links', 'Links'),
        ],
    }

    parts = os.path.splitext(os.path.basename(page.fname))[0].split('-', 1)
    if len(parts) < 2:
        return ''
    lang = parts[1]
    suffix = '-' + lang + '.md'

    output = u'<div id="menu"><ul>'
    for p in sorted(pages, key=lambda a: a.get('menu-index', 1)):
        if p.fname.endswith(suffix):
            name = os.path.basename(p.fname).split('-', 1)[0]
            output += u'<li class="%s"><a href="/%s-%s.html">%s</a></li>' % (name, name, lang, p.get('title', name))
    output += u'</ul></div>'
    return output

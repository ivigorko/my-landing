"""Проверка шаблона статей и размещения карточек перед публикацией."""
import argparse
import json
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = 'https://yanaprobeg.ru/'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    content: list = field(default_factory=list)

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, tag=None, cls=None, **attrs):
        return [node for node in self.walk()
                if (tag is None or node.tag == tag)
                and (cls is None or cls in node.attrs.get('class', '').split())
                and all(node.attrs.get(key) == value for key, value in attrs.items())]

    def text(self):
        return ''.join(item.text() if isinstance(item, Node) else item for item in self.content).strip()


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node('document')
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        self.stack[-1].content.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for position in range(len(self.stack) - 1, 0, -1):
            if self.stack[position].tag == tag:
                del self.stack[position:]
                break

    def handle_data(self, data):
        self.stack[-1].content.append(data)


def read(path):
    return Document(path.read_text(encoding='utf-8')).root


def local_target(root, page, url):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    target = (root / unquote(parsed.path).lstrip('/') if parsed.path.startswith('/')
              else page.parent / unquote(parsed.path)).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('путь выходит за каталог сайта')
    return target


def validate(root=ROOT):
    root = Path(root)
    errors = []

    def fail(page, message):
        errors.append(f'{page}: {message}')

    def require(page, node, tag=None, cls=None, **attrs):
        matches = node.find(tag, cls, **attrs)
        if len(matches) != 1:
            fail(page, f'ожидался один блок {cls or tag or attrs}, найдено {len(matches)}')
        return matches[0] if matches else None

    def resources(page, node):
        for item in node.walk():
            attribute = 'src' if item.tag == 'img' else 'href' if item.tag == 'a' else None
            if not attribute:
                continue
            url = item.attrs.get(attribute, '')
            if not url:
                fail(page, f'пустой {attribute}')
                continue
            try:
                target = local_target(root, root / page, url)
                if target is not None and not target.is_file():
                    fail(page, f'файл ссылки или изображения отсутствует: {url}')
            except ValueError as error:
                fail(page, str(error))
            if item.tag == 'img' and not item.attrs.get('alt', '').strip():
                fail(page, f'отсутствует alt изображения: {url}')

    if not all((root / name).is_file() for name in ['index.html', 'blog.html', 'sitemap.xml']):
        return ['Отсутствует index.html, blog.html или sitemap.xml']
    home = read(root / 'index.html')
    blog = read(root / 'blog.html')
    home_section = require('index.html', home, id='blog')
    blog_main = require('blog.html', blog, tag='main')

    def card_urls(page, node):
        urls = []
        for card in node.find(tag='article', cls='post-card') if node else []:
            link = require(page, card, tag='a')
            resources(page, card)
            if link:
                urls.append(link.attrs.get('href', ''))
        if len(set(urls)) != len(urls):
            fail(page, 'повторные карточки статей')
        return urls

    home_urls = card_urls('index.html', home_section)
    blog_urls = card_urls('blog.html', blog_main)
    if len(home_urls) != 6:
        fail('index.html', f'в #blog должно быть ровно 6 карточек, найдено {len(home_urls)}')
    if home_urls != blog_urls[:6]:
        fail('index.html', 'карточки должны совпадать с первыми шестью в полной ленте, новая статья первой')
    article_paths = sorted(root.glob('blog/*.html'))
    expected_urls = {path.relative_to(root).as_posix() for path in article_paths}
    if set(blog_urls) != expected_urls:
        fail('blog.html', 'полная лента должна содержать по одной карточке каждой статьи')
    try:
        sitemap = ElementTree.parse(root / 'sitemap.xml')
        sitemap_urls = [node.text for node in sitemap.findall('.//{*}loc')]
    except ElementTree.ParseError as error:
        return errors + [f'sitemap.xml: неверный XML: {error}']
    published = {}
    for path in article_paths:
        page = path.relative_to(root).as_posix()
        dom = read(path)
        require(page, dom, tag='nav', cls='nav')
        require(page, dom, cls='mobile-menu')
        require(page, dom, tag='footer')
        require(page, dom, cls='cookie-banner')
        hero = require(page, dom, cls='blog-hero')
        post = require(page, dom, tag='article', cls='post')
        related = require(page, dom, cls='related')
        if hero:
            require(page, hero, tag='h1')
            require(page, hero, tag='p')
        if post:
            header = require(page, post, cls='post-header')
            body = require(page, post, cls='post-body')
            require(page, post, cls='post-cover')
            require(page, post, cls='post-cover-tag')
            share = require(page, post, cls='post-share')
            if header:
                require(page, header, tag='h2')
                require(page, header, cls='post-dek')
                times = header.find(tag='time', itemprop='datePublished')
                if len(times) != 1:
                    fail(page, 'нужна одна дата публикации в post-header')
                else:
                    try:
                        published[page] = date.fromisoformat(times[0].attrs.get('datetime', ''))
                    except ValueError:
                        fail(page, 'некорректная дата публикации')
            if body and not body.text():
                fail(page, 'пустой текст статьи')
            if share and len(share.find(tag='a')) < 2:
                fail(page, 'в post-share нужны два перехода')
            resources(page, post)
        if related:
            cards = related.find(tag='article', cls='post-card')
            if len(cards) != 3:
                fail(page, f'в related должно быть ровно 3 карточки, найдено {len(cards)}')
            targets = []
            for card in cards:
                link = require(page, card, tag='a')
                require(page, card, tag='img')
                headings = [node for node in card.walk() if node.tag in {'h2', 'h3'} and node.text()]
                if len(headings) != 1:
                    fail(page, 'в связанной карточке нужен один непустой заголовок H2 или H3')
                resources(page, card)
                if link:
                    try:
                        target = local_target(root, path, link.attrs.get('href', ''))
                    except ValueError:
                        target = None
                    if target is None or target == path.resolve() or target.parent != (root / 'blog').resolve():
                        fail(page, 'related должен ссылаться на другую локальную статью блога')
                    targets.append(target)
            if len(set(targets)) != len(targets):
                fail(page, 'повторные статьи в related')
        canonical = dom.find(tag='link', rel='canonical')
        if len(canonical) != 1 or canonical[0].attrs.get('href') != DOMAIN + page:
            fail(page, 'canonical не совпадает с адресом статьи')
        if sitemap_urls.count(DOMAIN + page) != 1:
            fail(page, 'статья должна присутствовать в sitemap ровно один раз')
        blocks = dom.find(tag='script', type='application/ld+json')
        if len(blocks) != 1:
            fail(page, 'нужен ровно один JSON-LD блок')
        else:
            try:
                data = json.loads(blocks[0].text())
                items = data.get('@graph', [data])
                articles = [item for item in items if item.get('@type') == 'Article']
                if len(articles) != 1:
                    fail(page, 'JSON-LD должен содержать один Article')
            except (ValueError, AttributeError, TypeError):
                fail(page, 'неверный JSON-LD')
    dates = [published[url] for url in blog_urls if url in published]
    if dates != sorted(dates, reverse=True):
        fail('blog.html', 'статьи должны быть отсортированы по дате, новые сверху')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print('Проверка публикации не пройдена:')
        for error in errors:
            print('- ' + error)
        return 1
    print('Публикация согласована: шаблоны статей, 3 связанные карточки, 6 карточек главной и полная лента.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

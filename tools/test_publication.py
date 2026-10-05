"""Проверяем, что ошибочную публикацию нельзя выдать за корректную."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_publication import DOMAIN, validate


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'blog').mkdir()
        (self.root / 'assets').mkdir()
        (self.root / 'assets/test.png').write_bytes(b'image fixture')
        self.names = [f'blog/post-{i}.html' for i in range(7)]
        for i, name in enumerate(self.names):
            targets = [self.names[(i + shift) % 7].removeprefix('blog/') for shift in [1, 2, 3]]
            cards = ''.join(self.related_card(target) for target in targets)
            ld = json.dumps({'@type': 'Article', 'headline': 'Заголовок'}, ensure_ascii=False)
            source = f'''<html><head>
<link rel="canonical" href="{DOMAIN}{name}">
<script type="application/ld+json">{ld}</script></head><body>
<nav class="nav"></nav><div class="mobile-menu"></div>
<header class="blog-hero"><h1>Название статьи</h1><p>Тизер</p></header>
<article class="post">
<div class="post-cover"><img src="../assets/test.png" alt="Обложка"><span class="post-cover-tag">Раздел</span></div>
<header class="post-header"><time itemprop="datePublished" datetime="2026-10-{7-i:02d}">Дата</time><h2>Тема статьи</h2><p class="post-dek">Введение</p></header>
<div class="post-body"><p>Утверждённый текст</p></div>
<aside class="post-share"><a href="../index.html#pricing">В клуб</a><a href="https://vk.com/probeg_simf">ВКонтакте</a></aside>
</article>
<section class="related">{cards}</section>
<footer></footer><div class="cookie-banner"></div></body></html>'''
            self.write(name, source)
        self.write('blog.html', '<main>' + ''.join(self.card(name) for name in self.names) + '</main>')
        self.write('index.html', '<section id="blog">' + ''.join(self.card(name) for name in self.names[:6]) + '</section>')
        self.write('sitemap.xml', '<urlset>' + ''.join(f'<url><loc>{DOMAIN}{name}</loc></url>' for name in self.names) + '</urlset>')

    def write(self, name, source):
        (self.root / name).write_text(source, encoding='utf-8')

    def replace(self, name, before, after):
        path = self.root / name
        source = path.read_text(encoding='utf-8')
        self.assertIn(before, source)
        self.write(name, source.replace(before, after, 1))

    @staticmethod
    def card(target):
        return f'<article class="post-card"><a href="{target}"><img src="assets/test.png" alt="Обложка"><h3>Заголовок</h3></a></article>'

    @staticmethod
    def related_card(target):
        return f'<article class="post-card"><a href="{target}"><img src="../assets/test.png" alt="Обложка"><h3>Другой материал</h3></a></article>'

    def assert_failure(self, text):
        errors = validate(self.root)
        self.assertTrue(any(text in error for error in errors), errors)

    def test_valid_site_and_legacy_h3_are_accepted(self):
        self.assertEqual([], validate(self.root))

    def test_missing_related_block_fails(self):
        source = (self.root / self.names[0]).read_text(encoding='utf-8')
        start, end = source.index('<section class="related">'), source.index('</section>') + len('</section>')
        self.write(self.names[0], source[:start] + source[end:])
        self.assert_failure('блок related')

    def test_two_related_cards_fail(self):
        self.replace(self.names[0], self.related_card('post-1.html'), '')
        self.assert_failure('ровно 3 карточки')

    def test_duplicate_related_target_fails(self):
        self.replace(self.names[0], 'href="post-2.html"', 'href="post-1.html"')
        self.assert_failure('повторные статьи в related')

    def test_self_related_target_fails(self):
        self.replace(self.names[0], 'href="post-1.html"', 'href="post-0.html"')
        self.assert_failure('другую локальную статью')

    def test_missing_related_image_fails(self):
        self.replace(self.names[0], self.related_card('post-1.html'), self.related_card('post-1.html').replace('<img src="../assets/test.png" alt="Обложка">', ''))
        self.assert_failure('блок img')

    def test_duplicate_related_headings_fail(self):
        self.replace(self.names[0], '<h3>Другой материал</h3>', '<h3>Другой материал</h3><h2>Дубликат</h2>')
        self.assert_failure('один непустой заголовок')

    def test_missing_share_fails(self):
        self.replace(self.names[0], 'class="post-share"', 'class="missing-share"')
        self.assert_failure('блок post-share')

    def test_one_share_link_fails(self):
        self.replace(self.names[0], '<a href="https://vk.com/probeg_simf">ВКонтакте</a>', '')
        self.assert_failure('два перехода')

    def test_missing_header_dek_fails(self):
        self.replace(self.names[0], '<p class="post-dek">Введение</p>', '')
        self.assert_failure('блок post-dek')

    def test_missing_cover_fails(self):
        self.replace(self.names[0], 'class="post-cover"', 'class="missing-cover"')
        self.assert_failure('блок post-cover')

    def test_missing_cookie_banner_fails(self):
        self.replace(self.names[0], '<div class="cookie-banner"></div>', '')
        self.assert_failure('блок cookie-banner')

    def test_broken_local_image_fails(self):
        (self.root / 'assets/test.png').unlink()
        self.assert_failure('изображения отсутствует')

    def test_related_path_outside_root_reports_failure(self):
        self.replace(self.names[0], 'href="post-1.html"', 'href="../../outside.html"')
        self.assert_failure('путь выходит за каталог')

    def test_seven_home_cards_fail(self):
        self.replace('index.html', '</section>', self.card(self.names[6]) + '</section>')
        self.assert_failure('ровно 6 карточек')

    def test_five_home_cards_fail(self):
        self.replace('index.html', self.card(self.names[5]), '')
        self.assert_failure('ровно 6 карточек')

    def test_latest_article_missing_from_home_fails(self):
        self.replace('index.html', self.card(self.names[0]), self.card(self.names[6]))
        self.assert_failure('новая статья первой')

    def test_old_article_removed_from_full_blog_fails(self):
        self.replace('blog.html', self.card(self.names[6]), '')
        self.assert_failure('полная лента')

    def test_unsorted_blog_and_home_fail(self):
        self.replace(self.names[0], 'datetime="2026-10-07"', 'datetime="2026-09-01"')
        self.assert_failure('отсортированы по дате')

    def test_missing_sitemap_entry_fails(self):
        self.replace('sitemap.xml', f'<url><loc>{DOMAIN}{self.names[0]}</loc></url>', '')
        self.assert_failure('в sitemap ровно один раз')

    def test_invalid_json_ld_fails(self):
        self.replace(self.names[0], '{"@type": "Article", "headline": "Заголовок"}', 'invalid json')
        self.assert_failure('неверный JSON-LD')

    def test_cli_returns_failure_for_incomplete_publication(self):
        self.replace('index.html', self.card(self.names[0]), self.card(self.names[6]))
        result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).with_name('check_publication.py')), '--root', str(self.root)], capture_output=True, text=True, encoding='utf-8', check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn('новая статья первой', result.stdout)


if __name__ == '__main__':
    unittest.main()

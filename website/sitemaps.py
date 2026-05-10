from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PublicPagesSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "website:home",
            "website:sobre",
            "website:contactos",
            "website:feedback",
            "website:termos_condicoes",
            "website:politica_privacidade",
            "website:planos",
            "website:registo",
        ]

    def location(self, item):
        return reverse(item)

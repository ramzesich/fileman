from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.selector import HtmlXPathSelector

from swimport.items import SWPackageItem


class CompuLabSpider(CrawlSpider):
    name = 'compulab'
    allowed_domains = ['compulab.co.il']
    start_urls = [
        'http://compulab.co.il/products/',
    ]
    rules = (
        Rule(
            SgmlLinkExtractor(
                allow=(
                    'embedded-pcs/.*',
                    'computer-on-modules/.*',
                    'handheld-computers/.*',
                    'sbcs/.*',
                ),
                allow_domains='compulab.co.il',
            ),
            callback='parse_product'
        ),
    )
    
    def parse_product(self, response):
        items = []
        hxs = HtmlXPathSelector(response)
        product = hxs.select('//div[@id="main_content"]/*[1]/text()').extract()
        for sw_package in hxs.select('//div[@class="dev-res-part"]//li'):
            a = sw_package.select('a[contains(@href, "wp-content/uploads")]')
            if not a: continue
            items.append(SWPackageItem(
                product=product,
                title=a.select('text()').extract(),
                date=sw_package.select('span[@class="media-tag-item-date"]/text()').extract(),
                url=a.select('@href').extract()
            ))
        return items

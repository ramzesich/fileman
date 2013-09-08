from scrapy.item import Item, Field


class SWPackageItem(Item):
    product = Field()
    title = Field()
    date = Field()
    url = Field()

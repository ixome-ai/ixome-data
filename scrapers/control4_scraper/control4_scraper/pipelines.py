from itemadapter import ItemAdapter

class Control4ScraperPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # Example cleaning: Strip whitespace from fields
        for field in adapter.keys():
            if adapter[field]:
                adapter[field] = adapter[field].strip()
        return item
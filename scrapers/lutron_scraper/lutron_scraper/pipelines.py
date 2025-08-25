import json
from itemadapter import ItemAdapter

class LutronScraperPipeline:
    def __init__(self):
        self.file = open('lutron_data.json', 'w', encoding='utf-8')
        self.discarded_file = open('discarded_items.json', 'w', encoding='utf-8')
        self.items = []

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        cleaned_item = {
            'issue': adapter.get('issue', '').strip(),
            'solution': adapter.get('solution', '').strip(),
            'product': adapter.get('product', '').strip(),
            'category': adapter.get('category', '').strip(),
            'url': adapter.get('url', '').strip()
        }
        if cleaned_item['issue'] or cleaned_item['solution'] or cleaned_item['product']:
            self.items.append(cleaned_item)
            json.dump(cleaned_item, self.file, ensure_ascii=False)
            self.file.write('\n')
        else:
            json.dump(cleaned_item, self.discarded_file, ensure_ascii=False)
            self.discarded_file.write('\n')
        return item

    def close_spider(self, spider):
        self.file.close()
        self.discarded_file.close()
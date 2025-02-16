import time

# This dictionary will manage caches, organized by page_id and data type
cache_grouped_by_page_id = {}

def update_cache(page_id, data_type, new_data):
    """Update the cache for the given page_id and data type with new data and timestamp."""
    # Set default if page_id does not exist
    if page_id not in cache_grouped_by_page_id:
        cache_grouped_by_page_id[page_id] = {}

    # Set default for data_type if it does not exist
    cache_grouped_by_page_id[page_id].setdefault(data_type, {'data': None, 'timestamp': 0})

    # Update cache data and timestamp
    cache_grouped_by_page_id[page_id][data_type]['data'] = new_data
    cache_grouped_by_page_id[page_id][data_type]['timestamp'] = time.time()

def get_cache(page_id, data_type):
    """Retrieve cached data for the given page_id and data type."""
    # Safely attempt to get the cache, if it doesn't exist, return a default
    return cache_grouped_by_page_id.get(page_id, {}).get(data_type, {'data': None, 'timestamp': 0})

def delete_cache(page_id, data_type):
    """Delete the cache for the specified page_id and data type."""
    if page_id in cache_grouped_by_page_id and data_type in cache_grouped_by_page_id[page_id]:
        del cache_grouped_by_page_id[page_id][data_type]
        # If there are no more data types for this page_id, remove the page_id entry
        if not cache_grouped_by_page_id[page_id]:
            del cache_grouped_by_page_id[page_id]
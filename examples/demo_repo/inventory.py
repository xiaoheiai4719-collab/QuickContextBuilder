def stock_available(warehouse, product_id):
    return warehouse.get(product_id, 0) > 0

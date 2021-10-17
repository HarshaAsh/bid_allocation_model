def test_veracity_products(products):
    # Function checks if the required columns are present, throws error if they arnt
    products[['prod_name', 'prod_desc', 'selling_price', 'demand']]

def test_veracity_suppliers(suppliers):
    # Function checks if the required columns are present, throws error if they arnt
    suppliers[['supp_name', 'supp_desc', 'trans_cost']]

def test_veracity_bids(bids):
    # Function checks if the required columns are present, throws error if they arnt
    bids[['prod_name', 'supp_name', 'bid_cost', 'other_cost']]
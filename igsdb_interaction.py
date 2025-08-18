# For more information on getting data from the igsdb please see igsdb.lbl.gov/openapi
igsdb_api_token = "0e94db9c8cda032d3eaa083e21984350c17633ca"
url_single_product = "https://igsdb.lbl.gov/api/v1/products/{id}"  # Template URL for single product
url_single_product_datafile = "https://igsdb.lbl.gov/api/v1/products/{id}/datafile"  # Template URL for getting data file for a product
headers = {"Authorization": "Token {token}".format(token=igsdb_api_token)}  # Token authorization headers

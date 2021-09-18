def extract_address_from_a_response(a_response):
    return {x.address for x in a_response.rrset}

